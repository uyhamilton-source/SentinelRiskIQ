
from __future__ import annotations
from io import BytesIO
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

COMPANY_NAME = "Sentinel Risk Compliance Group"
TAGLINE = "Where Risk Becomes Strategy"

def build_client_report(controls_df: pd.DataFrame, result: dict, framework_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(COMPANY_NAME, styles["Title"]))
    story.append(Paragraph(TAGLINE, styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"{framework_name} Client Report", styles["Heading2"]))
    story.append(Paragraph(result["executive_summary"], styles["Normal"]))
    story.append(Spacer(1, 10))

    detail_df = controls_df[[
        "Control ID","Control Name","Status","Gap Type","Priority","Framework Citation"
    ]].head(12)
    data = [list(detail_df.columns)] + detail_df.astype(str).values.tolist()
    tbl = Table(data, repeatRows=1, colWidths=[60,140,55,90,55,130])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CBD5E1")),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)
    doc.build(story)
    return buffer.getvalue()
