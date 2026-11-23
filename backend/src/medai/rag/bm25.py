"""BM25 ranking function implementation following BMSTU NIRS specification."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "Bm25Params",
    "Lengths",
    "Postings",
    "idf",
    "rank",
    "score",
    "term_score",
    "unique_terms",
]

# Postings: term -> {doc_id: term_frequency}
Postings = Mapping[str, Mapping[str, int]]
Lengths = Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Bm25Params:
    """Parameters of BM25 ranking function from BMSTU NIRS course specification."""

    k1: float = 1.5
    b: float = 0.75

    def __post_init__(self) -> None:
        if self.k1 <= 0:
            raise ValueError("k1 must be positive")
        if not (0 <= self.b <= 1):
            raise ValueError("b must be between 0 and 1")


def idf(n_documents: int, document_frequency: int) -> float:
    """Robertson-Spärck Jones IDF with +0.5 smoothing from NIRS manual (1.3)."""
    if n_documents <= 0 or document_frequency <= 0:
        return 0.0
    numerator = n_documents - document_frequency + 0.5
    denominator = document_frequency + 0.5
    return math.log(1.0 + numerator / denominator)


def term_score(
    term_frequency: int,
    document_length: int,
    average_length: float,
    params: Bm25Params,
) -> float:
    """Contribution of term frequency and document length penalty."""
    if term_frequency <= 0 or document_length <= 0 or average_length <= 0:
        return 0.0
    length_ratio = document_length / average_length
    normalization = params.k1 * (1.0 - params.b + params.b * length_ratio)
    return term_frequency * (params.k1 + 1.0) / (term_frequency + normalization)


def unique_terms(terms: Sequence[str]) -> tuple[str, ...]:
    """Unique terms from query in order of appearance."""
    return tuple(dict.fromkeys(term for term in terms if term))


def score(
    query_terms: Sequence[str],
    postings: Postings,
    lengths: Lengths,
    n_documents: int,
    average_length: float,
    params: Bm25Params,
) -> dict[str, float]:
    """Score every document that shares at least one term with the query."""
    scores: dict[str, float] = {}
    if n_documents <= 0 or average_length <= 0:
        return scores

    for term in unique_terms(query_terms):
        term_postings = postings.get(term)
        if not term_postings:
            continue
        term_idf = idf(n_documents, len(term_postings))
        if term_idf <= 0:
            continue
        for doc_id, tf in term_postings.items():
            doc_len = lengths.get(doc_id, 0)
            contrib = term_idf * term_score(tf, doc_len, average_length, params)
            if contrib <= 0:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + contrib
    return scores


def rank(
    scores: Mapping[str, float],
    top_k: int,
) -> tuple[str, ...]:
    """Return top_k document IDs with positive score, descending order."""
    if top_k <= 0:
        return ()
    positive_docs = [doc_id for doc_id, val in scores.items() if val > 0]
    ranked = sorted(positive_docs, key=lambda doc_id: (-scores[doc_id], doc_id))
    return tuple(ranked[:top_k])
