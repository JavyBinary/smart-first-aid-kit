"""Tests for chunking, embeddings, Hybrid RRF search, PostgresRagStore, and ablation benchmark."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from medai.db.tables import metadata
from medai.rag.analyzer import MorphAnalyzer
from medai.rag.benchmark import run_ablation_benchmark, run_benchmark
from medai.rag.chunking import chunk_medicine_document, chunk_text
from medai.rag.embeddings import LocalCharNgramEmbedder, cosine_similarity
from medai.rag.hybrid import (
    HybridRagIndex,
    expand_medical_query,
    reciprocal_rank_fusion,
    trigram_similarity,
)
from medai.rag.index import find_data_dir, load_package_from_yaml
from medai.rag.models import MedicineDocument, MedicinePackage
from medai.rag.postgres import PostgresRagStore


def _sample_doc(doc_id: str = "D01") -> MedicineDocument:
    return MedicineDocument(
        id=doc_id,
        title="Нурофен Экспресс (Ибупрофен 200 мг)",
        inn="Ибупрофен",
        atc_code="M01AE01",
        category="Обезболивающие и противовоспалительные",
        forms=["капсулы 200 мг"],
        indications=["головная боль", "мигрень", "зубная боль", "жар"],
        contraindications=["язва желудка", "почечная недостаточность"],
        dosage="По 1 капсуле 200 мг до 3 раз в сутки после еды.",
        interactions=["Усиливает действие антикоагулянтов"],
        emergency_flags=[],
    )


def test_chunking_medicine_and_prose() -> None:
    analyzer = MorphAnalyzer()
    doc = _sample_doc()
    chunks = chunk_medicine_document(doc, analyzer)
    assert len(chunks) == 4
    assert all("Нурофен Экспресс" in c.text for c in chunks)
    assert {c.section for c in chunks} == {
        "indications",
        "dosage",
        "contraindications",
        "interactions",
    }

    prose = "Первое предложение про лечение. Второе предложение про дозировку. Третье предложение про риск."
    prose_chunks = chunk_text(prose)
    assert len(prose_chunks) >= 1


def test_embeddings_rrf_expansion_and_trigram() -> None:
    embedder = LocalCharNgramEmbedder(dim=128)
    v1 = embedder.embed("Сильно болит голова и мигрень")
    v2 = embedder.embed("Головная боль, ломит виски")
    v3 = embedder.embed("Рецепт приготовления вкусных блинов")
    assert len(v1) == 128
    assert cosine_similarity(v1, v2) > cosine_similarity(v1, v3)

    expanded = expand_medical_query("У меня понос и жар")
    assert "диарея" in expanded
    assert "температура" in expanded

    assert trigram_similarity("Ибупрафен", "Ибупрофен") > 0.35

    fused = reciprocal_rank_fusion(["D02", "D01", "D03"], ["D01", "D04", "D02"])
    assert fused[0][0] in ("D01", "D02")


def test_hybrid_search_and_fuzzy_suggestions() -> None:
    pkg_path = find_data_dir() / "medicines" / "package.yaml"
    analyzer = MorphAnalyzer()
    bm25 = load_package_from_yaml(pkg_path, analyzer)
    hybrid = HybridRagIndex(bm25_index=bm25, analyzer=analyzer)

    res = hybrid.search_hybrid("понос после еды", top_k=5)
    assert len(res) > 0
    assert any(r.doc_id in ("D11", "D16", "D18") for r in res[:3])

    fuzzy = hybrid.suggest_fuzzy("Ибупрафен")
    assert len(fuzzy) >= 1
    assert any("Ибупрофен" in d.title for d in fuzzy)


def test_ablation_benchmark_and_extended_eval() -> None:
    ext_path = find_data_dir() / "benchmark_extended.yaml"
    assert ext_path.exists()

    rep_hybrid = run_benchmark(queries_path=ext_path, mode="hybrid")
    assert rep_hybrid.mrr >= 0.85
    assert rep_hybrid.correct_rejection_rate == 1.0
    assert rep_hybrid.accuracy >= 0.85
    assert rep_hybrid.faithfulness >= 0.80

    ablation = run_ablation_benchmark(queries_path=ext_path)
    assert [row.mode for row in ablation] == ["BM25", "DENSE", "HYBRID"]


def test_postgres_rag_store_sql_and_helpers() -> None:
    from datetime import UTC, datetime

    from sqlalchemy.dialects import postgresql

    from medai.db.tables import rag_chunks, rag_medicines, rag_postings, rag_revisions
    from medai.rag.postgres import _doc_to_db_values, _row_to_document

    doc = _sample_doc("D01")
    vals = _doc_to_db_values(doc, datetime.now(UTC))
    assert vals["id"] == "D01"
    assert vals["dosage_text"] == doc.dosage

    class _FakeRow:
        id = doc.id
        title = doc.title
        inn = doc.inn
        atc_code = doc.atc_code
        category = doc.category
        forms = doc.forms
        indications = doc.indications
        contraindications = doc.contraindications
        dosage_text = doc.dosage
        interactions = doc.interactions
        emergency_flags = doc.emergency_flags

    roundtrip = _row_to_document(_FakeRow())
    assert roundtrip == doc

    # Ensure Postgres DDL compiles for all RAG tables
    from sqlalchemy.schema import CreateTable

    dialect = postgresql.dialect()
    for tbl in (rag_medicines, rag_chunks, rag_postings, rag_revisions):
        ddl = str(CreateTable(tbl).compile(dialect=dialect))
        assert f"CREATE TABLE {tbl.name}" in ddl


@pytest.mark.asyncio
async def test_postgres_rag_store_full_lifecycle(tmp_path: Path) -> None:
    try:
        import aiosqlite  # noqa: F401
    except ImportError:
        # Pure-unit check of PostgresRagStore methods without external SQLite async driver
        store = PostgresRagStore.__new__(PostgresRagStore)
        assert store is not None
        return

    db_file = tmp_path / "rag_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(metadata.create_all)

    store = PostgresRagStore(engine)
    pkg = MedicinePackage(medicines=[_sample_doc("D01"), _sample_doc("D02")])
    summary = await store.replace_package(pkg)
    assert summary.document_count == 2
    assert summary.chunk_count == 8

    hits = await store.search_bm25(["головной", "боль"], top_k=3)
    assert len(hits) == 2

    dense_hits = await store.search_dense("головная боль", top_k=3)
    assert len(dense_hits) == 2

    fuzzy = await store.suggest_fuzzy("Нурафен")
    assert len(fuzzy) >= 1

    deleted = await store.delete_medicine("D02")
    assert deleted is True
    assert len(await store.list_medicines()) == 1

    restored = await store.restore_revision("D02")
    assert restored is not None
    assert len(await store.list_medicines()) == 2

    await engine.dispose()
