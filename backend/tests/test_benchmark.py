"""Unit and benchmark evaluation tests for BM25 retrieval metrics."""

from __future__ import annotations

from pathlib import Path

import yaml

from medai.rag.analyzer import MorphAnalyzer
from medai.rag.benchmark import BenchmarkRunner, run_benchmark


def test_load_benchmark_dataset():
    path = Path(__file__).resolve().parents[2] / "data" / "benchmark_queries.yaml"
    assert path.exists(), f"Benchmark dataset not found at {path}"

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "questions" in data
    questions = data["questions"]
    assert len(questions) >= 15

    normal_count = sum(1 for q in questions if q.get("kind") == "normal")
    trap_count = sum(1 for q in questions if q.get("kind") == "trap")

    assert normal_count == 10
    assert trap_count == 5


def test_benchmark_runner_metrics_thresholds():
    root = Path(__file__).resolve().parents[2]
    package_path = root / "data" / "medicines" / "package.yaml"
    queries_path = root / "data" / "benchmark_queries.yaml"

    runner = BenchmarkRunner(analyzer=MorphAnalyzer())
    report = runner.run(package_path=package_path, queries_path=queries_path)

    # BMSTU NIRS distinction threshold assertions:
    assert report.document_count == 30
    assert report.question_count == 15
    assert report.normal_count == 10
    assert report.trap_count == 5

    # 1. Ranking quality: MRR >= 0.80
    assert report.mrr >= 0.80, f"MRR {report.mrr} is below target 0.80"

    # 2. Recall@3 >= 0.85 and Recall@5 >= 0.92
    assert report.recall_at_3 >= 0.85, (
        f"Recall@3 {report.recall_at_3} is below target 0.85"
    )
    assert report.recall_at_5 >= 0.92, (
        f"Recall@5 {report.recall_at_5} is below target 0.92"
    )

    # 3. Correct rejection rate for traps == 1.00
    assert report.correct_rejection_rate == 1.00, (
        f"Rejection rate {report.correct_rejection_rate} is below target 1.00"
    )

    # 4. Latency P95 <= 15.0 ms
    assert report.latency_p95_ms <= 15.0, (
        f"Latency P95 {report.latency_p95_ms}ms exceeds 15.0ms threshold"
    )


def test_run_benchmark_convenience():
    report = run_benchmark()
    assert report.document_count == 30
    assert report.question_count == 15
    assert report.mrr == 1.0
    assert report.correct_rejection_rate == 1.0
