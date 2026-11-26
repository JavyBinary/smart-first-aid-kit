"""Answerers and RAGAS-style evaluation helpers for MedAI benchmark."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from medai.rag.analyzer import normalize_text
from medai.rag.models import SearchResult

__all__ = [
    "BenchmarkAnswerer",
    "DeterministicRagAnswerer",
    "LiteLLMNotConfiguredError",
    "compute_faithfulness",
]

MIN_BM25_RELEVANCE_SCORE = 5.5


class LiteLLMNotConfiguredError(RuntimeError):
    """Raised when live LLM benchmark is requested without API configuration."""


class BenchmarkAnswerer(Protocol):
    async def generate(
        self,
        question: str,
        hits: Sequence[SearchResult],
    ) -> str: ...


class DeterministicRagAnswerer:
    """Grounded offline answerer summarizing retrieved medicine documents without hallucinations."""

    def __init__(self, *, min_score: float = 0.0) -> None:
        self._min_score = min_score

    def generate_sync(
        self,
        question: str,
        hits: Sequence[SearchResult],
    ) -> str:
        """Synchronously build grounded summary from retrieved hits."""
        if not hits or hits[0].score < self._min_score:
            return (
                "В документах нет этой информации. Препарат или заболевание "
                "не найдено в реестре домашней аптечки."
            )

        lines: list[str] = []
        for r in hits[:3]:
            doc = r.document
            indications = ", ".join(doc.indications[:4])
            contraindications = (
                ", ".join(doc.contraindications[:3])
                if doc.contraindications
                else "см. инструкцию"
            )
            lines.append(
                f"[{doc.id}] {doc.title} ({doc.inn}): показания — {indications}. "
                f"Дозировка: {doc.dosage} Противопоказания: {contraindications}."
            )
        return " ".join(lines)

    async def generate(
        self,
        question: str,
        hits: Sequence[SearchResult],
    ) -> str:
        return self.generate_sync(question, hits)


def compute_faithfulness(
    answer: str,
    hits: Sequence[SearchResult],
) -> float:
    """Estimate claim grounding against retrieved context sentences/fields."""
    norm_ans = normalize_text(answer)
    if not norm_ans:
        return 0.0
    # Refusal answers are trivially faithful to absence of context
    if any(
        marker in norm_ans
        for marker in ("нет этой информации", "нет информации", "не найдено", "нет сведений")
    ):
        return 1.0
    if not hits:
        return 0.0

    context_blob = normalize_text(
        " ".join(f"[{r.doc_id}] {r.document.full_text()}" for r in hits)
    )
    context_tokens = set(context_blob.split())

    # Split answer into simple factual clauses
    clauses = [
        c.strip()
        for c in norm_ans.replace(";", ".").split(".")
        if len(c.strip().split()) >= 3
    ]
    if not clauses:
        return 1.0

    grounded = 0
    for clause in clauses:
        words = [w for w in clause.split() if len(w) >= 4]
        if not words:
            grounded += 1
            continue
        overlap = sum(1 for w in words if w in context_tokens)
        if overlap / len(words) >= 0.45:
            grounded += 1

    return round(grounded / len(clauses), 4)
