"""Medical & Clinical Safety tools for MedAI Agent and deterministic fallback."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from medai.agent.tools import Tool
from medai.rag.analyzer import normalize_text
from medai.rag.hybrid import HybridRagIndex
from medai.rag.models import MedicineDocument

__all__ = [
    "CheckInteractionsTool",
    "GetSafetyProfileTool",
    "LookupMedicineTool",
    "SearchMedicinesTool",
    "analyze_medicine_safety",
]

NSAID_CLASSES = frozenset({"ибупрофен", "напроксен", "нимесулид", "нимесил", "аспирин", "ацетилсалициловая", "кеторолак", "кетанов", "диклофенак"})
VASOCONSTRICTORS = frozenset({"фенилэфрин", "ксилометазолин", "снуп", "терафлю", "колдрекс", "називин", "отривин"})


def analyze_medicine_safety(
    docs: list[MedicineDocument],
    health_profile: dict[str, Any] | None = None,
    user_kit_items: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Cross-check candidate medicines against allergies, chronic conditions, age, weight, duplicates, and expiry."""
    warnings: list[str] = []
    profile = health_profile or {}
    allergies = [normalize_text(str(a)) for a in profile.get("allergies", []) if str(a).strip()]
    chronic = [normalize_text(str(c)) for c in profile.get("chronic_diseases", profile.get("chronic", [])) if str(c).strip()]
    age = int(profile.get("age", 25) or 25)
    raw_weight = profile.get("weight_kg", profile.get("weight", 70))
    try:
        weight_kg = float(raw_weight) if raw_weight is not None else 70.0
    except (TypeError, ValueError):
        weight_kg = 70.0

    # 1. Check allergy, chronic disease, age and weight conflicts per document
    seen_inns: dict[str, list[str]] = {}
    for doc in docs:
        doc_blob = normalize_text(
            f"{doc.title} {doc.inn} {doc.category} {' '.join(doc.contraindications)} {doc.dosage}"
        )
        contra_blob = normalize_text(" ".join(doc.contraindications))
        # Split compound INNs (e.g. "Парацетамол + Напроксен + ...")
        inn_parts = [normalize_text(p) for p in doc.inn.split("+") if p.strip()]
        for inn in inn_parts:
            seen_inns.setdefault(inn, []).append(doc.title)

        is_nsaid = any(n in doc_blob for n in NSAID_CLASSES)
        is_vaso = any(v in doc_blob for v in VASOCONSTRICTORS)
        has_paracetamol = "парацетамол" in doc_blob

        for allergy in allergies:
            if allergy and (
                allergy in doc_blob
                or any(allergy in part or part in allergy for part in inn_parts)
                or ("нпвп" in allergy and is_nsaid)
                or ("пенициллин" in allergy and "пенициллин" in doc_blob)
                or ("сульфан" in allergy and "сульфан" in doc_blob)
            ):
                warnings.append(
                    f"ВНИМАНИЕ (АЛЛЕРГИЯ): Препарат «{doc.title}» может содержать или "
                    f"пересекаться с аллергеном из вашей медкарты ({allergy}). Прием противопоказан!"
                )

        # Chronic disease conflicts
        for disease in chronic:
            if any(k in disease for k in ("гастрит", "язва", "жкт", "гэрб", "рефлюкс")):
                if is_nsaid or "язва" in contra_blob:
                    warnings.append(
                        f"ВНИМАНИЕ (МЕДКАРТА — {disease}): «{doc.title}» содержит компоненты "
                        f"(НПВП/раздражители слизистой), нежелательные при заболевании «{disease}»."
                    )
            if any(k in disease for k in ("печен", "цирроз", "гепатит")) and (
                has_paracetamol or "печен" in contra_blob
            ):
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): «{doc.title}» требует осторожности "
                    f"при патологиях печени ({weight_kg:g} кг, {age} лет)."
                )
            if any(k in disease for k in ("астма", "бронх", "хобл")) and (
                is_nsaid or "астм" in contra_blob
            ):
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): проверьте переносимость «{doc.title}» при заболеваниях дыхательных путей ({disease})."
                )
            if any(k in disease for k in ("гипертон", "давлен", "ибс", "аритм", "тахикард", "серд")) and (
                is_vaso or is_nsaid or any(k in contra_blob for k in ("гипертенз", "ритм", "серд", "тахикард"))
            ):
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): «{doc.title}» может повышать давление или нагружать сердце при «{disease}»."
                )
            if any(k in disease for k in ("почк", "почеч", "пиелонефр", "мочекамен", "хпн")) and (
                is_nsaid or "почеч" in contra_blob or "нефрокальц" in contra_blob
            ):
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): «{doc.title}» требует корректировки или исключения при «{disease}»."
                )
            if "диабет" in disease and ("диабет" in contra_blob or "сахар" in doc_blob or "порошок" in doc_blob):
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): проверьте состав «{doc.title}» на содержание сахара и влияние на гликемию."
                )
            if "глауком" in disease and "глауком" in contra_blob:
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): «{doc.title}» противопоказан при глаукоме."
                )
            if any(k in disease for k in ("беремен", "лактац", "гв")) and (
                "беремен" in contra_blob or "лактац" in contra_blob or is_nsaid
            ):
                warnings.append(
                    f"ВНИМАНИЕ (МЕДКАРТА — {disease}): «{doc.title}» может быть противопоказан при «{disease}»."
                )

        # Age & weight safety checks
        if age < 12 and ("старше 12" in doc_blob or "старше 18" in doc_blob or "до 12" in contra_blob or "до 18" in contra_blob):
            warnings.append(
                f"ВОЗРАСТНОЕ ОГРАНИЧЕНИЕ ({age} лет, {weight_kg:g} кг): «{doc.title}» не рекомендован без педиатра."
            )
        elif age < 15 and ("до 15" in contra_blob or "метамизол" in doc_blob or "ацетилсалицил" in doc_blob):
            warnings.append(
                f"ВОЗРАСТНОЕ ОГРАНИЧЕНИЕ ({age} лет): «{doc.title}» не применяется до 15 лет."
            )
        elif age >= 65 and (is_nsaid or "хлоропирамин" in doc_blob or "фенобарбитал" in doc_blob):
            warnings.append(
                f"ВОЗРАСТ ({age} лет): при возрасте 65+ препарат «{doc.title}» применяйте с осторожностью в минимальной эффективной дозе."
            )

        if has_paracetamol and (weight_kg < 50 or age < 12):
            min_d = round(10 * weight_kg)
            max_d = round(15 * weight_kg)
            warnings.append(
                f"УЧЕТ ВЕСА ({weight_kg:g} кг): ориентировочная разовая доза парацетамола 10–15 мг/кг составляет {min_d}–{max_d} мг; не принимайте дозу выше этого предела."
            )
        elif "ибупрофен" in inn_parts and (weight_kg < 50 or age < 12):
            min_d = round(5 * weight_kg)
            max_d = round(10 * weight_kg)
            warnings.append(
                f"УЧЕТ ВЕСА ({weight_kg:g} кг): ориентировочная разовая доза ибупрофена 5–10 мг/кг составляет {min_d}–{max_d} мг."
            )
        elif weight_kg < 45 and age >= 12:
            warnings.append(
                f"МАЛАЯ МАССА ТЕЛА ({weight_kg:g} кг): выбирайте минимальную разовую дозировку препарата «{doc.title}»."
            )

        # Document-level interactions
        if len(docs) > 1:
            other_titles = [d for d in docs if d.id != doc.id]
            for inter in doc.interactions:
                norm_inter = normalize_text(inter)
                for other in other_titles:
                    if any(
                        tok in norm_inter
                        for tok in normalize_text(other.inn).split()
                        if len(tok) >= 5
                    ):
                        warnings.append(
                            f"ВЗАИМОДЕЙСТВИЕ («{doc.title}» + «{other.title}»): {inter}."
                        )

    # 2. Check duplicate active ingredients (e.g. Paracetamol + Theraflu)
    for inn, titles in seen_inns.items():
        if len(titles) > 1:
            warnings.append(
                f"РИСК ПЕРЕДОЗИРОВКИ: Одинаковое действующее вещество «{inn}» "
                f"содержится сразу в нескольких препаратах: {', '.join(titles)}. "
                f"Не принимайте их одновременно!"
            )

    # 3. Check expired kit items
    if user_kit_items:
        for item in user_kit_items:
            if item.get("is_expired"):
                name = item.get("name", "Препарат")
                if any(normalize_text(name) in normalize_text(d.title) or normalize_text(d.inn) in normalize_text(name) for d in docs):
                    warnings.append(
                        f"ПРОСРОЧЕНО В АПТЕЧКЕ: «{name}» имеет истекший срок годности ({item.get('expiry')}). Использовать запрещено!"
                    )

    # Deduplicate preserving order
    return list(dict.fromkeys(warnings))


class SearchMedicinesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=300)
    mode: Literal["all", "indications", "dosage", "contraindications"] = "all"
    top_k: int = Field(default=3, ge=1, le=5)


class SearchMedicinesTool(Tool):
    name: ClassVar[str] = "search_medicines"
    description: ClassVar[str] = (
        "Hybrid search (BM25 + Semantic RRF) across official Ministry of Health medicine instructions. "
        "Returns top matching medicines with indications, dosage, contraindications, and doc_id [Dxx]."
    )
    arguments_model: ClassVar[type[BaseModel]] = SearchMedicinesArgs

    def __init__(self, hybrid_index: HybridRagIndex) -> None:
        self._index = hybrid_index

    async def execute(self, arguments: BaseModel) -> dict[str, Any]:
        assert isinstance(arguments, SearchMedicinesArgs)
        hits = self._index.search_hybrid(
            arguments.query,
            top_k=arguments.top_k,
            bm25_min_gate=5.0,
        )
        if not hits:
            return {"status": "empty", "results": []}

        items: list[dict[str, Any]] = []
        for hit in hits:
            doc = hit.document
            entry: dict[str, Any] = {
                "doc_id": doc.id,
                "title": doc.title,
                "inn": doc.inn,
                "category": doc.category,
                "score": hit.score,
            }
            if arguments.mode in ("all", "indications"):
                entry["indications"] = doc.indications[:5]
            if arguments.mode in ("all", "dosage"):
                entry["dosage"] = doc.dosage
            if arguments.mode in ("all", "contraindications"):
                entry["contraindications"] = doc.contraindications
                entry["interactions"] = doc.interactions
            items.append(entry)
        return {"status": "found", "results": items}


class LookupMedicineArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class LookupMedicineTool(Tool):
    name: ClassVar[str] = "lookup_medicine"
    description: ClassVar[str] = (
        "Exact and typo-tolerant (fuzzy) lookup of a medicine by brand name or INN."
    )
    arguments_model: ClassVar[type[BaseModel]] = LookupMedicineArgs

    def __init__(self, hybrid_index: HybridRagIndex) -> None:
        self._index = hybrid_index

    async def execute(self, arguments: BaseModel) -> dict[str, Any]:
        assert isinstance(arguments, LookupMedicineArgs)
        q = normalize_text(arguments.name)
        exact = [
            doc
            for doc in self._index.documents.values()
            if q in normalize_text(doc.title) or q in normalize_text(doc.inn)
        ]
        if not exact:
            exact = self._index.suggest_fuzzy(arguments.name, threshold=0.25, limit=3)
        if not exact:
            return {"status": "not_found", "medicines": []}
        return {
            "status": "found",
            "medicines": [
                {
                    "doc_id": d.id,
                    "title": d.title,
                    "inn": d.inn,
                    "category": d.category,
                    "indications": d.indications,
                    "dosage": d.dosage,
                    "contraindications": d.contraindications,
                    "interactions": d.interactions,
                }
                for d in exact[:3]
            ],
        }


class EmptyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetSafetyProfileTool(Tool):
    name: ClassVar[str] = "get_user_safety_context"
    description: ClassVar[str] = (
        "Retrieve current user's first aid kit inventory (with expiry status) and health profile "
        "(age, weight, allergies, chronic diseases)."
    )
    arguments_model: ClassVar[type[BaseModel]] = EmptyArgs

    def __init__(self, context_snapshot: dict[str, Any]) -> None:
        self._snapshot = context_snapshot

    async def execute(self, arguments: BaseModel) -> dict[str, Any]:
        return self._snapshot


class CheckInteractionsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medicine_names: list[str] = Field(min_length=1, max_length=10)


class CheckInteractionsTool(Tool):
    name: ClassVar[str] = "check_drug_interactions"
    description: ClassVar[str] = (
        "Check candidate medicines against user allergies, chronic diseases, expiry dates, "
        "and drug-to-drug / duplicate-substance overdose risks."
    )
    arguments_model: ClassVar[type[BaseModel]] = CheckInteractionsArgs

    def __init__(
        self,
        hybrid_index: HybridRagIndex,
        safety_snapshot: dict[str, Any],
    ) -> None:
        self._index = hybrid_index
        self._snapshot = safety_snapshot

    async def execute(self, arguments: BaseModel) -> dict[str, Any]:
        assert isinstance(arguments, CheckInteractionsArgs)
        docs: list[MedicineDocument] = []
        for name in arguments.medicine_names:
            q = normalize_text(name)
            matched = [
                d
                for d in self._index.documents.values()
                if q in normalize_text(d.title) or q in normalize_text(d.inn)
            ]
            if not matched:
                matched = self._index.suggest_fuzzy(name, threshold=0.25, limit=1)
            for d in matched[:1]:
                if all(existing.id != d.id for existing in docs):
                    docs.append(d)

        warnings = analyze_medicine_safety(
            docs,
            health_profile=self._snapshot.get("health_profile"),
            user_kit_items=self._snapshot.get("kit_items"),
        )
        return {
            "checked_medicines": [d.title for d in docs],
            "warnings": warnings,
            "is_safe": len(warnings) == 0,
        }
