"""FastAPI admin router: stats, report moderation, medicine corpus CRUD, and benchmark."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status

from medai.admin.models import (
    MessageReportItem,
    ReportStatus,
    ReportStatusUpdate,
    StatsPeriod,
    UserStats,
)
from medai.admin.stores import AdminStore, ReportNotFoundError
from medai.auth.models import Role, User
from medai.auth.router import get_current_user
from medai.dialogs.service import DialogService
from medai.rag.benchmark import AblationRow, run_ablation_benchmark
from medai.rag.index import find_data_dir
from medai.rag.models import MedicineDocument
from medai.rag.postgres import PostgresRagStore

__all__ = ["create_admin_router"]


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (Role.ADMIN, Role.SUPERADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def create_admin_router(
    admin_store: AdminStore,
    rag_store: PostgresRagStore | None = None,
    dialog_service: DialogService | None = None,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/admin",
        tags=["admin"],
        dependencies=[Depends(_require_admin)],
    )

    @router.get("/stats", response_model=UserStats)
    async def get_admin_stats(
        period: StatsPeriod = StatsPeriod.DAYS_30,
    ) -> UserStats:
        med_count = 0
        if dialog_service and getattr(dialog_service, "_bm25_index", None):
            med_count = dialog_service._bm25_index.document_count  # type: ignore[union-attr]
        return await admin_store.get_stats(
            period, fallback_medicines_count=med_count
        )

    @router.get("/reports", response_model=dict[str, list[MessageReportItem]])
    async def list_reports(
        status_filter: Literal["new", "resolved", "dismissed", "all"] = "new",
    ) -> dict[str, list[MessageReportItem]]:
        target = None if status_filter == "all" else ReportStatus(status_filter)
        items = await admin_store.list_reports(target)
        return {"reports": items}

    @router.patch("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def set_report_status(
        report_id: int,
        body: ReportStatusUpdate,
        admin: User = Depends(_require_admin),
    ) -> Response:
        try:
            await admin_store.set_report_status(report_id, body.status, admin.id)
        except ReportNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/medicines", response_model=list[MedicineDocument])
    async def list_medicines() -> list[MedicineDocument]:
        if rag_store is not None:
            docs = await rag_store.list_medicines()
            if docs:
                return docs
        if dialog_service and getattr(dialog_service, "_bm25_index", None):
            return list(dialog_service._bm25_index.documents.values())  # type: ignore[union-attr]
        return []

    @router.post(
        "/medicines",
        status_code=status.HTTP_201_CREATED,
        response_model=MedicineDocument,
    )
    async def create_or_update_medicine(doc: MedicineDocument) -> MedicineDocument:
        if rag_store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database corpus store unavailable",
            )
        saved = await rag_store.upsert_medicine(doc)
        if dialog_service is not None:
            hybrid = await rag_store.load_into_hybrid_index()
            if hybrid is not None:
                dialog_service.set_rag_index(hybrid.bm25)
        return saved

    @router.delete("/medicines/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_medicine(doc_id: str) -> Response:
        if rag_store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database corpus store unavailable",
            )
        deleted = await rag_store.delete_medicine(doc_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found"
            )
        if dialog_service is not None:
            hybrid = await rag_store.load_into_hybrid_index()
            if hybrid is not None:
                dialog_service.set_rag_index(hybrid.bm25)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get("/benchmark", response_model=dict[str, list[AblationRow]])
    async def run_live_benchmark(
        dataset: Literal["base", "extended"] = "base",
    ) -> dict[str, list[AblationRow]]:
        data_dir = find_data_dir()
        q_path = (
            data_dir / "benchmark_extended.yaml"
            if dataset == "extended"
            else data_dir / "benchmark_queries.yaml"
        )
        rows = run_ablation_benchmark(queries_path=q_path)
        return {"rows": rows}

    return router
