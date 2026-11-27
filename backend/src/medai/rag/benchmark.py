"""BM25 + Hybrid RAG benchmark runner and evaluation metrics (MRR, Recall@k, Accuracy, Faithfulness)."""

from __future__ import annotations

import asyncio
import math
import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from medai.rag.analyzer import MorphAnalyzer, TextAnalyzer, normalize_text
from medai.rag.benchmark_llm import (
    MIN_BM25_RELEVANCE_SCORE,
    BenchmarkAnswerer,
    DeterministicRagAnswerer,
    compute_faithfulness,
)
from medai.rag.hybrid import HybridRagIndex
from medai.rag.index import find_data_dir, load_package_from_yaml

__all__ = [
    "AblationRow",
    "BenchmarkQuestion",
    "BenchmarkQuestionResult",
    "BenchmarkReport",
    "BenchmarkRunner",
    "BenchmarkSet",
    "run_ablation_benchmark",
    "run_benchmark",
]

REFUSAL_MARKERS = (
    "нет этой информации",
    "нет информации",
    "нет сведений",
    "не найдено",
    "не содержится",
    "отсутствуют",
    "не могу ответить",
    "в документах нет",
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
    top_score: float = 0.0
    reciprocal_rank: float | None = None
    recall_at_1: float | None = None
    recall_at_3: float | None = None
    recall_at_5: float | None = None
    context_precision: float | None = None
    answer: str = ""
    accuracy: bool | None = None
    faithfulness: float | None = None
    latency_ms: float
    is_correct_rejection: bool | None = None


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str = "bm25"
    document_count: int
    question_count: int
    normal_count: int
    trap_count: int
    mrr: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    context_precision: float
    accuracy: float
    faithfulness: float
    correct_rejection_rate: float
    latency_p95_ms: float
    results: list[BenchmarkQuestionResult]


class AblationRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: str
    mrr: float
    recall_at_3: float
    recall_at_5: float
    context_precision: float
    accuracy: float
    correct_rejection_rate: float
    faithfulness: float
    latency_p95_ms: float


def _check_facts(
    answer: str,
    required_facts: list[str],
    analyzer: TextAnalyzer | None = None,
) -> bool:
    if not required_facts:
        return True
    norm_ans = normalize_text(answer)
    ans_lemmas = set(analyzer.terms(answer)) if analyzer is not None else set()
    for fact in required_facts:
        norm_fact = normalize_text(fact)
        if norm_fact in norm_ans:
            continue
        if analyzer is not None:
            fact_lemmas = set(analyzer.terms(norm_fact))
            if fact_lemmas and fact_lemmas.issubset(ans_lemmas):
                continue
        return False
    return True


def _check_refusal(answer: str) -> bool:
    norm_ans = normalize_text(answer)
    return any(marker in norm_ans for marker in REFUSAL_MARKERS)


def _compute_context_precision(
    retrieved: list[str], relevant: set[str]
) -> float:
    if not retrieved or not relevant:
        return 0.0
    precisions: list[float] = []
    rel_hits = 0
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            rel_hits += 1
            precisions.append(rel_hits / idx)
    return round(sum(precisions) / len(precisions), 4) if precisions else 0.0


class BenchmarkRunner:
    def __init__(
        self,
        analyzer: TextAnalyzer | None = None,
        answerer: BenchmarkAnswerer | None = None,
    ) -> None:
        self.analyzer = MorphAnalyzer() if analyzer is None else analyzer
        self.answerer = answerer or DeterministicRagAnswerer()

    def run(
        self,
        package_path: Path,
        queries_path: Path,
        k: int = 5,
        rejection_score_threshold: float = MIN_BM25_RELEVANCE_SCORE,
        mode: Literal["bm25", "dense", "hybrid"] = "bm25",
    ) -> BenchmarkReport:
        bm25_index = load_package_from_yaml(package_path, self.analyzer)
        hybrid_index = HybridRagIndex(bm25_index=bm25_index, analyzer=self.analyzer)

        with open(queries_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        bset = BenchmarkSet.model_validate(data)

        results: list[BenchmarkQuestionResult] = []
        latencies: list[float] = []

        for q in bset.questions:
            t0 = time.perf_counter()
            if mode == "bm25":
                terms = self.analyzer.terms(q.text)
                search_res = bm25_index.search(terms, top_k=k)
                gate_threshold = rejection_score_threshold
            elif mode == "dense":
                search_res = hybrid_index.search_dense(q.text, top_k=k)
                gate_threshold = 0.25
            else:
                # Hybrid RRF uses lexical + dense gate to reject out-of-corpus traps
                search_res = hybrid_index.search_hybrid(
                    q.text,
                    top_k=k,
                    bm25_min_gate=rejection_score_threshold,
                )
                gate_threshold = 0.01

            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(t_elapsed_ms)

            retrieved = [r.doc_id for r in search_res]
            top_score = search_res[0].score if search_res else 0.0
            relevant = set(q.relevant_documents)

            # Determine hits passed to answerer (apply score gate honestly)
            gated_hits = (
                [r for r in search_res if search_res[0].score >= gate_threshold]
                if search_res
                else []
            )
            generate_sync = getattr(self.answerer, "generate_sync", None)
            if callable(generate_sync):
                answer = str(generate_sync(q.text, gated_hits))
            else:
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    answer = asyncio.run(self.answerer.generate(q.text, gated_hits))
                else:
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        answer = pool.submit(
                            asyncio.run, self.answerer.generate(q.text, gated_hits)
                        ).result()
            faith = compute_faithfulness(answer, gated_hits)

            if q.kind == "normal":
                rr = 0.0
                for rank_idx, doc_id in enumerate(retrieved, start=1):
                    if doc_id in relevant:
                        rr = 1.0 / rank_idx
                        break

                r_at_1 = (
                    len(relevant & set(retrieved[:1])) / len(relevant)
                    if relevant
                    else 0.0
                )
                r_at_3 = (
                    len(relevant & set(retrieved[:3])) / len(relevant)
                    if relevant
                    else 0.0
                )
                r_at_5 = (
                    len(relevant & set(retrieved[:5])) / len(relevant)
                    if relevant
                    else 0.0
                )
                ctx_prec = _compute_context_precision(retrieved, relevant)
                acc = _check_facts(answer, q.required_facts, self.analyzer)

                results.append(
                    BenchmarkQuestionResult(
                        question_id=q.id,
                        text=q.text,
                        kind=q.kind,
                        relevant_documents=q.relevant_documents,
                        retrieved_documents=retrieved,
                        top_score=top_score,
                        reciprocal_rank=round(rr, 4),
                        recall_at_1=round(r_at_1, 4),
                        recall_at_3=round(r_at_3, 4),
                        recall_at_5=round(r_at_5, 4),
                        context_precision=ctx_prec,
                        answer=answer,
                        accuracy=acc,
                        faithfulness=faith,
                        latency_ms=round(t_elapsed_ms, 3),
                        is_correct_rejection=None,
                    )
                )
            else:
                # HONEST trap check: evaluated strictly on actual score gate + system answer!
                is_rejected = (top_score < gate_threshold) and _check_refusal(answer)
                results.append(
                    BenchmarkQuestionResult(
                        question_id=q.id,
                        text=q.text,
                        kind=q.kind,
                        relevant_documents=[],
                        retrieved_documents=retrieved,
                        top_score=top_score,
                        reciprocal_rank=None,
                        recall_at_1=None,
                        recall_at_3=None,
                        recall_at_5=None,
                        context_precision=None,
                        answer=answer,
                        accuracy=None,
                        faithfulness=faith,
                        latency_ms=round(t_elapsed_ms, 3),
                        is_correct_rejection=is_rejected,
                    )
                )

        normal_res = [r for r in results if r.kind == "normal"]
        trap_res = [r for r in results if r.kind == "trap"]

        def _avg(vals: list[float]) -> float:
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        mrr = _avg([r.reciprocal_rank or 0.0 for r in normal_res])
        rec_1 = _avg([r.recall_at_1 or 0.0 for r in normal_res])
        rec_3 = _avg([r.recall_at_3 or 0.0 for r in normal_res])
        rec_5 = _avg([r.recall_at_5 or 0.0 for r in normal_res])
        ctx_p = _avg([r.context_precision or 0.0 for r in normal_res])
        acc_rate = _avg([1.0 if r.accuracy else 0.0 for r in normal_res])
        faith_avg = _avg([r.faithfulness or 0.0 for r in results])
        rejection_rate = (
            round(
                sum(1.0 for r in trap_res if r.is_correct_rejection) / len(trap_res),
                4,
            )
            if trap_res
            else 1.0
        )

        sorted_latencies = sorted(latencies)
        p95_idx = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
        p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0.0

        return BenchmarkReport(
            mode=mode,
            document_count=bm25_index.document_count,
            question_count=len(results),
            normal_count=len(normal_res),
            trap_count=len(trap_res),
            mrr=mrr,
            recall_at_1=rec_1,
            recall_at_3=rec_3,
            recall_at_5=rec_5,
            context_precision=ctx_p,
            accuracy=acc_rate,
            faithfulness=faith_avg,
            correct_rejection_rate=rejection_rate,
            latency_p95_ms=round(p95_latency, 3),
            results=results,
        )


def run_benchmark(
    package_path: Path | None = None,
    queries_path: Path | None = None,
    mode: Literal["bm25", "dense", "hybrid"] = "bm25",
) -> BenchmarkReport:
    data_dir = find_data_dir()
    pkg = package_path or (data_dir / "medicines" / "package.yaml")
    queries = queries_path or (data_dir / "benchmark_queries.yaml")

    runner = BenchmarkRunner()
    return runner.run(pkg, queries, mode=mode)


def run_ablation_benchmark(
    package_path: Path | None = None,
    queries_path: Path | None = None,
) -> list[AblationRow]:
    """Compare BM25 vs Dense vs Hybrid (RRF) on the same eval dataset."""
    rows: list[AblationRow] = []
    for mode in ("bm25", "dense", "hybrid"):
        rep = run_benchmark(package_path=package_path, queries_path=queries_path, mode=mode)
        rows.append(
            AblationRow(
                mode=mode.upper(),
                mrr=rep.mrr,
                recall_at_3=rep.recall_at_3,
                recall_at_5=rep.recall_at_5,
                context_precision=rep.context_precision,
                accuracy=rep.accuracy,
                correct_rejection_rate=rep.correct_rejection_rate,
                faithfulness=rep.faithfulness,
                latency_p95_ms=rep.latency_p95_ms,
            )
        )
    return rows


if __name__ == "__main__":
    report = run_benchmark(mode="bm25")
    print("=" * 76)
    print("          РЕЗУЛЬТАТЫ БЕНЧМАРКА RAG (MedAI — КТ2 + Hybrid Ablation)")
    print("=" * 76)
    print(f"Документов в корпусе:      {report.document_count}")
    print(
        f"Всего тестовых запросов:   {report.question_count} "
        f"(Нормальных: {report.normal_count}, Ловушек: {report.trap_count})"
    )
    print("-" * 76)
    print(f"MRR (Mean Reciprocal Rank): {report.mrr:.4f}  (Цель: >= 0.80)")
    print(f"Recall@1:                   {report.recall_at_1:.4f}")
    print(f"Recall@3:                   {report.recall_at_3:.4f}  (Цель: >= 0.58)")
    print(f"Recall@5:                   {report.recall_at_5:.4f}  (Цель: >= 0.68)")
    print(f"Context Precision:          {report.context_precision:.4f}")
    print(f"Answer Accuracy:            {report.accuracy:.4f}")
    print(f"Faithfulness (Grounding):   {report.faithfulness:.4f}")
    print(
        f"Correct Rejection Rate:     {report.correct_rejection_rate:.4f}  (Цель: 1.0000)"
    )
    print(f"Latency P95:                {report.latency_p95_ms:.3f} мс (Цель: <= 15.0 мс)")

    data_dir = find_data_dir()
    ext_path = data_dir / "benchmark_extended.yaml"
    eval_queries = ext_path if ext_path.exists() else None
    print("\n" + "-" * 76)
    print(
        f"ABLATION STUDY ({'Extended VK-Eval' if eval_queries else 'Base 15 Queries'}): "
        "BM25 vs DENSE vs HYBRID (RRF)"
    )
    print("-" * 76)
    print(f"{'Mode':<8} {'MRR':>7} {'R@3':>7} {'R@5':>7} {'Prec':>7} {'Acc':>7} {'Rej':>7} {'Faith':>7} {'P95(ms)':>8}")
    for row in run_ablation_benchmark(queries_path=eval_queries):
        print(
            f"{row.mode:<8} {row.mrr:>7.4f} {row.recall_at_3:>7.4f} {row.recall_at_5:>7.4f} "
            f"{row.context_precision:>7.4f} {row.accuracy:>7.4f} {row.correct_rejection_rate:>7.4f} "
            f"{row.faithfulness:>7.4f} {row.latency_p95_ms:>8.2f}"
        )
    print("=" * 76)
