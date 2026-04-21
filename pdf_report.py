
from io import BytesIO
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def build_client_report(controls_df: pd.DataFrame, result: dict, framework_name: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], textColor=colors.HexColor("#0A1F44"), fontSize=20))
    story = [Paragraph("SentinelRiskIQ Stable Platform", styles["BrandTitle"]), Paragraph(f"{framework_name} Client Report", styles["Heading2"]), Paragraph(result["executive_summary"], styles["Normal"]), Spacer(1, 10)]
    cols = [c for c in ["Control ID","Control Name","Status","Priority","Framework Citation","VMaaS Penalty","Adjusted Score"] if c in controls_df.columns]
    detail = controls_df[cols].head(12)
    data = [list(detail.columns)] + detail.astype(str).values.tolist()
    tbl = Table(data)
    tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1E3A8A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.black)]))
    story.append(tbl)
    doc.build(story)
    return buffer.getvalue()
