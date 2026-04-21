
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

def build_pdf(readiness: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"RiskNavigator™ {readiness.get('framework','Combined')} Executive Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Overall Score: <b>{readiness.get('overall_score',0):.1f}</b> | Readiness Band: <b>{readiness.get('readiness_band','')}</b>", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Executive Summary</b>", styles["Heading2"]))
    story.append(Paragraph(readiness.get("executive_summary","No summary available.").replace("\n","<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 12))

    gaps = readiness.get("gaps", [])[:6]
    if gaps:
        story.append(Paragraph("<b>Design vs Implementation Gaps</b>", styles["Heading2"]))
        data = [["Control ID", "Framework", "Citation", "Priority"]]
        for g in gaps:
            data.append([g.get("control_id",""), g.get("framework",""), g.get("citation",""), g.get("priority","")])
        table = Table(data, colWidths=[90, 80, 140, 70])
        table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#0A1F44")),
            ("TEXTCOLOR",(0,0),(-1,0), colors.white),
            ("GRID",(0,0),(-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.whitesmoke, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    recs = readiness.get("recommendations", [])[:5]
    if recs:
        story.append(Paragraph("<b>Prioritized Next Actions</b>", styles["Heading2"]))
        for idx, rec in enumerate(recs, start=1):
            story.append(Paragraph(f"{idx}. <b>{rec.get('area','')}</b> — {rec.get('recommendation','')}", styles["BodyText"]))
            story.append(Spacer(1, 6))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
