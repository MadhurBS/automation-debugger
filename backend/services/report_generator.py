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
        h2_style    = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#1e3a5f"), spaceAfter=4)
        h3_style    = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=12, textColor=colors.HexColor("#374151"), spaceAfter=3)
        body_style  = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)
        code_style  = ParagraphStyle("code", fontName="Courier", fontSize=9, leading=12, backColor=colors.HexColor("#f5f5f5"))
        muted_style = ParagraphStyle("muted", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
        info_style  = ParagraphStyle("info", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#1e40af"), backColor=colors.HexColor("#eff6ff"), leading=13)

        severity_colors = {
            "critical": colors.HexColor("#dc2626"),
            "high":     colors.HexColor("#ea580c"),
            "medium":   colors.HexColor("#ca8a04"),
            "low":      colors.HexColor("#16a34a"),
        }

        story = []

        # ── Cover ──────────────────────────────────────────────────────────── #
        story.append(Paragraph("Automation Project Debugger", title_style))
        story.append(Paragraph("Root Cause Analysis Report", h2_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 0.5 * cm))

        rpa_tool   = getattr(report, "rpa_tool", None) or ""
        has_log    = bool(getattr(report, "has_log", False))

        meta_data = [
            ["Report ID",         str(report.id)],
            ["Platform",          str(getattr(report, "platform", "unknown")).upper()],
            ["RPA Tool",          rpa_tool or "Auto-detected"],
            ["Status",            str(getattr(report, "status", "completed")).upper()],
            ["Analysis Mode",     "Runtime (Log-First)" if has_log else "Static (No Log)"],
            ["AI Analysis Used",  "Yes" if getattr(report, "ai_used", False) else "No (Heuristic)"],
            ["Overall Confidence",f"{(getattr(report, 'overall_confidence', 0) or 0) * 100:.0f}%"],
            ["Generated",         datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]

        meta_table = Table(meta_data, colWidths=[4 * cm, 13 * cm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4ff")),
            ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("PADDING",    (0, 0), (-1, -1), 6),
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

        # AI narrative summary
        ai_narrative = getattr(report, "ai_narrative", None) or {}
        if isinstance(ai_narrative, dict) and ai_narrative.get("runtime_error_summary"):
            story.append(Paragraph(
                f"<b>AI Analysis:</b> {ai_narrative['runtime_error_summary']}",
                info_style,
            ))
            story.append(Spacer(1, 0.3 * cm))

        story.append(Spacer(1, 0.5 * cm))

        # ── Runtime Analysis (when log present) ──────────────────────────── #
        runtime_analysis = getattr(report, "runtime_analysis", None) or {}
        if isinstance(runtime_analysis, dict) and runtime_analysis.get("has_log"):
            story.append(PageBreak())
            story.append(Paragraph("Runtime Analysis", h2_style))
            story.append(Paragraph(
                "(Based on uploaded execution log — this is the primary evidence source.)",
                muted_style,
            ))
            story.append(Spacer(1, 0.3 * cm))

            ra_fields = [
                ["Exception Type",    runtime_analysis.get("exception_type", "—")],
                ["Error Message",     (runtime_analysis.get("error_message") or "—")[:300]],
                ["Failure Category",  runtime_analysis.get("failure_category", "—")],
                ["Failed Workflow",   runtime_analysis.get("failed_workflow") or "Not identified"],
                ["Failed Activity",   runtime_analysis.get("failed_activity") or "Not identified"],
                ["Timestamp",         runtime_analysis.get("timestamp") or "—"],
            ]
            ra_table = Table(ra_fields, colWidths=[4 * cm, 13 * cm])
            ra_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff1f2")),
                ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
                ("PADDING",    (0, 0), (-1, -1), 6),
                ("WORDWRAP",   (1, 0), (1, -1), "WORD"),
            ]))
            story.append(ra_table)
            story.append(Spacer(1, 0.4 * cm))

            if runtime_analysis.get("root_cause_summary"):
                story.append(Paragraph("<b>Root Cause Summary:</b>", h3_style))
                story.append(Paragraph(runtime_analysis["root_cause_summary"], body_style))
                story.append(Spacer(1, 0.3 * cm))

            evidence = runtime_analysis.get("evidence_from_log", [])
            if evidence:
                story.append(Paragraph("<b>Evidence from Log:</b>", h3_style))
                for ev in evidence[:15]:
                    story.append(Paragraph(f"• {ev}", code_style))
                story.append(Spacer(1, 0.3 * cm))

            fixes = runtime_analysis.get("suggested_fixes", [])
            if fixes:
                story.append(Paragraph("<b>Suggested Fixes:</b>", h3_style))
                for fix in fixes:
                    story.append(Paragraph(f"• {fix}", body_style))
                story.append(Spacer(1, 0.3 * cm))

            steps = runtime_analysis.get("validation_steps", [])
            if steps:
                story.append(Paragraph("<b>Validation Steps:</b>", h3_style))
                for i, step in enumerate(steps, 1):
                    story.append(Paragraph(f"{i}. {step}", body_style))
                story.append(Spacer(1, 0.3 * cm))

            all_exc = runtime_analysis.get("all_exceptions", [])
            if len(all_exc) > 1:
                story.append(Paragraph(f"<b>All Exceptions ({len(all_exc)}):</b>", h3_style))
                for exc in all_exc[:20]:
                    story.append(Paragraph(
                        f"<b>{exc.get('type', 'Unknown')}:</b> {(exc.get('message') or '')[:200]}",
                        code_style,
                    ))
                story.append(Spacer(1, 0.3 * cm))

        # ── AI Narrative (detailed per-cause) ─────────────────────────────── #
        ai_details = (ai_narrative or {}).get("root_causes_detail", [])
        if ai_details:
            story.append(PageBreak())
            story.append(Paragraph("Detailed AI Analysis", h2_style))
            story.append(Paragraph(
                "11-point structured analysis produced by the AI engine per identified failure.",
                muted_style,
            ))
            story.append(Spacer(1, 0.3 * cm))

            for i, detail in enumerate(ai_details, 1):
                story.append(Paragraph(f"#{i} {detail.get('title', '')}", h3_style))
                d_fields = []
                if detail.get("affected_workflow"):
                    d_fields.append(["Workflow / Process", detail["affected_workflow"]])
                if detail.get("affected_activity"):
                    d_fields.append(["Activity / Stage",   detail["affected_activity"]])
                if detail.get("failure_category"):
                    d_fields.append(["Failure Category",   detail["failure_category"]])
                if detail.get("confidence_label"):
                    d_fields.append(["Confidence",         detail["confidence_label"]])
                if d_fields:
                    d_table = Table(d_fields, colWidths=[4 * cm, 13 * cm])
                    d_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4ff")),
                        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE",   (0, 0), (-1, -1), 9),
                        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                        ("PADDING",    (0, 0), (-1, -1), 5),
                    ]))
                    story.append(d_table)
                    story.append(Spacer(1, 0.2 * cm))
                if detail.get("what_was_happening"):
                    story.append(Paragraph(f"<b>What was happening:</b> {detail['what_was_happening']}", body_style))
                if detail.get("why_it_failed"):
                    story.append(Paragraph(f"<b>Why it failed:</b> {detail['why_it_failed']}", body_style))
                if detail.get("confidence_reasoning"):
                    story.append(Paragraph(f"<i>Confidence reasoning: {detail['confidence_reasoning']}</i>", muted_style))
                checks = detail.get("suggested_checks", [])
                if checks:
                    story.append(Paragraph("<b>Suggested Checks:</b>", body_style))
                    for j, chk in enumerate(checks, 1):
                        story.append(Paragraph(f"  {j}. {chk}", body_style))
                if detail.get("suggested_fix"):
                    story.append(Paragraph(f"<b>Recommended Fix:</b> {detail['suggested_fix']}", info_style))
                story.append(Spacer(1, 0.5 * cm))

        # ── Root Causes ───────────────────────────────────────────────────── #
        story.append(PageBreak())
        story.append(Paragraph("Root Causes", h2_style))
        for i, rc in enumerate(root_causes, 1):
            sev       = rc.get("severity", "medium")
            sev_color = severity_colors.get(sev, colors.grey)

            story.append(Paragraph(
                f'<b>#{i} [{sev.upper()}] {rc.get("title", "")}</b>',
                ParagraphStyle(f"rc_{i}", parent=h2_style, fontSize=12, textColor=sev_color),
            ))
            story.append(Paragraph(rc.get("description", ""), body_style))
            story.append(Spacer(1, 0.2 * cm))

            if rc.get("affected_workflow") or rc.get("affected_activity"):
                story.append(Paragraph(
                    f"Workflow: <b>{rc.get('affected_workflow', 'N/A')}</b> | "
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

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1e3a5f")
        sub_fill    = PatternFill("solid", fgColor="dbeafe")
        sub_font    = Font(bold=True, color="1e40af")
        wrap        = Alignment(wrap_text=True)

        # ── Sheet 1: Summary ──────────────────────────────────────────────── #
        ws_sum = wb.active
        ws_sum.title = "Summary"
        ws_sum.column_dimensions["A"].width = 28
        ws_sum.column_dimensions["B"].width = 55

        ws_sum.append(["Automation Project Debugger — RCA Report"])
        ws_sum["A1"].font = Font(bold=True, size=14)
        ws_sum.append([])

        ws_sum.append(["Field", "Value"])
        for cell in ws_sum[3]:
            cell.font = header_font
            cell.fill = header_fill

        rpa_tool  = getattr(report, "rpa_tool", None) or "Auto-detected"
        has_log   = bool(getattr(report, "has_log", False))
        ai_narrative = getattr(report, "ai_narrative", None) or {}

        meta = [
            ("Report ID",         str(report.id)),
            ("Platform",          str(getattr(report, "platform", "unknown")).upper()),
            ("RPA Tool",          rpa_tool),
            ("Status",            str(getattr(report, "status", "completed")).upper()),
            ("Analysis Mode",     "Runtime (Log-First)" if has_log else "Static (No Log)"),
            ("AI Analysis Used",  "Yes" if getattr(report, "ai_used", False) else "No"),
            ("Overall Confidence",f"{(getattr(report, 'overall_confidence', 0) or 0) * 100:.0f}%"),
            ("Generated At",      datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]
        if isinstance(ai_narrative, dict) and ai_narrative.get("runtime_error_summary"):
            meta.append(("AI Summary", ai_narrative["runtime_error_summary"]))

        for row in meta:
            ws_sum.append(list(row))
            ws_sum.cell(ws_sum.max_row, 2).alignment = wrap

        # ── Sheet 2: Runtime Analysis ─────────────────────────────────────── #
        ws_rt = wb.create_sheet("Runtime Analysis")
        ws_rt.column_dimensions["A"].width = 28
        ws_rt.column_dimensions["B"].width = 75

        ws_rt.append(["Runtime Analysis"])
        ws_rt["A1"].font = Font(bold=True, size=13)
        ws_rt.append([])

        ws_rt.append(["Field", "Value"])
        for cell in ws_rt[3]:
            cell.font = header_font
            cell.fill = header_fill

        runtime_analysis = getattr(report, "runtime_analysis", None) or {}
        if isinstance(runtime_analysis, dict) and runtime_analysis.get("has_log"):
            ra_rows = [
                ("Analysis Mode",     "Runtime — log file was primary evidence"),
                ("Exception Type",    runtime_analysis.get("exception_type", "—")),
                ("Error Message",     runtime_analysis.get("error_message", "—")),
                ("Failure Category",  runtime_analysis.get("failure_category", "—")),
                ("Failed Workflow",   runtime_analysis.get("failed_workflow") or "Not identified"),
                ("Failed Activity",   runtime_analysis.get("failed_activity") or "Not identified"),
                ("Timestamp",         runtime_analysis.get("timestamp") or "—"),
                ("Root Cause Summary", runtime_analysis.get("root_cause_summary", "—")),
            ]
            for row in ra_rows:
                ws_rt.append(list(row))
                ws_rt.cell(ws_rt.max_row, 2).alignment = wrap

            ws_rt.append([])
            ws_rt.append(["Evidence from Log"])
            ws_rt.cell(ws_rt.max_row, 1).font = sub_font
            ws_rt.cell(ws_rt.max_row, 1).fill = sub_fill
            for ev in (runtime_analysis.get("evidence_from_log") or [])[:15]:
                ws_rt.append(["", ev])
                ws_rt.cell(ws_rt.max_row, 2).alignment = wrap

            ws_rt.append([])
            ws_rt.append(["Suggested Fixes"])
            ws_rt.cell(ws_rt.max_row, 1).font = sub_font
            ws_rt.cell(ws_rt.max_row, 1).fill = sub_fill
            for fix in (runtime_analysis.get("suggested_fixes") or []):
                ws_rt.append(["", fix])
                ws_rt.cell(ws_rt.max_row, 2).alignment = wrap

            ws_rt.append([])
            ws_rt.append(["Validation Steps"])
            ws_rt.cell(ws_rt.max_row, 1).font = sub_font
            ws_rt.cell(ws_rt.max_row, 1).fill = sub_fill
            for i, step in enumerate((runtime_analysis.get("validation_steps") or []), 1):
                ws_rt.append([f"Step {i}", step])
                ws_rt.cell(ws_rt.max_row, 2).alignment = wrap

            all_exc = runtime_analysis.get("all_exceptions", [])
            if all_exc:
                ws_rt.append([])
                ws_rt.append([f"All Exceptions ({len(all_exc)})"])
                ws_rt.cell(ws_rt.max_row, 1).font = sub_font
                ws_rt.cell(ws_rt.max_row, 1).fill = sub_fill
                for exc in all_exc[:20]:
                    ws_rt.append([exc.get("type", "Unknown"), (exc.get("message") or "")[:200]])
                    ws_rt.cell(ws_rt.max_row, 2).alignment = wrap
        else:
            ws_rt.append(["Analysis Mode", "Static — no execution log was uploaded"])
            ws_rt.append(["Note", "Upload an execution log and re-run analysis to get runtime-based diagnosis."])

        # ── Sheet 3: AI Narrative ─────────────────────────────────────────── #
        ws_ai = wb.create_sheet("AI Narrative")
        ws_ai.column_dimensions["A"].width = 28
        ws_ai.column_dimensions["B"].width = 75

        ws_ai.append(["AI Detailed Analysis"])
        ws_ai["A1"].font = Font(bold=True, size=13)
        ws_ai.append([])

        ai_details = (ai_narrative or {}).get("root_causes_detail", []) if isinstance(ai_narrative, dict) else []
        if ai_details:
            for i, detail in enumerate(ai_details, 1):
                ws_ai.append([f"Failure #{i}", detail.get("title", "")])
                ws_ai.cell(ws_ai.max_row, 1).font = Font(bold=True)
                ws_ai.cell(ws_ai.max_row, 1).fill = PatternFill("solid", fgColor="fef3c7")
                ws_ai.cell(ws_ai.max_row, 2).font = Font(bold=True)
                ws_ai.cell(ws_ai.max_row, 2).alignment = wrap

                rows = [
                    ("Workflow / Process",   detail.get("affected_workflow")),
                    ("Activity / Stage",     detail.get("affected_activity")),
                    ("Failure Category",     detail.get("failure_category")),
                    ("Confidence",           detail.get("confidence_label")),
                    ("Confidence Reasoning", detail.get("confidence_reasoning")),
                    ("What was happening",   detail.get("what_was_happening")),
                    ("Why it failed",        detail.get("why_it_failed")),
                    ("Recommended Fix",      detail.get("suggested_fix")),
                ]
                for label, val in rows:
                    if val:
                        ws_ai.append([label, val])
                        ws_ai.cell(ws_ai.max_row, 2).alignment = wrap

                checks = detail.get("suggested_checks", [])
                for j, chk in enumerate(checks, 1):
                    ws_ai.append([f"Check {j}", chk])
                    ws_ai.cell(ws_ai.max_row, 2).alignment = wrap

                ws_ai.append([])
        else:
            ws_ai.append(["", "No AI narrative available (AI analysis not used or no OpenAI key configured)."])

        # ── Sheet 4: Root Causes ──────────────────────────────────────────── #
        ws_rc = wb.create_sheet("Root Causes")
        ws_rc.column_dimensions["A"].width = 5
        ws_rc.column_dimensions["B"].width = 20
        ws_rc.column_dimensions["C"].width = 30
        ws_rc.column_dimensions["D"].width = 55
        ws_rc.column_dimensions["E"].width = 12
        ws_rc.column_dimensions["F"].width = 12
        ws_rc.column_dimensions["G"].width = 55

        headers = ["#", "Category", "Title", "Description", "Severity", "Confidence", "Suggested Fix"]
        ws_rc.append(headers)
        for cell in ws_rc[1]:
            cell.font = header_font
            cell.fill = header_fill

        severity_fills = {
            "critical": PatternFill("solid", fgColor="fecaca"),
            "high":     PatternFill("solid", fgColor="fed7aa"),
            "medium":   PatternFill("solid", fgColor="fef08a"),
            "low":      PatternFill("solid", fgColor="bbf7d0"),
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
            sev  = rc.get("severity", "medium")
            fill = severity_fills.get(sev, severity_fills["medium"])
            for cell in ws_rc[ws_rc.max_row]:
                cell.fill = fill
                cell.alignment = Alignment(wrap_text=True)

        # ── Sheet 5: Recommendations ──────────────────────────────────────── #
        ws_recs = wb.create_sheet("Recommendations")
        ws_recs.column_dimensions["A"].width = 5
        ws_recs.column_dimensions["B"].width = 85
        ws_recs.append(["#", "Recommendation"])
        for cell in ws_recs[1]:
            cell.font = header_font
            cell.fill = header_fill

        for j, rec in enumerate((report.recommendations or {}).get("items", []), 1):
            ws_recs.append([j, rec])
            ws_recs.cell(ws_recs.max_row, 2).alignment = wrap

        wb.save(str(filename))
        return str(filename)
