from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import AnalysisReport, AnalysisStatusEnum, Project, User
from services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{report_id}/pdf")
async def download_pdf(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _get_completed_report(report_id, current_user.id, db)

    if report.pdf_path and Path(report.pdf_path).exists():
        return FileResponse(report.pdf_path, media_type="application/pdf", filename=f"rca_{report_id}.pdf")

    generator = ReportGenerator()
    pdf_path = await generator.generate_pdf(report)
    report.pdf_path = pdf_path
    await db.commit()
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"rca_{report_id}.pdf")


@router.get("/{report_id}/excel")
async def download_excel(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _get_completed_report(report_id, current_user.id, db)

    if report.excel_path and Path(report.excel_path).exists():
        return FileResponse(
            report.excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"rca_{report_id}.xlsx",
        )

    generator = ReportGenerator()
    excel_path = await generator.generate_excel(report)
    report.excel_path = excel_path
    await db.commit()
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"rca_{report_id}.xlsx",
    )


@router.post("/{report_id}/regenerate", status_code=200)
async def regenerate_reports(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await _get_completed_report(report_id, current_user.id, db)
    generator = ReportGenerator()
    report.pdf_path = await generator.generate_pdf(report)
    report.excel_path = await generator.generate_excel(report)
    await db.commit()
    return {"message": "Reports regenerated", "pdf_path": report.pdf_path, "excel_path": report.excel_path}


async def _get_completed_report(report_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> AnalysisReport:
    result = await db.execute(
        select(AnalysisReport)
        .join(Project, Project.id == AnalysisReport.project_id)
        .where(AnalysisReport.id == report_id, Project.owner_id == user_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.status != AnalysisStatusEnum.COMPLETED:
        raise HTTPException(400, "Report is not yet completed")
    return report
