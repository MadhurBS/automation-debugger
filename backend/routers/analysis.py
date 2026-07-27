from __future__ import annotations

import math
import uuid
from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import AsyncSessionLocal, get_db
from models import AnalysisReport, AnalysisStatusEnum, LogFile, Project, User
from schemas import (
    AnalysisListResponse,
    AnalysisReportResponse,
    AnalysisStatusResponse,
    MessageResponse,
    TriggerAnalysisRequest,
)
from services.rca_engine import RCAEngine
from services.standards_checker import StandardsChecker

router = APIRouter(prefix="/analysis", tags=["Analysis"])


async def _run_analysis(
    report_id: uuid.UUID,
    pasted_error_text: str | None = None,
    check_standards: bool = True,
) -> None:
    """Background task: RCA + coding standards check."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(AnalysisReport).where(AnalysisReport.id == report_id))
            report = result.scalar_one_or_none()
            if not report:
                return

            proj_result = await db.execute(select(Project).where(Project.id == report.project_id))
            project = proj_result.scalar_one_or_none()
            if not project:
                report.status = AnalysisStatusEnum.FAILED
                report.error_message = "Project not found"
                await db.commit()
                return

            logs_result = await db.execute(select(LogFile).where(LogFile.project_id == project.id))
            log_files = list(logs_result.scalars().all())

            report.status = AnalysisStatusEnum.PARSING
            await db.commit()

            # ── RCA ────────────────────────────────────────────────────────────
            engine = RCAEngine()
            rca_result = await engine.analyze(
                project=project,
                log_files=log_files,
                pasted_error_text=pasted_error_text,
            )

            report.status = AnalysisStatusEnum.ANALYZING
            await db.commit()

            # ── Coding Standards Check ─────────────────────────────────────────
            standards_violations: dict | None = None
            code_errors: dict | None = None
            standards_score: float | None = None

            if check_standards:
                checker = StandardsChecker()
                std_result = checker.check(project)
                standards_violations = {
                    "violations": [asdict(v) for v in std_result.violations],
                    "summary": std_result.summary,
                    "passed_rules": std_result.passed_rules,
                }
                code_errors = {
                    "errors": [asdict(e) for e in std_result.code_errors],
                    "total": len(std_result.code_errors),
                }
                standards_score = std_result.score

            # ── Persist ────────────────────────────────────────────────────────
            report.status = AnalysisStatusEnum.COMPLETED
            report.platform = project.platform
            report.root_causes = {"causes": [rc.model_dump() for rc in rca_result.root_causes]}
            report.recommendations = {"items": rca_result.recommendations}
            report.raw_ai_response = rca_result.raw_ai_response
            report.ai_used = rca_result.ai_used
            report.overall_confidence = rca_result.overall_confidence
            report.standards_violations = standards_violations
            report.code_errors = code_errors
            report.standards_score = standards_score
            await db.commit()

        except Exception as exc:
            async with AsyncSessionLocal() as err_db:
                err_result = await err_db.execute(select(AnalysisReport).where(AnalysisReport.id == report_id))
                err_report = err_result.scalar_one_or_none()
                if err_report:
                    err_report.status = AnalysisStatusEnum.FAILED
                    err_report.error_message = str(exc)
                    await err_db.commit()


@router.post("/trigger", response_model=AnalysisStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_analysis(
    payload: TriggerAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == payload.project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    report = AnalysisReport(project_id=payload.project_id, platform=project.platform)
    db.add(report)
    await db.commit()
    await db.refresh(report)

    background_tasks.add_task(
        _run_analysis,
        report.id,
        getattr(payload, "pasted_error_text", None),
        payload.check_standards,
    )
    return report


@router.get("/{report_id}/status", response_model=AnalysisStatusResponse)
async def get_status(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AnalysisReport).where(AnalysisReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Analysis report not found")
    return report


@router.get("/{report_id}", response_model=AnalysisReportResponse)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AnalysisReport).where(AnalysisReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Analysis report not found")
    if report.status not in (AnalysisStatusEnum.COMPLETED, AnalysisStatusEnum.FAILED):
        raise HTTPException(400, f"Analysis is still {report.status.value}")
    return report


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = 1,
    size: int = 20,
    project_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AnalysisReport)
        .join(Project, Project.id == AnalysisReport.project_id)
        .where(Project.owner_id == current_user.id)
    )
    if project_id:
        query = query.where(AnalysisReport.project_id == project_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    items_result = await db.execute(query.offset((page - 1) * size).limit(size).order_by(AnalysisReport.created_at.desc()))
    items = list(items_result.scalars().all())

    return AnalysisListResponse(items=items, total=total, page=page, size=size, pages=math.ceil(total / size) if total else 1)


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisReport)
        .join(Project, Project.id == AnalysisReport.project_id)
        .where(AnalysisReport.id == report_id, Project.owner_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    await db.delete(report)
    await db.commit()
    return MessageResponse(message="Report deleted")
