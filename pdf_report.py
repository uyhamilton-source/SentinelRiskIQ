
from io import BytesIO
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

PLATFORM_NAME = "RiskNavigator by SentinelRiskIQ™"
COMPANY_NAME = "Sentinel Risk Compliance Group"
TAGLINE = "Where Risk Becomes Strategy"

def build_client_report(controls_df: pd.DataFrame, result: dict, framework_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], textColor=colors.HexColor("#0A1F44"), fontSize=20))
    story = []
    story.append(Paragraph(PLATFORM_NAME, styles["BrandTitle"]))
    story.append(Paragraph(COMPANY_NAME, styles["Normal"]))
    story.append(Paragraph(TAGLINE, styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"{framework_name} Client Report", styles["Heading2"]))
    story.append(Paragraph(result["executive_summary"], styles["Normal"]))
    story.append(Spacer(1, 10))
    summary = Table([
        ["Overall Score","Readiness Band","High Priority","Critical Findings"],
        [f"{result['overall_score']:.1f}", result["readiness_band"], str(result["counts"].get("high_priority", 0)), str(result["counts"].get("critical_findings", 0))]
    ], colWidths=[110,110,110,120])
    summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0A1F44")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),("ALIGN",(0,0),(-1,-1),"CENTER")]))
    story.append(summary)
    story.append(Spacer(1,10))
    detail = controls_df[["Control ID","Control Name","Status","Critical Control","Gap Type","Priority","Framework Citation"]].head(12)
    data = [list(detail.columns)] + detail.astype(str).values.tolist()
    tbl = Table(data, repeatRows=1, colWidths=[50,125,50,55,85,50,110])
    tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1E3A8A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#CBD5E1")),("FONTSIZE",(0,0),(-1,-1),7)]))
    story.append(tbl)
    doc.build(story)
    return buffer.getvalue()
