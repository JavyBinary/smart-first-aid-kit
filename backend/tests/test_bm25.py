"""Unit tests for BM25 ranking, text analysis, and in-memory indexing."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from medai.rag.analyzer import MorphAnalyzer, SimpleAnalyzer, normalize_text
from medai.rag.bm25 import Bm25Params, idf, rank, score, term_score
from medai.rag.index import InMemoryBm25Index, load_package_from_yaml
from medai.rag.models import MedicineDocument


def test_normalize_text():
    raw = "Парацетамол-МВ, 500 мг   (таблетки)!  Ёмкость"
    normalized = normalize_text(raw)
    assert "парацетамол-мв" in normalized
    assert "емкость" in normalized
    assert "  " not in normalized


def test_simple_analyzer():
    analyzer = SimpleAnalyzer()
    tokens = analyzer.terms("Ибупрофен, 400 мг: головная боль!")
    assert "ибупрофен" in tokens
    assert "400" in tokens
    assert "мг" in tokens
    assert "головная" in tokens
    assert "боль" in tokens


def test_morph_analyzer_lemmatization():
    analyzer = MorphAnalyzer()
    tokens = analyzer.terms("болит голова и ноет зуб")
    assert "болеть" in tokens
    assert "голова" in tokens
    assert "ныть" in tokens
    assert "зуб" in tokens


def test_bm25_idf_mathematics():
    # N = 100, df = 10
    # Robertson-Spärck Jones IDF: ln(1 + (100 - 10 + 0.5) / (10 + 0.5))
    computed = idf(n_documents=100, document_frequency=10)
    expected = math.log(1.0 + (100 - 10 + 0.5) / (10 + 0.5))
    assert pytest.approx(computed, rel=1e-4) == expected
    assert computed > 0.0

    # Rare word (df=1) has strictly higher IDF than common word (df=50)
    assert idf(100, 1) > idf(100, 50)


def test_bm25_term_score_and_saturation():
    params = Bm25Params(k1=1.5, b=0.75)
    doc_len = 100
    avg_len = 100.0

    score_tf1 = term_score(
        term_frequency=1,
        document_length=doc_len,
        average_length=avg_len,
        params=params,
    )
    score_tf5 = term_score(
        term_frequency=5,
        document_length=doc_len,
        average_length=avg_len,
        params=params,
    )
    score_tf100 = term_score(
        term_frequency=100,
        document_length=doc_len,
        average_length=avg_len,
        params=params,
    )

    assert score_tf1 < score_tf5 < score_tf100
    # Saturation upper bound: tf / (tf + 0) * (k1 + 1) = 2.5
    assert score_tf100 < 2.5


def test_bm25_score_computation():
    params = Bm25Params(k1=1.5, b=0.75)
    postings = {
        "голова": {"D01": 2, "D02": 1},
        "боль": {"D01": 1},
    }
    lengths = {"D01": 10, "D02": 10}
    scores = score(
        query_terms=["голова", "боль"],
        postings=postings,
        lengths=lengths,
        n_documents=2,
        average_length=10.0,
        params=params,
    )
    assert "D01" in scores
    assert "D02" in scores
    # D01 has both terms, D02 only has "голова"
    assert scores["D01"] > scores["D02"]


def test_bm25_ranking_ordering():
    scores = {"D01": 1.25, "D02": 3.45, "D03": 2.10, "D04": 0.0}
    ranked = rank(scores, top_k=2)
    assert len(ranked) == 2
    assert ranked[0] == "D02"
    assert ranked[1] == "D03"


def test_in_memory_bm25_index():
    index = InMemoryBm25Index()
    doc1 = MedicineDocument(
        id="D01",
        title="Ибупрофен",
        inn="Ибупрофен",
        atc_code="M01AE01",
        category="НПВП",
        forms=["таблетки 400 мг"],
        indications=["головная боль", "лихорадка"],
        contraindications=["язва желудка"],
        dosage="По 1 таблетке 3 раза в день",
        interactions=[],
        emergency_flags=[],
    )
    doc2 = MedicineDocument(
        id="D02",
        title="Парацетамол",
        inn="Парацетамол",
        atc_code="N02BE01",
        category="Анальгетики и антипиретики",
        forms=["таблетки 500 мг"],
        indications=["жар", "лихорадка", "простуда"],
        contraindications=["тяжелая печеночная недостаточность"],
        dosage="По 1 таблетке до 4 раз в день",
        interactions=[],
        emergency_flags=[],
    )

    index.add_document(doc1, ["ибупрофен", "головной", "боль", "лихорадка"])
    index.add_document(doc2, ["парацетамол", "жар", "лихорадка", "простуда"])

    assert index.document_count == 2
    assert index.average_length == 4.0

    # Query matching only D01
    results = index.search(["головной", "боль"], top_k=5)
    assert len(results) == 1
    assert results[0].doc_id == "D01"
    assert results[0].score > 0.0

    # Query matching both
    results_fever = index.search(["лихорадка"], top_k=5)
    assert len(results_fever) == 2


def test_load_package_from_yaml():
    pkg_path = Path(__file__).resolve().parents[2] / "data" / "medicines" / "package.yaml"
    assert pkg_path.exists()

    analyzer = MorphAnalyzer()
    index = load_package_from_yaml(pkg_path, analyzer)

    assert index.document_count == 30
    assert index.average_length > 0.0
    assert "D01" in index.documents
    assert "D30" in index.documents


def test_knowledge_load_main(monkeypatch):
    from medai.rag.knowledge_load import main

    # Test main execution without error
    monkeypatch.setattr("sys.argv", ["knowledge_load"])
    main()
