"""PostgreSQL storage and set-based BM25/Hybrid index for MedAI knowledge base."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import yaml
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from medai.db.tables import (
    rag_bm25_index,
    rag_chunks,
    rag_loads,
    rag_medicines,
    rag_postings,
    rag_revisions,
    rag_stats,
    rag_terms,
)
from medai.rag.analyzer import MorphAnalyzer, TextAnalyzer, normalize_text
from medai.rag.bm25 import Bm25Params, unique_terms
from medai.rag.chunking import chunk_medicine_document
from medai.rag.embeddings import (
    EmbeddingProvider,
    LocalCharNgramEmbedder,
    cosine_similarity,
)
from medai.rag.hybrid import HybridRagIndex, trigram_similarity
from medai.rag.index import InMemoryBm25Index
from medai.rag.models import MedicineDocument, MedicinePackage, SearchResult

__all__ = ["LoadSummary", "PostgresRagStore"]

logger = logging.getLogger(__name__)
_RAG_LOCK_KEY = int.from_bytes(b"medairag", "big", signed=True)


class LoadSummary:
    def __init__(
        self,
        *,
        load_id: int,
        document_count: int,
        chunk_count: int,
        term_count: int,
    ) -> None:
        self.load_id = load_id
        self.document_count = document_count
        self.chunk_count = chunk_count
        self.term_count = term_count


def _row_to_document(row: Any) -> MedicineDocument:
    return MedicineDocument(
        id=row.id,
        title=row.title,
        inn=row.inn,
        atc_code=row.atc_code,
        category=row.category,
        forms=list(row.forms) if row.forms else ["таблетки"],
        indications=list(row.indications) if row.indications else ["симптомы"],
        contraindications=(
            list(row.contraindications) if row.contraindications else []
        ),
        dosage=row.dosage_text,
        interactions=list(row.interactions) if row.interactions else [],
        emergency_flags=list(row.emergency_flags) if row.emergency_flags else [],
    )


def _doc_to_db_values(doc: MedicineDocument, now: datetime) -> dict[str, Any]:
    return {
        "id": doc.id,
        "title": doc.title,
        "inn": doc.inn,
        "atc_code": doc.atc_code,
        "category": doc.category,
        "forms": list(doc.forms),
        "indications": list(doc.indications),
        "contraindications": list(doc.contraindications),
        "dosage_text": doc.dosage,
        "interactions": list(doc.interactions),
        "emergency_flags": list(doc.emergency_flags),
        "created_at": now,
        "updated_at": now,
    }


class PostgresRagStore:
    """PostgreSQL-backed medicine knowledge store with chunked BM25 + vector index."""

    def __init__(
        self,
        engine: AsyncEngine,
        analyzer: TextAnalyzer | None = None,
        embedder: EmbeddingProvider | None = None,
        params: Bm25Params | None = None,
    ) -> None:
        self._engine = engine
        self._analyzer = analyzer or MorphAnalyzer()
        self._embedder = embedder or LocalCharNgramEmbedder()
        self._params = params or Bm25Params()

    async def _acquire_lock(self, conn: AsyncConnection) -> None:
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": _RAG_LOCK_KEY},
            )

    async def _next_revision(self, conn: AsyncConnection, doc_id: str) -> int:
        res = await conn.execute(
            select(func.coalesce(func.max(rag_revisions.c.revision), 0)).where(
                rag_revisions.c.doc_id == doc_id
            )
        )
        return int(res.scalar() or 0) + 1

    async def _record_revision(
        self,
        conn: AsyncConnection,
        doc: MedicineDocument,
        operation: str,
        now: datetime,
    ) -> None:
        rev = await self._next_revision(conn, doc.id)
        await conn.execute(
            insert(rag_revisions).values(
                doc_id=doc.id,
                revision=rev,
                operation=operation,
                snapshot=doc.model_dump(mode="json"),
                created_at=now,
            )
        )

    async def _rebuild_inverted_stats(
        self, conn: AsyncConnection, version: int
    ) -> tuple[int, int]:
        """Recompute term DF, corpus chunk count, and avgdl inside one transaction."""
        await conn.execute(delete(rag_terms))
        await conn.execute(
            text(
                "INSERT INTO rag_terms (term, df) "
                "SELECT term, count(*) FROM rag_postings GROUP BY term"
            )
        )
        await conn.execute(delete(rag_stats))
        await conn.execute(
            text(
                "INSERT INTO rag_stats (id, n_chunks, avgdl, version) "
                "SELECT 1, count(*), coalesce(avg(term_count), 0), :version "
                "FROM rag_chunks"
            ).bindparams(version=version)
        )
        chunk_count = int(
            (await conn.execute(select(func.count()).select_from(rag_chunks))).scalar()
            or 0
        )
        term_count = int(
            (await conn.execute(select(func.count()).select_from(rag_terms))).scalar()
            or 0
        )
        return chunk_count, term_count

    async def _index_document_rows(
        self,
        conn: AsyncConnection,
        doc: MedicineDocument,
        now: datetime,
    ) -> int:
        """Index doc-level rag_bm25_index + section chunks + rag_postings."""
        full_terms = self._analyzer.terms(doc.full_text())
        tf_map = dict(Counter(full_terms))
        await conn.execute(delete(rag_bm25_index).where(rag_bm25_index.c.doc_id == doc.id))
        await conn.execute(
            insert(rag_bm25_index).values(
                doc_id=doc.id,
                lemmatized_text=" ".join(full_terms),
                doc_length=len(full_terms),
                term_frequencies=tf_map,
                updated_at=now,
            )
        )

        # Clean existing chunks (cascades to rag_postings)
        await conn.execute(delete(rag_chunks).where(rag_chunks.c.doc_id == doc.id))

        chunks = chunk_medicine_document(doc, self._analyzer)
        for chunk in chunks:
            emb = self._embedder.embed(chunk.text)
            chunk_id = (
                await conn.execute(
                    insert(rag_chunks)
                    .values(
                        doc_id=chunk.doc_id,
                        position=chunk.position,
                        section=chunk.section,
                        text=chunk.text,
                        term_count=chunk.term_count,
                        embedding=emb,
                    )
                    .returning(rag_chunks.c.id)
                )
            ).scalar_one()

            chunk_tf = Counter(self._analyzer.terms(chunk.text))
            if chunk_tf:
                await conn.execute(
                    insert(rag_postings),
                    [
                        {"term": term, "chunk_id": chunk_id, "tf": count}
                        for term, count in chunk_tf.items()
                    ],
                )
        return len(chunks)

    async def replace_package(self, package: MedicinePackage) -> LoadSummary:
        """Atomically replace the entire medical corpus and inverted index."""
        now = datetime.now(UTC)
        async with self._engine.begin() as conn:
            await self._acquire_lock(conn)
            load_id = int(
                (
                    await conn.execute(
                        insert(rag_loads)
                        .values(
                            operation="load",
                            document_count=len(package.medicines),
                            started_at=now,
                        )
                        .returning(rag_loads.c.id)
                    )
                ).scalar_one()
            )

            await conn.execute(delete(rag_postings))
            await conn.execute(delete(rag_chunks))
            await conn.execute(delete(rag_bm25_index))
            await conn.execute(delete(rag_medicines))

            for doc in package.medicines:
                await conn.execute(
                    insert(rag_medicines).values(**_doc_to_db_values(doc, now))
                )
                await self._index_document_rows(conn, doc, now)
                await self._record_revision(conn, doc, "create", now)

            chunk_count, term_count = await self._rebuild_inverted_stats(
                conn, version=load_id
            )
            await conn.execute(
                update(rag_loads)
                .where(rag_loads.c.id == load_id)
                .values(
                    document_count=len(package.medicines),
                    chunk_count=chunk_count,
                    term_count=term_count,
                    finished_at=datetime.now(UTC),
                )
            )
            return LoadSummary(
                load_id=load_id,
                document_count=len(package.medicines),
                chunk_count=chunk_count,
                term_count=term_count,
            )

    async def replace_from_yaml(self, path: Any) -> LoadSummary:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        pkg = MedicinePackage.model_validate(data)
        return await self.replace_package(pkg)

    async def upsert_medicine(self, doc: MedicineDocument) -> MedicineDocument:
        """Create or update a single medicine and re-index atomically."""
        now = datetime.now(UTC)
        async with self._engine.begin() as conn:
            await self._acquire_lock(conn)
            exists = (
                await conn.execute(
                    select(rag_medicines.c.id).where(rag_medicines.c.id == doc.id)
                )
            ).first()

            load_id = int(
                (
                    await conn.execute(
                        insert(rag_loads)
                        .values(operation="load", document_count=1, started_at=now)
                        .returning(rag_loads.c.id)
                    )
                ).scalar_one()
            )

            values = _doc_to_db_values(doc, now)
            if exists is None:
                await conn.execute(insert(rag_medicines).values(**values))
                op = "create"
            else:
                values.pop("created_at")
                await conn.execute(
                    update(rag_medicines)
                    .where(rag_medicines.c.id == doc.id)
                    .values(**values)
                )
                op = "update"

            await self._index_document_rows(conn, doc, now)
            await self._record_revision(conn, doc, op, now)
            chunk_count, term_count = await self._rebuild_inverted_stats(
                conn, version=load_id
            )
            await conn.execute(
                update(rag_loads)
                .where(rag_loads.c.id == load_id)
                .values(
                    chunk_count=chunk_count,
                    term_count=term_count,
                    finished_at=datetime.now(UTC),
                )
            )
            return doc

    async def delete_medicine(self, doc_id: str) -> bool:
        """Delete a medicine with revision snapshot and inverted index rebuild."""
        now = datetime.now(UTC)
        async with self._engine.begin() as conn:
            await self._acquire_lock(conn)
            row = (
                await conn.execute(
                    select(rag_medicines).where(rag_medicines.c.id == doc_id)
                )
            ).first()
            if row is None:
                return False

            doc = _row_to_document(row)
            load_id = int(
                (
                    await conn.execute(
                        insert(rag_loads)
                        .values(operation="delete", document_count=1, started_at=now)
                        .returning(rag_loads.c.id)
                    )
                ).scalar_one()
            )
            await self._record_revision(conn, doc, "delete", now)
            await conn.execute(
                delete(rag_medicines).where(rag_medicines.c.id == doc_id)
            )
            chunk_count, term_count = await self._rebuild_inverted_stats(
                conn, version=load_id
            )
            await conn.execute(
                update(rag_loads)
                .where(rag_loads.c.id == load_id)
                .values(
                    chunk_count=chunk_count,
                    term_count=term_count,
                    finished_at=datetime.now(UTC),
                )
            )
            return True

    async def restore_revision(
        self, doc_id: str, revision: int | None = None
    ) -> MedicineDocument | None:
        """Restore a medicine document from rag_revisions."""
        async with self._engine.connect() as conn:
            stmt = select(rag_revisions).where(rag_revisions.c.doc_id == doc_id)
            if revision is not None:
                stmt = stmt.where(rag_revisions.c.revision == revision)
            else:
                stmt = stmt.order_by(rag_revisions.c.revision.desc()).limit(1)
            row = (await conn.execute(stmt)).first()
            if row is None:
                return None
            doc = MedicineDocument.model_validate(row.snapshot)

        await self.upsert_medicine(doc)
        return doc

    async def list_medicines(self) -> list[MedicineDocument]:
        stmt = select(rag_medicines).order_by(rag_medicines.c.id.asc())
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [_row_to_document(r) for r in rows]

    async def get_medicine(self, doc_id: str) -> MedicineDocument | None:
        stmt = select(rag_medicines).where(rag_medicines.c.id == doc_id)
        async with self._engine.connect() as conn:
            row = (await conn.execute(stmt)).first()
        return _row_to_document(row) if row is not None else None

    async def export_package(self) -> MedicinePackage:
        docs = await self.list_medicines()
        return MedicinePackage(medicines=docs)

    async def search_bm25(
        self, query_terms: Sequence[str], top_k: int = 5
    ) -> list[SearchResult]:
        """Execute set-based BM25 scoring over PostgreSQL/SQLite inverted index."""
        terms = list(unique_terms(query_terms))
        if not terms or top_k <= 0:
            return []

        async with self._engine.connect() as conn:
            stat_row = (await conn.execute(select(rag_stats).where(rag_stats.c.id == 1))).first()
            if stat_row is None or stat_row.n_chunks <= 0 or stat_row.avgdl <= 0:
                return []

            n_chunks = int(stat_row.n_chunks)
            avgdl = float(stat_row.avgdl)
            k1 = self._params.k1
            b = self._params.b

            term_rows = (
                await conn.execute(
                    select(rag_terms.c.term, rag_terms.c.df).where(
                        rag_terms.c.term.in_(terms)
                    )
                )
            ).all()
            if not term_rows:
                return []

            df_map = {r.term: int(r.df) for r in term_rows}
            matched_terms = list(df_map.keys())

            post_stmt = (
                select(
                    rag_postings.c.term,
                    rag_postings.c.tf,
                    rag_chunks.c.id.label("chunk_id"),
                    rag_chunks.c.doc_id,
                    rag_chunks.c.term_count,
                )
                .select_from(
                    rag_postings.join(
                        rag_chunks, rag_postings.c.chunk_id == rag_chunks.c.id
                    )
                )
                .where(rag_postings.c.term.in_(matched_terms))
            )
            post_rows = (await conn.execute(post_stmt)).all()
            if not post_rows:
                return []

            import math

            chunk_scores: dict[int, tuple[str, float]] = {}
            for r in post_rows:
                df_val = df_map[r.term]
                idf_val = math.log(1.0 + (n_chunks - df_val + 0.5) / (df_val + 0.5))
                if idf_val <= 0:
                    continue
                norm = k1 * (1.0 - b + b * (float(r.term_count) / avgdl))
                contrib = idf_val * (float(r.tf) * (k1 + 1.0)) / (float(r.tf) + norm)
                prev = chunk_scores.get(int(r.chunk_id), (r.doc_id, 0.0))[1]
                chunk_scores[int(r.chunk_id)] = (r.doc_id, prev + contrib)

            # Aggregate best chunk score per document
            doc_scores: dict[str, float] = {}
            for doc_id, sc in chunk_scores.values():
                if sc > doc_scores.get(doc_id, 0.0):
                    doc_scores[doc_id] = sc

            ranked_ids = [
                doc_id
                for doc_id, _ in sorted(
                    doc_scores.items(), key=lambda x: (-x[1], x[0])
                )[:top_k]
            ]
            if not ranked_ids:
                return []

            doc_rows = (
                await conn.execute(
                    select(rag_medicines).where(rag_medicines.c.id.in_(ranked_ids))
                )
            ).all()
            docs_by_id = {r.id: _row_to_document(r) for r in doc_rows}

        results: list[SearchResult] = []
        for doc_id in ranked_ids:
            doc = docs_by_id.get(doc_id)
            if doc:
                results.append(
                    SearchResult(
                        doc_id=doc_id,
                        title=doc.title,
                        score=round(doc_scores[doc_id], 4),
                        document=doc,
                    )
                )
        return results

    async def search_dense(
        self, query_text: str, top_k: int = 5, *, min_similarity: float = 0.08
    ) -> list[SearchResult]:
        """Dense cosine similarity over chunk embeddings stored in PostgreSQL."""
        q_vec = self._embedder.embed(query_text)
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(rag_chunks.c.doc_id, rag_chunks.c.embedding)
                )
            ).all()
            if not rows:
                return []

            doc_scores: dict[str, float] = {}
            for r in rows:
                emb = r.embedding if isinstance(r.embedding, list) else []
                sim = cosine_similarity(q_vec, emb)
                if sim >= min_similarity and sim > doc_scores.get(r.doc_id, 0.0):
                    doc_scores[r.doc_id] = sim

            ranked = sorted(doc_scores.items(), key=lambda item: (-item[1], item[0]))[
                :top_k
            ]
            if not ranked:
                return []
            doc_ids = [d_id for d_id, _ in ranked]
            doc_rows = (
                await conn.execute(
                    select(rag_medicines).where(rag_medicines.c.id.in_(doc_ids))
                )
            ).all()
            docs_by_id = {r.id: _row_to_document(r) for r in doc_rows}

        return [
            SearchResult(
                doc_id=d_id,
                title=docs_by_id[d_id].title,
                score=round(sim, 4),
                document=docs_by_id[d_id],
            )
            for d_id, sim in ranked
            if d_id in docs_by_id
        ]

    async def suggest_fuzzy(
        self, query: str, *, threshold: float = 0.25, limit: int = 5
    ) -> list[MedicineDocument]:
        """Typo-tolerant fuzzy match using pg_trgm in Postgres or Python trigrams."""
        q = normalize_text(query)
        if not q:
            return []

        async with self._engine.connect() as conn:
            if conn.dialect.name == "postgresql":
                stmt = (
                    select(
                        rag_medicines,
                        func.greatest(
                            func.similarity(func.lower(rag_medicines.c.title), q),
                            func.similarity(func.lower(rag_medicines.c.inn), q),
                        ).label("sim"),
                    )
                    .where(
                        func.greatest(
                            func.similarity(func.lower(rag_medicines.c.title), q),
                            func.similarity(func.lower(rag_medicines.c.inn), q),
                        )
                        >= threshold
                    )
                    .order_by(text("sim DESC"), rag_medicines.c.id.asc())
                    .limit(limit)
                )
                rows = (await conn.execute(stmt)).all()
                return [_row_to_document(r) for r in rows]

        docs = await self.list_medicines()
        scored = [
            (max(trigram_similarity(q, d.title), trigram_similarity(q, d.inn)), d)
            for d in docs
        ]
        scored = [(s, d) for s, d in scored if s >= threshold]
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [d for _, d in scored[:limit]]

    async def load_into_hybrid_index(self) -> HybridRagIndex | None:
        """Build a fast in-memory HybridRagIndex synced from DB documents."""
        docs = await self.list_medicines()
        if not docs:
            return None
        bm25 = InMemoryBm25Index(self._params)
        for doc in docs:
            bm25.add_document(doc, self._analyzer.terms(doc.full_text()))
        return HybridRagIndex(
            bm25_index=bm25,
            analyzer=self._analyzer,
            embedder=self._embedder,
        )
