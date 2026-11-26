"""Hybrid search (BM25 + Dense Vector + RRF), query expansion, and fuzzy trigram matching."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from medai.rag.analyzer import MorphAnalyzer, TextAnalyzer, normalize_text
from medai.rag.embeddings import (
    EmbeddingProvider,
    LocalCharNgramEmbedder,
    cosine_similarity,
)
from medai.rag.index import InMemoryBm25Index
from medai.rag.models import MedicineDocument, SearchResult

__all__ = [
    "HybridRagIndex",
    "expand_medical_query",
    "reciprocal_rank_fusion",
    "trigram_similarity",
]

# Colloquial Russian medical synonyms & abbreviations for Query Expansion
MEDICAL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "температура": ("жар", "лихорадка", "озноб", "орви", "грипп"),
    "жар": ("температура", "лихорадка", "жаропонижающее"),
    "лихорадка": ("температура", "жар"),
    "голова": ("головная боль", "мигрень", "виски", "обезболивающее"),
    "мигрень": ("головная боль", "обезболивающее"),
    "зуб": ("зубная боль", "челюсть", "обезболивающее"),
    "живот": ("спазм", "колики", "брюшной", "спазмолитик", "жкт"),
    "желудок": ("жкт", "изжога", "тяжесть", "панкреатин", "омепразол"),
    "жкт": ("желудок", "кишечник", "изжога", "тяжесть", "диарея"),
    "понос": ("диарея", "жидкий стул", "расстройство", "смекта", "полисорб"),
    "диарея": ("жидкий стул", "расстройство", "энтеросорбент"),
    "отравление": ("токсины", "диарея", "сорбент", "полисорб", "активированный уголь"),
    "рвота": ("тошнота", "отравление", "обезвоживание"),
    "тошнота": ("отравление", "рвота", "желудок"),
    "изжога": ("кислотность", "отрыжка", "антацид", "ренни", "омепразол"),
    "горло": ("першение", "глотать", "тонзиллит", "стрепсилс"),
    "насморк": ("нос", "заложенность", "ринит", "снуп"),
    "аллергия": ("зуд", "сыпь", "чихание", "антигистаминный", "поллиноз"),
    "крапивница": ("аллергия", "зуд", "сыпь"),
    "порез": ("рана", "ссадина", "кровотечение", "антисептик", "хлоргексидин"),
    "рана": ("порез", "ссадина", "дезинфекция", "хлоргексидин", "перекись"),
    "кашель": ("мокрота", "бронхит", "ацц"),
    "сердце": ("стенокардия", "давящая боль", "нитроглицерин"),
    "нпвп": ("ибупрофен", "обезболивающее", "противовоспалительное"),
    "орви": ("простуда", "грипп", "температура", "насморк"),
    "но-шпа": ("дротаверин", "спазм"),
    "нурофен": ("ибупрофен", "обезболивающее"),
}


def expand_medical_query(query: str) -> str:
    """Append domain-relevant medical synonyms and expanded abbreviations."""
    normalized = normalize_text(query)
    if not normalized:
        return query
    words = normalized.split()
    additions: list[str] = []
    seen = set(words)

    for word in words:
        for key, synonyms in MEDICAL_SYNONYMS.items():
            if word == key or (len(word) >= 4 and word.startswith(key[:4])):
                for syn in synonyms:
                    if syn not in seen:
                        additions.append(syn)
                        seen.add(syn)

    if not additions:
        return query
    return f"{query} {' '.join(additions[:8])}"


def _trigrams(text: str) -> set[str]:
    norm = f"  {normalize_text(text)}  "
    if len(norm) < 3:
        return set()
    return {norm[i : i + 3] for i in range(len(norm) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    """Compute Dice/Jaccard trigram similarity compatible with pg_trgm semantics."""
    ta = _trigrams(a)
    tb = _trigrams(b)
    if not ta or not tb:
        return 0.0
    union = len(ta | tb)
    if union == 0:
        return 0.0
    return len(ta & tb) / union


def reciprocal_rank_fusion(
    *ranked_lists: Sequence[str],
    k: int = 60,
    top_k: int = 5,
) -> list[tuple[str, float]]:
    """Combine multiple ranked document ID lists via Reciprocal Rank Fusion."""
    rrf_scores: dict[str, float] = {}
    for ranking in ranked_lists:
        for rank_pos, doc_id in enumerate(ranking, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank_pos)

    ordered = sorted(rrf_scores.items(), key=lambda item: (-item[1], item[0]))
    return ordered[:top_k]


class HybridRagIndex:
    """Combined BM25 + Dense Vector index with RRF fusion and fuzzy suggestions."""

    def __init__(
        self,
        bm25_index: InMemoryBm25Index,
        analyzer: TextAnalyzer | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.bm25 = bm25_index
        self.analyzer = analyzer or MorphAnalyzer()
        self.embedder = embedder or LocalCharNgramEmbedder()
        self._doc_vectors: dict[str, list[float]] = {}
        self._rebuild_vectors()

    def _rebuild_vectors(self) -> None:
        self._doc_vectors.clear()
        for doc_id, doc in self.bm25.documents.items():
            self._doc_vectors[doc_id] = self.embedder.embed(doc.full_text())

    @property
    def documents(self) -> Mapping[str, MedicineDocument]:
        return self.bm25.documents

    def search_bm25(
        self,
        query: str,
        top_k: int = 5,
        *,
        expand: bool = False,
    ) -> list[SearchResult]:
        q_text = expand_medical_query(query) if expand else query
        terms = self.analyzer.terms(q_text)
        return self.bm25.search(terms, top_k=top_k)

    def search_dense(
        self,
        query: str,
        top_k: int = 5,
        *,
        min_similarity: float = 0.08,
    ) -> list[SearchResult]:
        if not self._doc_vectors:
            return []
        q_vec = self.embedder.embed(expand_medical_query(query))
        scored: list[tuple[str, float]] = []
        for doc_id, d_vec in self._doc_vectors.items():
            sim = cosine_similarity(q_vec, d_vec)
            if sim >= min_similarity:
                scored.append((doc_id, sim))
        scored.sort(key=lambda item: (-item[1], item[0]))

        results: list[SearchResult] = []
        for doc_id, sim in scored[:top_k]:
            doc = self.bm25.documents[doc_id]
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    title=doc.title,
                    score=round(sim, 4),
                    document=doc,
                )
            )
        return results

    def search_hybrid(
        self,
        query: str,
        top_k: int = 5,
        *,
        rrf_k: int = 60,
        bm25_min_gate: float = 0.0,
    ) -> list[SearchResult]:
        """Search using BM25 (raw + expanded + fuzzy) and Dense Vector fused via RRF."""
        bm25_raw_terms = self.analyzer.terms(query)
        bm25_raw_res = self.bm25.search(bm25_raw_terms, top_k=max(top_k * 2, 10))
        bm25_exp_terms = self.analyzer.terms(expand_medical_query(query))
        bm25_exp_res = self.bm25.search(bm25_exp_terms, top_k=max(top_k * 2, 10))
        dense_res = self.search_dense(query, top_k=max(top_k * 2, 10))

        # Typo-tolerant boost for direct drug name mentions
        fuzzy_ids = [doc.id for doc in self.suggest_fuzzy(query, threshold=0.25, limit=3)]
        for tok in normalize_text(query).split():
            if len(tok) >= 5:
                for doc in self.suggest_fuzzy(tok, threshold=0.32, limit=2):
                    if doc.id not in fuzzy_ids:
                        fuzzy_ids.append(doc.id)

        top_bm25 = max(
            bm25_raw_res[0].score if bm25_raw_res else 0.0,
            bm25_exp_res[0].score if bm25_exp_res else 0.0,
        )
        top_dense = dense_res[0].score if dense_res else 0.0
        if (
            bm25_min_gate > 0.0
            and top_bm25 < bm25_min_gate
            and top_dense < 0.25
            and not fuzzy_ids
        ):
            return []

        bm25_ids = [r.doc_id for r in (bm25_exp_res or bm25_raw_res)]
        dense_ids = [r.doc_id for r in dense_res]

        fused = reciprocal_rank_fusion(
            bm25_ids, dense_ids, fuzzy_ids, k=rrf_k, top_k=top_k
        )
        results: list[SearchResult] = []
        for doc_id, rrf_score in fused:
            doc = self.bm25.documents[doc_id]
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    title=doc.title,
                    score=round(rrf_score * 100.0, 4),
                    document=doc,
                )
            )
        return results

    def suggest_fuzzy(
        self, name_query: str, *, threshold: float = 0.25, limit: int = 5
    ) -> list[MedicineDocument]:
        """Find closest medicines by trigram similarity (typo-tolerant fallback)."""
        q = normalize_text(name_query)
        if not q:
            return []
        scored: list[tuple[float, MedicineDocument]] = []
        for doc in self.bm25.documents.values():
            best = max(
                trigram_similarity(q, doc.title),
                trigram_similarity(q, doc.inn),
            )
            if best >= threshold:
                scored.append((best, doc))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [doc for _, doc in scored[:limit]]
