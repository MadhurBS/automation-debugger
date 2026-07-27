from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings


class ReportGenerator:
    """Generates PDF and Excel RCA reports."""

    async def generate_pdf(self, report: Any) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_pdf_sync, report)

    async def generate_excel(self, report: Any) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_excel_sync, report)

    def _generate_pdf_sync(self, report: Any) -> str:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        reports_dir = Path(settings.REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = reports_dir / f"rca_{report.id}.pdf"

        doc = SimpleDocTemplate(
            str(filename),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=22, spaceAfter=6)
        h2_style = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#1e3a5f"), spaceAfter=4)
        body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)
        code_style = ParagraphStyle("code", fontName="Courier", fontSize=9, leading=12, backColor=colors.HexColor("#f5f5f5"))
        muted_style = ParagraphStyle("muted", parent=styles["Normal"], fontSize=9, textColor=colors.grey)

        severity_colors = {
            "critical": colors.HexColor("#dc2626"),
            "high": colors.HexColor("#ea580c"),
            "medium": colors.HexColor("#ca8a04"),
            "low": colors.HexColor("#16a34a"),
        }

        story = []

        # ── Cover ──────────────────────────────────────────────────────────── #
        story.append(Paragraph("Automation Project Debugger", title_style))
        story.append(Paragraph("Root Cause Analysis Report", h2_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 0.5 * cm))

        meta_data = [
            ["Report ID", str(report.id)],
            ["Platform", str(getattr(report, "platform", "unknown")).upper()],
            ["Status", str(getattr(report, "status", "completed")).upper()],
            ["AI Analysis Used", "Yes" if getattr(report, "ai_used", False) else "No (Heuristic)"],
            ["Overall Confidence", f"{(getattr(report, 'overall_confidence', 0) or 0) * 100:.0f}%"],
            ["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]

        meta_table = Table(meta_data, colWidths=[4 * cm, 13 * cm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4ff")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 1 * cm))

        # ── Executive Summary ─────────────────────────────────────────────── #
        story.append(Paragraph("Executive Summary", h2_style))
        root_causes = (report.root_causes or {}).get("causes", [])
        if root_causes:
            primary = root_causes[0]
            story.append(Paragraph(
                f"The analysis identified <b>{len(root_causes)}</b> root cause(s). "
                f"The primary issue is: <b>{primary.get('title', 'Unknown')}</b>.",
                body_style,
            ))
            story.append(Spacer(1, 0.3 * cm))
        story.append(Spacer(1, 0.5 * cm))

        # ── Root Causes ───────────────────────────────────────────────────── #
        story.append(Paragraph("Root Causes", h2_style))
        for i, rc in enumerate(root_causes, 1):
            sev = rc.get("severity", "medium")
            sev_color = severity_colors.get(sev, colors.grey)

            story.append(Paragraph(
                f'<b>#{i} [{sev.upper()}] {rc.get("title", "")}</b>',
                ParagraphStyle(f"rc_{i}", parent=h2_style, fontSize=12, textColor=sev_color),
            ))
            story.append(Paragraph(rc.get("description", ""), body_style))
            story.append(Spacer(1, 0.2 * cm))

            if rc.get("affected_workflow") or rc.get("affected_activity"):
                story.append(Paragraph(
                    f"📍 Workflow: <b>{rc.get('affected_workflow', 'N/A')}</b> | "
                    f"Activity: <b>{rc.get('affected_activity', 'N/A')}</b>",
                    muted_style,
                ))

            for ev in (rc.get("evidence") or [])[:3]:
                story.append(Paragraph(f"• {ev}", code_style))

            if rc.get("suggested_fix"):
                story.append(Paragraph(f"<b>Suggested Fix:</b> {rc['suggested_fix']}", body_style))

            story.append(Spacer(1, 0.5 * cm))

        # ── Recommendations ───────────────────────────────────────────────── #
        recs = (report.recommendations or {}).get("items", [])
        if recs:
            story.append(PageBreak())
            story.append(Paragraph("Recommendations & Action Items", h2_style))
            for j, rec in enumerate(recs[:20], 1):
                story.append(Paragraph(f"{j}. {rec}", body_style))
            story.append(Spacer(1, 0.3 * cm))

        doc.build(story)
        return str(filename)

    def _generate_excel_sync(self, report: Any) -> str:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        reports_dir = Path(settings.REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = reports_dir / f"rca_{report.id}.xlsx"

        wb = Workbook()

        # ── Sheet 1: Summary ──────────────────────────────────────────────── #
        ws_sum = wb.active
        ws_sum.title = "Summary"
        ws_sum.column_dimensions["A"].width = 25
        ws_sum.column_dimensions["B"].width = 50

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1e3a5f")

        ws_sum.append(["Automation Project Debugger — RCA Report"])
        ws_sum["A1"].font = Font(bold=True, size=14)
        ws_sum.append([])
        ws_sum.append(["Field", "Value"])
        for cell in ws_sum[3]:
            cell.font = header_font
            cell.fill = header_fill

        meta = [
            ("Report ID", str(report.id)),
            ("Platform", str(getattr(report, "platform", "unknown")).upper()),
            ("Status", str(getattr(report, "status", "completed")).upper()),
            ("AI Analysis Used", "Yes" if getattr(report, "ai_used", False) else "No"),
            ("Overall Confidence", f"{(getattr(report, 'overall_confidence', 0) or 0) * 100:.0f}%"),
            ("Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]
        for row in meta:
            ws_sum.append(list(row))

        # ── Sheet 2: Root Causes ──────────────────────────────────────────── #
        ws_rc = wb.create_sheet("Root Causes")
        ws_rc.column_dimensions["A"].width = 5
        ws_rc.column_dimensions["B"].width = 20
        ws_rc.column_dimensions["C"].width = 30
        ws_rc.column_dimensions["D"].width = 50
        ws_rc.column_dimensions["E"].width = 12
        ws_rc.column_dimensions["F"].width = 12
        ws_rc.column_dimensions["G"].width = 50

        headers = ["#", "Category", "Title", "Description", "Severity", "Confidence", "Suggested Fix"]
        ws_rc.append(headers)
        for cell in ws_rc[1]:
            cell.font = header_font
            cell.fill = header_fill

        severity_fills = {
            "critical": PatternFill("solid", fgColor="fecaca"),
            "high": PatternFill("solid", fgColor="fed7aa"),
            "medium": PatternFill("solid", fgColor="fef08a"),
            "low": PatternFill("solid", fgColor="bbf7d0"),
        }

        root_causes = (report.root_causes or {}).get("causes", [])
        for i, rc in enumerate(root_causes, 1):
            row = [
                i,
                rc.get("category", ""),
                rc.get("title", ""),
                rc.get("description", ""),
                rc.get("severity", ""),
                f"{(rc.get('confidence', 0) or 0) * 100:.0f}%",
                rc.get("suggested_fix", ""),
            ]
            ws_rc.append(row)
            sev = rc.get("severity", "medium")
            fill = severity_fills.get(sev, severity_fills["medium"])
            for cell in ws_rc[ws_rc.max_row]:
                cell.fill = fill
                cell.alignment = Alignment(wrap_text=True)

        # ── Sheet 3: Recommendations ──────────────────────────────────────── #
        ws_recs = wb.create_sheet("Recommendations")
        ws_recs.column_dimensions["A"].width = 5
        ws_recs.column_dimensions["B"].width = 80
        ws_recs.append(["#", "Recommendation"])
        for cell in ws_recs[1]:
            cell.font = header_font
            cell.fill = header_fill

        for j, rec in enumerate((report.recommendations or {}).get("items", []), 1):
            ws_recs.append([j, rec])

        wb.save(str(filename))
        return str(filename)
