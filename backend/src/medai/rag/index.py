"""In-memory BM25 index and package loader for MedAI."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import yaml

from medai.rag.analyzer import TextAnalyzer
from medai.rag.bm25 import Bm25Params, rank, score
from medai.rag.models import MedicineDocument, MedicinePackage, SearchResult

__all__ = [
    "InMemoryBm25Index",
    "find_data_dir",
    "load_package_from_yaml",
]


def find_data_dir() -> Path:
    """Find data directory robustly in dev, worktree, and docker container."""
    cur = Path(__file__).resolve().parent
    for p in (cur, *cur.parents):
        candidate = p / "data"
        if candidate.is_dir():
            return candidate
    cwd = Path.cwd().resolve()
    for p in (cwd, *cwd.parents):
        candidate = p / "data"
        if candidate.is_dir():
            return candidate
    return Path("/app/data")


class InMemoryBm25Index:
    def __init__(self, params: Bm25Params | None = None) -> None:
        self.params = Bm25Params() if params is None else params
        self.documents: dict[str, MedicineDocument] = {}
        self.postings: dict[str, dict[str, int]] = {}
        self.lengths: dict[str, int] = {}
        self._total_length: int = 0

    @property
    def document_count(self) -> int:
        return len(self.documents)

    @property
    def average_length(self) -> float:
        if not self.documents:
            return 0.0
        return self._total_length / len(self.documents)

    def add_document(self, doc: MedicineDocument, terms: Sequence[str]) -> None:
        doc_id = doc.id
        self.documents[doc_id] = doc
        length = len(terms)
        self.lengths[doc_id] = length
        self._total_length += length

        term_counts = Counter(terms)
        for term, count in term_counts.items():
            self.postings.setdefault(term, {})[doc_id] = count

    def search(
        self,
        query_terms: Sequence[str],
        top_k: int = 5,
    ) -> list[SearchResult]:
        if not self.documents or not query_terms:
            return []

        scores = score(
            query_terms=query_terms,
            postings=self.postings,
            lengths=self.lengths,
            n_documents=len(self.documents),
            average_length=self.average_length,
            params=self.params,
        )

        ranked_ids = rank(scores, top_k=top_k)
        results: list[SearchResult] = []
        for doc_id in ranked_ids:
            doc = self.documents[doc_id]
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    title=doc.title,
                    score=round(scores[doc_id], 4),
                    document=doc,
                )
            )
        return results


def load_package_from_yaml(path: Path, analyzer: TextAnalyzer) -> InMemoryBm25Index:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    pkg = MedicinePackage.model_validate(data)
    index = InMemoryBm25Index()

    for doc in pkg.medicines:
        terms = analyzer.terms(doc.full_text())
        index.add_document(doc, terms)

    return index
