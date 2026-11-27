"""Dialog application service coordinating Agent/LLM, Hybrid RAG, safety checks, and SSE."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from uuid import UUID

from medai.agent import (
    Agent,
    AgentConfig,
    AgentResponse,
    AgentTextDelta,
    LLMProvider,
    Message,
    MessageRole,
    ToolRegistry,
    UserRequest,
    load_system_prompt,
)
from medai.agent.medical_tools import (
    CheckInteractionsTool,
    GetSafetyProfileTool,
    LookupMedicineTool,
    SearchMedicinesTool,
    analyze_medicine_safety,
)
from medai.dialogs.event_broker import DialogEventBroker
from medai.dialogs.events import DialogEvent, DialogEventType, DialogSubscription
from medai.dialogs.guardrails import (
    OUT_OF_DOMAIN_RESPONSE,
    PROMPT_INJECTION_RESPONSE,
    detect_prompt_injection,
    is_emergency_query,
    is_out_of_domain_query,
    verify_output_grounding,
)
from medai.dialogs.history import (
    DialogNotFoundError,
    DialogSummary,
    DialogTranscript,
    HistoryStore,
    ReportNewsItem,
    make_title,
)
from medai.kit.stores import KitStore
from medai.observability import log_event
from medai.profile.stores import ProfileStore
from medai.rag.analyzer import MorphAnalyzer, TextAnalyzer, normalize_text
from medai.rag.hybrid import HybridRagIndex
from medai.rag.index import InMemoryBm25Index
from medai.rag.models import MedicineDocument, SearchResult

__all__ = ["DialogService"]

logger = logging.getLogger(__name__)

EMERGENCY_RESPONSE_TEXT = (
    "Обнаружены признаки неотложного жизнеугрожающего состояния! "
    "Прием таблеток запрещен до осмотра врачом. Немедленно наберите номер службы спасения 112 или 103.\n\n"
    "Шаги доврачебной первой помощи:\n"
    "1. Обеспечьте безопасность пострадавшего и вызовите скорую помощь (112).\n"
    "2. При термическом ожоге: охлаждайте зону проточной прохладной водой 15 минут. "
    "Категорически запрещено наносить масла, жир, спирт или прокалывать пузыри.\n"
    "3. При кровотечении: наложите давящую повязку, прижмите артерию выше раны.\n"
    "4. При потере сознания: поверните пострадавшего на бок для предотвращения западения языка.\n"
    "5. Контролируйте дыхание и пульс до прибытия врачей."
)

EMERGENCY_STEPS = [
    "Немедленно наберите номер службы спасения 112 или 103.",
    "При термическом ожоге: охлаждайте зону проточной прохладной водой 15 минут.",
    "Категорически запрещено наносить масла, спирт, мази или прокалывать пузыри.",
    "Обеспечьте покой и контролируйте дыхание пострадавшего до прибытия медиков.",
]

DISCLAIMER_TEXT = (
    "Информация носит ознакомительный доврачебный характер. "
    "При сохранении симптомов свыше 2 дней обратитесь к врачу."
)

_MD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_MD_ITALIC_STAR_RE = re.compile(r"(?<!\w)\*([^*\n]+?)\*(?!\w)")
_MD_CODE_RE = re.compile(r"`([^`]+?)`")


def strip_markdown(text: str) -> str:
    """Remove Markdown formatting tokens while keeping readable plain text structure."""
    if not text:
        return text
    cleaned = _MD_HEADING_RE.sub("", text)
    cleaned = _MD_BOLD_RE.sub(lambda m: m.group(1) if m.group(1) is not None else m.group(2), cleaned)
    cleaned = _MD_ITALIC_STAR_RE.sub(r"\1", cleaned)
    cleaned = _MD_CODE_RE.sub(r"\1", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "")
    cleaned = re.sub(r"^\s*\|\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*\|\s*$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def _kit_match_strength(doc: MedicineDocument, item_name: str) -> int:
    """Return 2 for direct drug match, 1 for multi-ingredient INN overlap, 0 otherwise."""
    norm_name = normalize_text(item_name)
    if not norm_name:
        return 0
    norm_title = normalize_text(doc.title)
    norm_inn = normalize_text(doc.inn)
    if norm_name in norm_title or norm_title in norm_name or norm_name == norm_inn:
        return 2
    first_word = norm_title.split("(")[0].strip().split()[0] if norm_title else ""
    if len(first_word) >= 4 and first_word in norm_name:
        return 2
    for part in norm_inn.split("+"):
        p = part.strip()
        if len(p) >= 4 and p in norm_name:
            return 1
    return 0


def _matches_kit_item(doc: MedicineDocument, item_name: str) -> bool:
    return _kit_match_strength(doc, item_name) > 0


class DialogService:
    def __init__(
        self,
        history_store: HistoryStore,
        event_broker: DialogEventBroker,
        bm25_index: InMemoryBm25Index | None = None,
        analyzer: TextAnalyzer | None = None,
        *,
        hybrid_index: HybridRagIndex | None = None,
        llm_provider: LLMProvider | None = None,
        kit_store: KitStore | None = None,
        profile_store: ProfileStore | None = None,
    ) -> None:
        self._history = history_store
        self._broker = event_broker
        self._analyzer = MorphAnalyzer() if analyzer is None else analyzer
        self._bm25_index = bm25_index
        if hybrid_index is not None:
            self._hybrid_index: HybridRagIndex | None = hybrid_index
        elif bm25_index is not None:
            self._hybrid_index = HybridRagIndex(bm25_index, analyzer=self._analyzer)
        else:
            self._hybrid_index = None

        self._llm_provider = llm_provider
        self._kit_store = kit_store
        self._profile_store = profile_store
        self._system_prompt = load_system_prompt()
        self._dialog_chains: dict[UUID, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    def set_rag_index(self, bm25_index: InMemoryBm25Index) -> None:
        """Hot-swap the active RAG index after admin edits or corpus reload."""
        self._bm25_index = bm25_index
        self._hybrid_index = HybridRagIndex(bm25_index, analyzer=self._analyzer)

    def _can_use_llm(self) -> bool:
        if self._llm_provider is None:
            return False
        return getattr(self._llm_provider, "is_configured", True)

    async def start_dialog(self, owner_id: UUID) -> UUID:
        dialog_id = await self._history.create_dialog(owner_id)
        log_event(
            logger,
            logging.INFO,
            "dialog.created",
            dialog_id=str(dialog_id),
            user_id=str(owner_id),
        )
        return dialog_id

    async def list_dialogs(
        self, owner_id: UUID, limit: int = 50
    ) -> list[DialogSummary]:
        return await self._history.list_dialogs(owner_id, limit=limit)

    async def get_transcript(self, owner_id: UUID, dialog_id: UUID) -> DialogTranscript:
        return await self._history.get_transcript(owner_id, dialog_id)

    async def delete_dialog(self, owner_id: UUID, dialog_id: UUID) -> None:
        deleted = await self._history.delete_dialog(owner_id, dialog_id)
        if not deleted:
            raise DialogNotFoundError(dialog_id)
        await self._broker.close_dialog(dialog_id)
        log_event(
            logger,
            logging.INFO,
            "dialog.deleted",
            dialog_id=str(dialog_id),
            user_id=str(owner_id),
        )

    async def set_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int, score: int
    ) -> None:
        await self._history.set_feedback(owner_id, dialog_id, message_id, score)

    async def clear_feedback(
        self, owner_id: UUID, dialog_id: UUID, message_id: int
    ) -> None:
        await self._history.clear_feedback(owner_id, dialog_id, message_id)

    async def report(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        message_id: int,
        reason: str,
        comment: str | None = None,
    ) -> int:
        return await self._history.create_report(
            owner_id, dialog_id, message_id, reason, comment
        )

    async def report_news(self, owner_id: UUID) -> list[ReportNewsItem]:
        return await self._history.list_report_news(owner_id)

    async def mark_report_news_seen(
        self, owner_id: UUID, report_ids: list[int]
    ) -> None:
        await self._history.mark_report_news_seen(owner_id, report_ids)

    async def subscribe(self, owner_id: UUID, dialog_id: UUID) -> DialogSubscription:
        await self._history.get_transcript(owner_id, dialog_id)
        return await self._broker.subscribe(dialog_id)

    async def unsubscribe(self, subscription: DialogSubscription) -> None:
        await self._broker.unsubscribe(subscription)

    async def submit_message(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        content: str,
        include_kit_context: bool = True,
        selected_pills: list[str] | None = None,
        response_depth: str = "detailed",
    ) -> None:
        await self._history.get_transcript(owner_id, dialog_id)

        async with self._lock:
            prev_task = self._dialog_chains.get(dialog_id)
            task = asyncio.create_task(
                self._run_chain(
                    prev_task,
                    owner_id,
                    dialog_id,
                    content,
                    include_kit_context,
                    list(selected_pills or []),
                    response_depth,
                )
            )
            self._dialog_chains[dialog_id] = task

    async def _run_chain(
        self,
        prev_task: asyncio.Task[None] | None,
        owner_id: UUID,
        dialog_id: UUID,
        content: str,
        include_kit_context: bool,
        selected_pills: list[str],
        response_depth: str,
    ) -> None:
        if prev_task is not None:
            try:
                await prev_task
            except Exception:
                pass
        await self._process_message(
            owner_id,
            dialog_id,
            content,
            include_kit_context,
            selected_pills,
            response_depth,
        )

    async def _load_user_safety_snapshot(
        self,
        owner_id: UUID | None,
        *,
        kit_names_override: list[str] | None = None,
        kit_items_override: list[dict[str, Any]] | None = None,
        health_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kit_items: list[dict[str, Any]] = []
        health_profile: dict[str, Any] = dict(health_override or {})

        if owner_id is not None:
            if self._kit_store is not None:
                try:
                    stored_items = await self._kit_store.list_items(owner_id)
                    kit_items = [
                        {
                            "name": it.name,
                            "dosage": it.dosage,
                            "form": it.form,
                            "expiry": it.expiry,
                            "is_expired": it.is_expired,
                            "status": it.status,
                        }
                        for it in stored_items
                    ]
                except Exception:
                    logger.warning("Failed to load user kit for %s", owner_id)
            if self._profile_store is not None and not health_profile:
                try:
                    prof = await self._profile_store.get_profile(owner_id)
                    health_profile = prof.model_dump()
                except Exception:
                    logger.warning("Failed to load health profile for %s", owner_id)

        if not kit_items and kit_items_override:
            for raw in kit_items_override:
                if isinstance(raw, dict) and raw.get("name"):
                    kit_items.append(
                        {
                            "name": str(raw.get("name")),
                            "dosage": raw.get("dosage") or "",
                            "form": raw.get("form") or "",
                            "expiry": raw.get("expiry") or "",
                            "is_expired": bool(raw.get("is_expired", False)),
                            "status": raw.get("status") or "otc",
                        }
                    )
        if not kit_items and kit_names_override:
            kit_items = [{"name": n, "is_expired": False} for n in kit_names_override if n]

        return {
            "kit_items": kit_items,
            "kit_names": [it["name"] for it in kit_items],
            "health_profile": health_profile,
        }

    def _find_docs_for_pills(self, pill_names: list[str]) -> list[SearchResult]:
        if not self._hybrid_index or not pill_names:
            return []
        found: list[SearchResult] = []
        seen_ids: set[str] = set()
        for name in pill_names:
            q = normalize_text(name)
            matched_docs = [
                d
                for d in self._hybrid_index.documents.values()
                if q in normalize_text(d.title) or q in normalize_text(d.inn)
            ]
            if not matched_docs:
                matched_docs = self._hybrid_index.suggest_fuzzy(
                    name, threshold=0.25, limit=1
                )
            for doc in matched_docs[:1]:
                if doc.id not in seen_ids:
                    seen_ids.add(doc.id)
                    found.append(
                        SearchResult(
                            doc_id=doc.id,
                            title=doc.title,
                            score=10.0,
                            document=doc,
                        )
                    )
        return found

    def _synthesize_rag(
        self,
        query: str,
        user_kit_names: list[str] | None = None,
        *,
        selected_pills: list[str] | None = None,
        health_profile: dict[str, Any] | None = None,
        kit_items: list[dict[str, Any]] | None = None,
        response_depth: str = "detailed",
    ) -> dict[str, Any]:
        """Deterministic safety-aware RAG synthesis (used as fallback and card builder)."""
        if detect_prompt_injection(query):
            return {
                "status": "injection_blocked",
                "emergency_mode": False,
                "message": PROMPT_INJECTION_RESPONSE,
                "first_aid_steps": None,
                "recommendation": None,
                "safety_warnings": [],
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        if is_emergency_query(query):
            return {
                "status": "emergency",
                "emergency_mode": True,
                "message": EMERGENCY_RESPONSE_TEXT,
                "first_aid_steps": EMERGENCY_STEPS,
                "recommendation": None,
                "safety_warnings": [],
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        if is_out_of_domain_query(query):
            return {
                "status": "out_of_domain",
                "emergency_mode": False,
                "message": OUT_OF_DOMAIN_RESPONSE,
                "first_aid_steps": None,
                "recommendation": None,
                "safety_warnings": [],
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        if not self._hybrid_index:
            return {
                "status": "success",
                "emergency_mode": False,
                "message": "Поисковый индекс временно недоступен. Обратитесь к врачу.",
                "first_aid_steps": None,
                "recommendation": None,
                "safety_warnings": [],
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        # 1. Resolve explicitly selected pills first and search wider candidate pool so kit medicines are prioritized
        pill_results = self._find_docs_for_pills(selected_pills or [])
        symptom_results = self._hybrid_index.search_hybrid(
            query, top_k=8, bm25_min_gate=4.5
        )

        # Combine pill results & symptom results uniquely
        combined_results: list[SearchResult] = []
        seen_ids: set[str] = set()
        for r in pill_results + symptom_results:
            if r.doc_id not in seen_ids:
                seen_ids.add(r.doc_id)
                combined_results.append(r)

        # Only fall back to arbitrary user_kit_names when LLM is disabled AND query itself looked vague
        # (never force a medicine card onto playful/off-corpus health questions when live LLM handles them).
        if not combined_results and user_kit_names and not self._can_use_llm():
            combined_results = self._find_docs_for_pills(user_kit_names)

        # Prioritize direct valid (non-expired) medicines present in the user's first aid kit
        effective_kit = kit_items or [{"name": n, "is_expired": False} for n in (user_kit_names or [])]
        pill_id_set = {r.doc_id for r in pill_results}

        def _kit_priority(sr: SearchResult) -> tuple[int, float]:
            if sr.doc_id in pill_id_set:
                return (0, -sr.score)
            matches = [
                (it, _kit_match_strength(sr.document, str(it.get("name", ""))))
                for it in effective_kit
            ]
            matches = [(it, lvl) for it, lvl in matches if lvl > 0]
            if matches:
                max_lvl = max(lvl for _, lvl in matches)
                has_valid = any(not it.get("is_expired") for it, _ in matches)
                cand_warns = analyze_medicine_safety(
                    [sr.document], health_profile=health_profile, user_kit_items=effective_kit
                )
                has_severe = any("АЛЛЕРГИЯ" in w or "ПРОСРОЧЕНО" in w or "МЕДКАРТА" in w for w in cand_warns)
                if has_valid and not has_severe:
                    return (1 if max_lvl == 2 else 2, -sr.score)
                if has_valid:
                    return (3, -sr.score)
                return (5, -sr.score)
            return (4, -sr.score)

        search_results = sorted(combined_results, key=_kit_priority)

        if not search_results:
            return {
                "status": "success",
                "emergency_mode": False,
                "message": (
                    "В документах нет этой информации: в официальном корпусе домашней аптечки "
                    "отсутствуют данные по вашему запросу. Рекомендуется обратиться к врачу."
                ),
                "first_aid_steps": None,
                "recommendation": None,
                "safety_warnings": [],
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        docs: list[MedicineDocument] = [r.document for r in search_results[:3]]
        safety_warnings = analyze_medicine_safety(
            docs,
            health_profile=health_profile,
            user_kit_items=kit_items,
        )

        # Pick safest candidate from top-3 if top-1 triggers allergy/chronic conflict
        chosen_doc = docs[0]
        if safety_warnings and len(docs) > 1:
            for cand in docs[1:]:
                cand_warns = analyze_medicine_safety(
                    [cand], health_profile=health_profile, user_kit_items=kit_items
                )
                if not cand_warns:
                    chosen_doc = cand
                    break

        sources = [
            {
                "doc_id": r.doc_id,
                "title": r.title,
                "bm25_score": r.score,
            }
            for r in search_results[:3]
        ]

        in_kit = any(_matches_kit_item(chosen_doc, str(n)) for n in (user_kit_names or []))

        indications_str = ", ".join(chosen_doc.indications[:4])
        contraindications_str = (
            ", ".join(chosen_doc.contraindications[:3])
            if chosen_doc.contraindications
            else "Не указаны"
        )
        interactions_str = (
            ", ".join(chosen_doc.interactions[:2])
            if chosen_doc.interactions
            else "Не превышать максимальную суточную дозировку."
        )

        warn_block = ""
        if safety_warnings:
            warn_block = "\n\nПредупреждения по вашей медкарте и аптечке:\n" + "\n".join(
                f"- {w}" for w in safety_warnings
            )

        if response_depth == "brief":
            full_text = (
                f"[{chosen_doc.id}] {chosen_doc.title} ({chosen_doc.inn}) — {chosen_doc.category}.\n"
                f"Дозировка: {chosen_doc.dosage}"
                f"{warn_block}\n\n{DISCLAIMER_TEXT}"
            )
        else:
            full_text = (
                f"По результатам анализа рекомендован препарат [{chosen_doc.id}] {chosen_doc.title} "
                f"({chosen_doc.inn}), группа: {chosen_doc.category}.\n\n"
                f"Показания: {indications_str}.\n"
                f"Режим дозирования: {chosen_doc.dosage}\n"
                f"Противопоказания: {contraindications_str}."
                f"{warn_block}\n\n{DISCLAIMER_TEXT}"
            )

        if not verify_output_grounding(full_text, search_results):
            full_text += "\n\n(Сверьте дозировку с официальной инструкцией перед приемом.)"

        return {
            "status": "success",
            "emergency_mode": False,
            "message": full_text,
            "first_aid_steps": None,
            "recommendation": {
                "medicine_name": chosen_doc.title,
                "in_user_kit": in_kit,
                "dosage": chosen_doc.dosage,
                "contraindications": contraindications_str,
                "warnings": (
                    " | ".join(safety_warnings)
                    if safety_warnings
                    else interactions_str
                ),
            },
            "safety_warnings": safety_warnings,
            "sources": sources,
            "disclaimer": DISCLAIMER_TEXT,
        }

    def _build_patient_context_prompt(
        self,
        safety_snapshot: dict[str, Any],
        selected_pills: list[str],
    ) -> str:
        profile = safety_snapshot.get("health_profile") or {}
        age = profile.get("age", 25)
        weight = profile.get("weight_kg", profile.get("weight", 70))
        allergies = profile.get("allergies") or []
        chronic = profile.get("chronic_diseases") or profile.get("chronic") or []
        notes = profile.get("special_notes") or ""

        kit_items = safety_snapshot.get("kit_items") or []
        if kit_items:
            kit_lines = []
            for it in kit_items:
                name = it.get("name", "Препарат")
                dosage = it.get("dosage") or ""
                expiry = it.get("expiry") or "не указан"
                expired_flag = "ПРОСРОЧЕН! ПРИЕМ ЗАПРЕЩЕН" if it.get("is_expired") else f"годен до {expiry}"
                kit_lines.append(f"- {name} ({dosage}) [{expired_flag}]")
            kit_block = "\n".join(kit_lines)
        else:
            kit_block = "Аптечка пользователя пуста."

        lines = [
            "АКТУАЛЬНЫЙ ПРОФИЛЬ И АПТЕЧКА ПАЦИЕНТА (ОБЯЗАТЕЛЬНО ИСПОЛЬЗОВАТЬ В ОТВЕТЕ):",
            f"- Возраст: {age} лет",
            f"- Вес: {weight} кг",
            f"- Аллергии: {', '.join(allergies) if allergies else 'не указаны'}",
            f"- Хронические заболевания: {', '.join(chronic) if chronic else 'не указаны'}",
        ]
        if notes:
            lines.append(f"- Особые примечания: {notes}")
        if selected_pills:
            lines.append(f"- Явно выбраны пользователем в сообщении: {', '.join(selected_pills)}")
        lines.append("Домашняя аптечка пользователя:\n" + kit_block)
        lines.append(
            "Напоминание: сначала проверь, что есть подходящего (и НЕ просроченного) в аптечке выше, "
            "обязательно учти возраст/вес/хронику/аллергии, и пиши ЧИСТЫМ ТЕКСТОМ без Markdown (** и ### запрещены)."
        )
        return "\n".join(lines)

    async def _run_llm_agent_stream(
        self,
        dialog_id: UUID | None,
        history: list[Message],
        query: str,
        safety_snapshot: dict[str, Any],
        selected_pills: list[str],
        response_depth: str,
    ) -> tuple[str, bool]:
        assert self._llm_provider is not None
        assert self._hybrid_index is not None

        tools = ToolRegistry(
            [
                SearchMedicinesTool(self._hybrid_index),
                LookupMedicineTool(self._hybrid_index),
                GetSafetyProfileTool(safety_snapshot),
                CheckInteractionsTool(self._hybrid_index, safety_snapshot),
            ]
        )
        patient_context = self._build_patient_context_prompt(safety_snapshot, selected_pills)
        agent = Agent(
            llm_provider=self._llm_provider,
            tool_registry=tools,
            config=AgentConfig(system_prompt=f"{self._system_prompt}\n\n{patient_context}"),
        )

        prompt_query = query
        if selected_pills:
            prompt_query = (
                f"[Выбранные пользователем препараты: {', '.join(selected_pills)}] {query}"
            )

        req = UserRequest(
            content=prompt_query,
            response_depth="brief" if response_depth == "brief" else "detailed",
            selected_pills=selected_pills,
            user_kit_names=safety_snapshot.get("kit_names", []),
            health_profile=safety_snapshot.get("health_profile"),
        )

        final_content = ""
        used_llm = False
        async for ev in agent.run(history, req):
            if isinstance(ev, AgentTextDelta):
                if dialog_id is not None:
                    await self._broker.publish(
                        dialog_id,
                        DialogEvent(type=DialogEventType.MESSAGE_DELTA, delta=ev.content),
                    )
            elif isinstance(ev, AgentResponse):
                final_content = strip_markdown(ev.content)
                used_llm = ev.used_llm
        return final_content, used_llm

    async def _process_message(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        content: str,
        include_kit_context: bool,
        selected_pills: list[str],
        response_depth: str,
    ) -> None:
        try:
            await self._broker.publish(
                dialog_id,
                DialogEvent(type=DialogEventType.MESSAGE_START),
            )

            safety_snapshot = (
                await self._load_user_safety_snapshot(owner_id)
                if include_kit_context
                else {"kit_items": [], "kit_names": [], "health_profile": {}}
            )

            # Build structured clinical + RAG assessment first (for card & guardrails)
            rag_res = self._synthesize_rag(
                content,
                user_kit_names=safety_snapshot.get("kit_names", []),
                selected_pills=selected_pills,
                health_profile=safety_snapshot.get("health_profile"),
                kit_items=safety_snapshot.get("kit_items"),
                response_depth=response_depth,
            )

            full_text = str(rag_res.get("message") or "")
            used_llm = False
            streamed_live = False

            # Run live LLM Agent only if input passed guardrails (not emergency/injection/out-of-domain)
            if rag_res["status"] == "success" and self._can_use_llm() and self._hybrid_index:
                try:
                    transcript = await self._history.get_transcript(owner_id, dialog_id)
                    history = [
                        Message(
                            role=MessageRole.USER if m.role == "user" else MessageRole.ASSISTANT,
                            content=m.content,
                        )
                        for m in transcript.messages[-20:]
                        if m.role in ("user", "assistant") and (m.content or "").strip()
                    ]
                    llm_text, used_llm = await self._run_llm_agent_stream(
                        dialog_id=dialog_id,
                        history=history,
                        query=content,
                        safety_snapshot=safety_snapshot,
                        selected_pills=selected_pills,
                        response_depth=response_depth,
                    )
                    if llm_text.strip():
                        full_text = llm_text.strip()
                        streamed_live = True
                except Exception:
                    logger.warning("LLM stream failed, falling back to deterministic RAG.")
                    used_llm = False

            if not streamed_live:
                chunk_size = 24
                for i in range(0, len(full_text), chunk_size):
                    chunk = full_text[i : i + chunk_size]
                    await self._broker.publish(
                        dialog_id,
                        DialogEvent(
                            type=DialogEventType.MESSAGE_DELTA,
                            delta=chunk,
                        ),
                    )
                    await asyncio.sleep(0.005)

            rag_payload = {
                "status": rag_res["status"],
                "emergency_mode": rag_res["emergency_mode"],
                "first_aid_steps": rag_res.get("first_aid_steps"),
                "recommendation": rag_res.get("recommendation"),
                "safety_warnings": rag_res.get("safety_warnings", []),
                "sources": rag_res.get("sources", []),
                "disclaimer": rag_res.get("disclaimer", DISCLAIMER_TEXT),
                "used_llm": used_llm,
            }
            title = make_title(content)
            _, asst_msg = await self._history.append_exchange(
                owner_id=owner_id,
                dialog_id=dialog_id,
                user_content=content,
                assistant_content=full_text,
                rag_payload=rag_payload,
                title=title,
            )

            await self._broker.publish(
                dialog_id,
                DialogEvent(
                    type=DialogEventType.MESSAGE_END,
                    message_id=asst_msg.id,
                    status=rag_res["status"],
                    emergency_mode=rag_res["emergency_mode"],
                    first_aid_steps=rag_res.get("first_aid_steps"),
                    recommendation=rag_res.get("recommendation"),
                    safety_warnings=rag_res.get("safety_warnings"),
                    sources=rag_res.get("sources", []),
                    used_llm=used_llm,
                ),
            )
            log_event(
                logger,
                logging.INFO,
                "dialog.message_processed",
                dialog_id=str(dialog_id),
                message_id=asst_msg.id,
                used_llm=used_llm,
            )

        except Exception:
            logger.exception("Error processing message in dialog %s", dialog_id)
            await self._broker.publish(
                dialog_id,
                DialogEvent(
                    type=DialogEventType.MESSAGE_ERROR,
                    code="internal_error",
                    message="Произошла ошибка при обработке запроса.",
                ),
            )

    def process_query_sync(
        self,
        query: str,
        user_kit_names: list[str] | None = None,
        *,
        selected_pills: list[str] | None = None,
        health_profile: dict[str, Any] | None = None,
        kit_items: list[dict[str, Any]] | None = None,
        response_depth: str = "detailed",
    ) -> dict[str, Any]:
        """Synchronous query processor for direct unit calls and fallback."""
        res = self._synthesize_rag(
            query,
            user_kit_names=user_kit_names,
            selected_pills=selected_pills,
            health_profile=health_profile,
            kit_items=kit_items,
            response_depth=response_depth,
        )
        res["used_llm"] = False
        return res

    async def process_query_async(
        self,
        query: str,
        *,
        owner_id: UUID | None = None,
        user_kit_names: list[str] | None = None,
        user_kit_items: list[dict[str, Any]] | None = None,
        selected_pills: list[str] | None = None,
        health_profile: dict[str, Any] | None = None,
        response_depth: str = "detailed",
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Async /chat/query handler enriching with DB profile/kit + optional live LLM."""
        safety_snapshot = await self._load_user_safety_snapshot(
            owner_id,
            kit_names_override=user_kit_names,
            kit_items_override=user_kit_items,
            health_override=health_profile,
        )
        res = self._synthesize_rag(
            query,
            user_kit_names=safety_snapshot.get("kit_names") or user_kit_names,
            selected_pills=selected_pills,
            health_profile=safety_snapshot.get("health_profile") or health_profile,
            kit_items=safety_snapshot.get("kit_items"),
            response_depth=response_depth,
        )
        used_llm = False
        if res["status"] == "success" and self._can_use_llm() and self._hybrid_index:
            try:
                client_history = [
                    Message(
                        role=MessageRole.USER if h.get("role") == "user" else MessageRole.ASSISTANT,
                        content=str(h.get("content") or ""),
                    )
                    for h in (history or [])[-20:]
                    if h.get("role") in ("user", "assistant") and str(h.get("content") or "").strip()
                ]
                llm_text, used_llm = await self._run_llm_agent_stream(
                    dialog_id=None,
                    history=client_history,
                    query=query,
                    safety_snapshot=safety_snapshot,
                    selected_pills=list(selected_pills or []),
                    response_depth=response_depth,
                )
                if llm_text.strip():
                    res["message"] = strip_markdown(llm_text.strip())
            except Exception:
                logger.warning("LLM failed in /chat/query; using safety RAG synthesis.")
        res["used_llm"] = used_llm
        return res

    async def shutdown(self) -> None:
        async with self._lock:
            for task in self._dialog_chains.values():
                task.cancel()
        await self._broker.shutdown()
