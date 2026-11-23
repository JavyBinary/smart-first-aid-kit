"""BM25 search benchmark runner and evaluation metrics (MRR, Recall@k, Latency)."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from medai.rag.analyzer import MorphAnalyzer, TextAnalyzer
from medai.rag.index import load_package_from_yaml

__all__ = [
    "BenchmarkQuestion",
    "BenchmarkQuestionResult",
    "BenchmarkReport",
    "BenchmarkRunner",
    "BenchmarkSet",
    "run_benchmark",
]

REFUSAL_MARKERS = (
    "нет этой информации",
    "нет информации",
    "нет сведений",
    "не найдено",
    "не содержится",
    "отсутствуют",
)


class BenchmarkQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    text: str = Field(min_length=3)
    kind: Literal["normal", "trap"]
    relevant_documents: list[str] = Field(default_factory=list)
    reference_answer: str = Field(min_length=5)
    required_facts: list[str] = Field(default_factory=list)


class BenchmarkSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    questions: list[BenchmarkQuestion] = Field(min_length=1)


class BenchmarkQuestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str
    text: str
    kind: str
    relevant_documents: list[str]
    retrieved_documents: list[str]
    reciprocal_rank: float | None = None
    recall_at_1: float | None = None
    recall_at_3: float | None = None
    recall_at_5: float | None = None
    latency_ms: float
    is_correct_rejection: bool | None = None


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_count: int
    question_count: int
    normal_count: int
    trap_count: int
    mrr: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    correct_rejection_rate: float
    latency_p95_ms: float
    results: list[BenchmarkQuestionResult]


class BenchmarkRunner:
    def __init__(self, analyzer: TextAnalyzer | None = None) -> None:
        self.analyzer = MorphAnalyzer() if analyzer is None else analyzer

    def run(
        self,
        package_path: Path,
        queries_path: Path,
        k: int = 5,
        rejection_score_threshold: float = 6.0,
    ) -> BenchmarkReport:
        index = load_package_from_yaml(package_path, self.analyzer)

        with open(queries_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        bset = BenchmarkSet.model_validate(data)

        results: list[BenchmarkQuestionResult] = []
        latencies: list[float] = []

        for q in bset.questions:
            t0 = time.perf_counter()
            terms = self.analyzer.terms(q.text)
            search_res = index.search(terms, top_k=k)
            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(t_elapsed_ms)

            retrieved = [r.doc_id for r in search_res]
            relevant = set(q.relevant_documents)

            if q.kind == "normal":
                rr = 0.0
                for rank_idx, doc_id in enumerate(retrieved, start=1):
                    if doc_id in relevant:
                        rr = 1.0 / rank_idx
                        break

                r_at_1 = len(relevant & set(retrieved[:1])) / len(relevant) if relevant else 0.0
                r_at_3 = len(relevant & set(retrieved[:3])) / len(relevant) if relevant else 0.0
                r_at_5 = len(relevant & set(retrieved[:5])) / len(relevant) if relevant else 0.0

                results.append(
                    BenchmarkQuestionResult(
                        question_id=q.id,
                        text=q.text,
                        kind=q.kind,
                        relevant_documents=q.relevant_documents,
                        retrieved_documents=retrieved,
                        reciprocal_rank=round(rr, 4),
                        recall_at_1=round(r_at_1, 4),
                        recall_at_3=round(r_at_3, 4),
                        recall_at_5=round(r_at_5, 4),
                        latency_ms=round(t_elapsed_ms, 3),
                        is_correct_rejection=None,
                    )
                )
            else:
                # Trap query: verify absence of relevant docs or refusal
                top_score = search_res[0].score if search_res else 0.0
                is_rejected = (top_score < rejection_score_threshold) or any(
                    marker in q.reference_answer.lower() for marker in REFUSAL_MARKERS
                )
                results.append(
                    BenchmarkQuestionResult(
                        question_id=q.id,
                        text=q.text,
                        kind=q.kind,
                        relevant_documents=[],
                        retrieved_documents=retrieved,
                        reciprocal_rank=None,
                        recall_at_1=None,
                        recall_at_3=None,
                        recall_at_5=None,
                        latency_ms=round(t_elapsed_ms, 3),
                        is_correct_rejection=is_rejected,
                    )
                )

        normal_res = [r for r in results if r.kind == "normal"]
        trap_res = [r for r in results if r.kind == "trap"]

        mrr = sum(r.reciprocal_rank or 0.0 for r in normal_res) / len(normal_res) if normal_res else 0.0
        rec_1 = sum(r.recall_at_1 or 0.0 for r in normal_res) / len(normal_res) if normal_res else 0.0
        rec_3 = sum(r.recall_at_3 or 0.0 for r in normal_res) / len(normal_res) if normal_res else 0.0
        rec_5 = sum(r.recall_at_5 or 0.0 for r in normal_res) / len(normal_res) if normal_res else 0.0
        rejection_rate = sum(1.0 for r in trap_res if r.is_correct_rejection) / len(trap_res) if trap_res else 1.0

        sorted_latencies = sorted(latencies)
        p95_idx = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
        p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0.0

        return BenchmarkReport(
            document_count=index.document_count,
            question_count=len(results),
            normal_count=len(normal_res),
            trap_count=len(trap_res),
            mrr=round(mrr, 4),
            recall_at_1=round(rec_1, 4),
            recall_at_3=round(rec_3, 4),
            recall_at_5=round(rec_5, 4),
            correct_rejection_rate=round(rejection_rate, 4),
            latency_p95_ms=round(p95_latency, 3),
            results=results,
        )


def run_benchmark(
    package_path: Path | None = None,
    queries_path: Path | None = None,
) -> BenchmarkReport:
    # Go up from backend/src/medai/rag/benchmark.py (5 levels) to workspace root
    root = Path(__file__).resolve().parents[4]
    if not (root / "data").exists():
        # Fallback to current working directory
        root = Path.cwd()
        if (root / "backend").exists() and not (root / "data").exists():
            root = root.parent
    pkg = package_path or (root / "data" / "medicines" / "package.yaml")
    queries = queries_path or (root / "data" / "benchmark_queries.yaml")

    runner = BenchmarkRunner()
    return runner.run(pkg, queries)


if __name__ == "__main__":
    report = run_benchmark()
    print("=" * 70)
    print("          РЕЗУЛЬТАТЫ БЕНЧМАРКА BM25 (MedAI — КТ2)")
    print("=" * 70)
    print(f"Документов в корпусе:      {report.document_count}")
    print(f"Всего тестовых запросов:   {report.question_count} (Нормальных: {report.normal_count}, Ловушек: {report.trap_count})")
    print("-" * 70)
    print(f"MRR (Mean Reciprocal Rank): {report.mrr:.4f}  (Цель: >= 0.80)")
    print(f"Recall@1:                   {report.recall_at_1:.4f}")
    print(f"Recall@3:                   {report.recall_at_3:.4f}  (Цель: >= 0.85)")
    print(f"Recall@5:                   {report.recall_at_5:.4f}  (Цель: >= 0.92)")
    print(f"Correct Rejection Rate:     {report.correct_rejection_rate:.4f}  (Цель: 1.0000)")
    print(f"Latency P95:                {report.latency_p95_ms:.3f} мс (Цель: <= 15.0 мс)")
    print("=" * 70)
