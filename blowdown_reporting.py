from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@dataclass
class BlowdownReportBundle:
    title: str
    text: str
    summary_rows: list[tuple[str, str]]
    generated_on: str
    software_version: str


def _draw_page_decorations(canvas: Canvas, _doc, *, footer_text: str) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(36, 24, footer_text)
    canvas.drawRightString(A4[0] - 36, 24, f"Sayfa {canvas.getPageNumber()}")
    canvas.restoreState()


def export_blowdown_report_csv(path: str | Path, bundle: BlowdownReportBundle) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Alan", "Değer"])
        for key, value in bundle.summary_rows:
            writer.writerow([key, value])


def export_blowdown_report_pdf(path: str | Path, bundle: BlowdownReportBundle) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    footer_text = "Bu rapor screening amaçlıdır; son tasarım doğrulaması için API standartlarına başvurun."

    story = [
        Paragraph(escape(bundle.title), styles["Title"]),
        Spacer(1, 6),
        Paragraph(escape(f"Tarih: {bundle.generated_on} | {bundle.software_version}"), styles["Normal"]),
        Spacer(1, 12),
    ]

    table = Table([["Alan", "Değer"], *bundle.summary_rows], colWidths=[190, 330])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    story.extend([table, Spacer(1, 16), Paragraph("Detaylı Sonuçlar", styles["Heading2"])])
    for line in bundle.text.splitlines():
        story.append(Paragraph(escape(line) or "&nbsp;", styles["Code"]))

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page_decorations(canvas, doc, footer_text=footer_text),
        onLaterPages=lambda canvas, doc: _draw_page_decorations(canvas, doc, footer_text=footer_text),
    )
