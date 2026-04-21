
from __future__ import annotations

from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

BRAND_NAME = "SentinelRiskIQ™"
COMPANY_NAME = "Sentinel Risk Compliance Group"
TAGLINE = "Where Risk Becomes Strategy"


def build_client_report(controls_df: pd.DataFrame, result: dict, output_path: str | Path, framework_name: str) -> Path:
    output_path = Path(output_path)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=38,
        bottomMargin=38,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], textColor=colors.HexColor("#0A1F44"), fontSize=22))
    styles.add(ParagraphStyle(name="BrandSub", parent=styles["Normal"], textColor=colors.HexColor("#A78BFA"), fontSize=11))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#1E3A8A"), fontSize=14))

    story = []
    story.append(Paragraph(COMPANY_NAME, styles["BrandTitle"]))
    story.append(Paragraph(TAGLINE, styles["BrandSub"]))
    story.append(Spacer(1, 8))

    divider = Table([[""]], colWidths=[520])
    divider.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 3, colors.HexColor("#C9A646"))]))
    story.append(divider)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"{framework_name} Client Report", styles["Section"]))
    story.append(Paragraph(result["executive_summary"], styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("How the intake maps to this report", styles["Section"]))
    story.append(
        Paragraph(
            "Each output row is generated directly from the intake fields. Status sets the base score. Policy Exists "
            "drives Design Gap detection. Procedure Exists and Owner Assigned drive Implementation Gap detection. "
            "Evidence Available and Tested Recently drive Operating Effectiveness and priority.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 10))

    summary_tbl = Table(
        [
            ["Overall Score", "Readiness Band", "High Priority Controls", "Total Controls"],
            [
                f"{result['overall_score']:.1f}",
                result["readiness_band"],
                str(result["counts"].get("high_priority", 0)),
                str(result["counts"].get("controls", 0)),
            ],
        ],
        colWidths=[120, 120, 140, 120],
    )
    summary_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A1F44")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C0C7D1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(summary_tbl)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Control detail matched to intake columns", styles["Section"]))
    report_df = controls_df[controls_df["Framework"] == framework_name][
        [
            "Control ID",
            "Control Name",
            "Status",
            "Policy Exists",
            "Procedure Exists",
            "Tested Recently",
            "Gap Type",
            "Priority",
            "Framework Citation",
        ]
    ].head(12)

    data = [list(report_df.columns)] + report_df.astype(str).values.tolist()
    report_tbl = Table(data, repeatRows=1, colWidths=[55, 120, 50, 55, 60, 60, 85, 50, 85])
    report_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C0C7D1")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(report_tbl)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Prioritized remediation plan", styles["Section"]))
    for action in result["top_actions"][:5]:
        story.append(
            Paragraph(
                f"<b>{action['Control Name']}</b> — {action['Priority']} priority<br/>{action['Recommended Actions']}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 6))

    doc.build(story)
    return output_path
