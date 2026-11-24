"""Dialog application service coordinating history, BM25 RAG, and streaming events."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from medai.dialogs.event_broker import DialogEventBroker
from medai.dialogs.events import DialogEvent, DialogEventType, DialogSubscription
from medai.dialogs.guardrails import (
    OUT_OF_DOMAIN_RESPONSE,
    is_emergency_query,
    is_out_of_domain_query,
)
from medai.dialogs.history import (
    DialogNotFoundError,
    DialogSummary,
    DialogTranscript,
    HistoryStore,
    make_title,
)
from medai.observability import log_event
from medai.rag.analyzer import MorphAnalyzer, TextAnalyzer
from medai.rag.index import InMemoryBm25Index
from medai.rag.models import SearchResult

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

DISCLAIMER_TEXT = (
    "Информация носит ознакомительный доврачебный характер. "
    "При сохранении симптомов свыше 2 дней обратитесь к врачу."
)


class DialogService:
    def __init__(
        self,
        history_store: HistoryStore,
        event_broker: DialogEventBroker,
        bm25_index: InMemoryBm25Index | None = None,
        analyzer: TextAnalyzer | None = None,
    ) -> None:
        self._history = history_store
        self._broker = event_broker
        self._bm25_index = bm25_index
        self._analyzer = MorphAnalyzer() if analyzer is None else analyzer
        self._dialog_chains: dict[UUID, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

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

    async def subscribe(self, owner_id: UUID, dialog_id: UUID) -> DialogSubscription:
        # Validate ownership
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
    ) -> None:
        # Ensure dialog exists and is owned by caller
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
    ) -> None:
        if prev_task is not None:
            try:
                await prev_task
            except Exception:
                pass
        await self._process_message(owner_id, dialog_id, content, include_kit_context)

    def _is_emergency(self, text: str) -> bool:
        return is_emergency_query(text)

    def _synthesize_rag(
        self, query: str, user_kit_names: list[str] | None = None
    ) -> tuple[str, list[dict[str, Any]], bool]:
        if is_emergency_query(query):
            return EMERGENCY_RESPONSE_TEXT, [], True

        if is_out_of_domain_query(query):
            return OUT_OF_DOMAIN_RESPONSE, [], False

        if not self._bm25_index:
            return (
                "Поисковый индекс временно недоступен. Обратитесь к врачу.",
                [],
                False,
            )

        # Check if query asks about a specific medicine attached or mentioned
        if user_kit_names and self._bm25_index:
            for kit_med in user_kit_names:
                med_terms = self._analyzer.terms(kit_med)
                matched = self._bm25_index.search(med_terms, top_k=1)
                if matched and matched[0].score > 1.0:
                    top_doc = matched[0].document
                    sources = [
                        {
                            "doc_id": matched[0].doc_id,
                            "title": matched[0].title,
                            "bm25_score": matched[0].score,
                        }
                    ]
                    indications_str = ", ".join(top_doc.indications[:3])
                    contraindications_str = (
                        ", ".join(top_doc.contraindications[:3])
                        if top_doc.contraindications
                        else "Не указаны"
                    )
                    full_text = (
                        f"Препарат **{top_doc.title}** ({top_doc.inn}) — фармакотерапевтическая группа: {top_doc.category}.\n\n"
                        f"**Показания к применению:** {indications_str}.\n"
                        f"**Режим дозирования:** {top_doc.dosage}.\n"
                        f"**Противопоказания:** {contraindications_str}.\n\n"
                        f"*{DISCLAIMER_TEXT}*"
                    )
                    return full_text, sources, False

        terms = self._analyzer.terms(query)
        search_results: list[SearchResult] = self._bm25_index.search(terms, top_k=3)

        if not search_results or search_results[0].score < 1.0:
            return (
                "В официальном корпусе медицинской аптечки нет информации о препаратах для указанных симптомов. "
                "Рекомендуется обратиться к профильному врачу для очной консультации.",
                [],
                False,
            )

        top_doc = search_results[0].document
        sources = [
            {
                "doc_id": r.doc_id,
                "title": r.title,
                "bm25_score": r.score,
            }
            for r in search_results
        ]

        indications_str = ", ".join(top_doc.indications[:3])
        contraindications_str = (
            ", ".join(top_doc.contraindications[:3])
            if top_doc.contraindications
            else "Не указаны"
        )

        full_text = (
            f"По результатам анализа симптомов рекомендуется рассмотреть препарат **{top_doc.title}** ({top_doc.inn}), "
            f"фармакотерапевтическая группа: {top_doc.category}.\n\n"
            f"**Показания:** {indications_str}.\n"
            f"**Режим дозирования:** {top_doc.dosage}.\n"
            f"**Противопоказания:** {contraindications_str}.\n\n"
            f"*{DISCLAIMER_TEXT}*"
        )
        return full_text, sources, False

    async def _process_message(
        self,
        owner_id: UUID,
        dialog_id: UUID,
        content: str,
        include_kit_context: bool,
    ) -> None:
        try:
            # 1. Publish message_start
            await self._broker.publish(
                dialog_id,
                DialogEvent(type=DialogEventType.MESSAGE_START),
            )

            # 2. RAG Synthesis
            full_text, sources, is_emergency = self._synthesize_rag(content)

            # 3. Stream text deltas in chunks
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
                await asyncio.sleep(0.01)

            # 4. Atomically persist user and assistant messages
            rag_payload = {
                "emergency_mode": is_emergency,
                "sources": sources,
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

            # 5. Publish message_end
            await self._broker.publish(
                dialog_id,
                DialogEvent(
                    type=DialogEventType.MESSAGE_END,
                    message_id=asst_msg.id,
                    emergency_mode=is_emergency,
                    sources=sources,
                ),
            )
            log_event(
                logger,
                logging.INFO,
                "dialog.message_processed",
                dialog_id=str(dialog_id),
                message_id=asst_msg.id,
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
        self, query: str, user_kit_names: list[str] | None = None
    ) -> dict[str, Any]:
        """Synchronous query processor for legacy REST compatibility with /chat/query."""
        if is_emergency_query(query):
            return {
                "status": "emergency",
                "emergency_mode": True,
                "message": EMERGENCY_RESPONSE_TEXT,
                "first_aid_steps": [
                    "Немедленно наберите номер службы спасения 112 или 103.",
                    "При термическом ожоге: охлаждайте зону проточной водой 15 минут.",
                    "Категорически запрещено наносить масла или мази.",
                    "Наложите сухую повязку и обеспечьте покой до прибытия медиков.",
                ],
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
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        full_text, sources, is_emergency = self._synthesize_rag(
            query, user_kit_names=user_kit_names
        )
        if not sources:
            return {
                "status": "success",
                "emergency_mode": False,
                "message": full_text,
                "recommendation": None,
                "sources": [],
                "disclaimer": DISCLAIMER_TEXT,
            }

        top_src = sources[0]
        med_doc = (
            self._bm25_index.documents[top_src["doc_id"]] if self._bm25_index else None
        )
        med_name = med_doc.title if med_doc else top_src["title"]
        in_kit = False
        if user_kit_names:
            in_kit = any(med_name.lower() in k.lower() for k in user_kit_names)

        return {
            "status": "success",
            "emergency_mode": False,
            "message": full_text,
            "recommendation": {
                "medicine_name": med_name,
                "in_user_kit": in_kit,
                "dosage": med_doc.dosage if med_doc else "По инструкции",
                "contraindications": (
                    ", ".join(med_doc.contraindications)
                    if med_doc
                    else "См. инструкцию"
                ),
                "warnings": (
                    ", ".join(med_doc.interactions)
                    if med_doc
                    else "Не превышать дозировку"
                ),
            },
            "sources": sources,
            "disclaimer": DISCLAIMER_TEXT,
        }

    async def shutdown(self) -> None:
        async with self._lock:
            for task in self._dialog_chains.values():
                task.cancel()
        await self._broker.shutdown()
