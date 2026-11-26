"""Structure-aware and contextual chunking for MedAI medical documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from medai.rag.analyzer import TextAnalyzer
from medai.rag.models import MedicineDocument

__all__ = [
    "ChunkingConfig",
    "MedicineChunk",
    "chunk_medicine_document",
    "chunk_text",
]

_SENTENCE_BREAK = re.compile(r"(?<=[.!?…])\s+")
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_WORD = re.compile(r"\S+")


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    min_words: int = 30
    target_words: int = 120
    max_words: int = 200
    overlap_words: int = 25

    def __post_init__(self) -> None:
        if self.min_words <= 0:
            raise ValueError("min_words must be positive")
        if not self.min_words <= self.target_words <= self.max_words:
            raise ValueError("expected min_words <= target_words <= max_words")
        if self.overlap_words < 0:
            raise ValueError("overlap_words must not be negative")
        if self.overlap_words >= self.target_words:
            raise ValueError("overlap_words must be smaller than target_words")


class MedicineChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    position: int
    section: str
    text: str
    term_count: int


def _count_words(text: str) -> int:
    return len(_WORD.findall(text))


def _sentences(text: str, max_words: int) -> list[str]:
    result: list[str] = []
    for paragraph in _PARAGRAPH_BREAK.split(text.strip()):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        for sentence in _SENTENCE_BREAK.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            words = _WORD.findall(sentence)
            if len(words) <= max_words:
                result.append(sentence)
            else:
                for start in range(0, len(words), max_words):
                    result.append(" ".join(words[start : start + max_words]))
    return result


def chunk_text(text: str, config: ChunkingConfig | None = None) -> tuple[str, ...]:
    """Split prose into overlapping sentence-aligned chunks."""
    settings = config or ChunkingConfig()
    sentences = _sentences(text, settings.max_words)
    if not sentences:
        return ()

    chunks: list[str] = []
    current: list[str] = []

    def words_count(items: list[str]) -> int:
        return sum(_count_words(item) for item in items)

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(" ".join(current).strip())
            current = []

    def overlap() -> list[str]:
        if not current or settings.overlap_words <= 0:
            return []
        tail: list[str] = []
        total = 0
        for sent in reversed(current):
            size = _count_words(sent)
            if tail and total + size > settings.overlap_words:
                break
            if not tail and size > settings.overlap_words:
                break
            tail.append(sent)
            total += size
        return list(reversed(tail))

    for index, sentence in enumerate(sentences):
        has_next = index + 1 < len(sentences)
        sent_words = _count_words(sentence)

        if current and words_count(current) + sent_words > settings.max_words:
            prev = overlap() if has_next else []
            flush()
            current = prev

        if current and words_count(current) + sent_words > settings.max_words:
            flush()

        current.append(sentence)
        if words_count(current) >= settings.target_words:
            prev = overlap() if has_next else []
            flush()
            current = prev

    flush()
    if len(chunks) >= 2 and _count_words(chunks[-1]) < settings.min_words:
        if _count_words(chunks[-2]) + _count_words(chunks[-1]) <= settings.max_words:
            chunks[-2] = f"{chunks[-2]} {chunks[-1]}"
            chunks.pop()
    return tuple(chunks)


def chunk_medicine_document(
    doc: MedicineDocument,
    analyzer: TextAnalyzer,
) -> list[MedicineChunk]:
    """Split a structured medicine card into contextualized section chunks.

    Each chunk includes a Contextual Retrieval header so isolated sections
    retain the drug name, INN, ATC code, and therapeutic category.
    """
    header = (
        f"Препарат: {doc.title} ({doc.inn}), АТХ {doc.atc_code}, "
        f"категория: {doc.category}, формы: {', '.join(doc.forms)}."
    )

    sections: list[tuple[str, str]] = [
        (
            "indications",
            f"{header} Показания к применению и симптомы: {', '.join(doc.indications)}.",
        ),
        (
            "dosage",
            f"{header} Режим дозирования: {doc.dosage}",
        ),
    ]
    if doc.contraindications:
        sections.append(
            (
                "contraindications",
                f"{header} Противопоказания: {', '.join(doc.contraindications)}.",
            )
        )
    if doc.interactions or doc.emergency_flags:
        extra_parts: list[str] = []
        if doc.interactions:
            extra_parts.append(f"Взаимодействия: {', '.join(doc.interactions)}.")
        if doc.emergency_flags:
            extra_parts.append(
                f"Экстренные предупреждения: {', '.join(doc.emergency_flags)}."
            )
        sections.append(("interactions", f"{header} {' '.join(extra_parts)}"))

    chunks: list[MedicineChunk] = []
    for pos, (section_name, body) in enumerate(sections):
        terms = analyzer.terms(body)
        chunks.append(
            MedicineChunk(
                doc_id=doc.id,
                position=pos,
                section=section_name,
                text=body,
                term_count=len(terms),
            )
        )
    return chunks
