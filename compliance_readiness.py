
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd

STATUS_SCORE = {"Yes": 100, "Partial": 50, "No": 0}

SOC2_WEIGHTS = {
    "Control Environment": 0.10,
    "Communication": 0.08,
    "Risk Management": 0.12,
    "Control Activities": 0.12,
    "Logical Access": 0.18,
    "System Operations": 0.15,
    "Change Management": 0.10,
    "Incident Response": 0.10,
    "Availability": 0.03,
    "Confidentiality": 0.02,
}

HIPAA_WEIGHTS = {
    "Administrative": 0.40,
    "Physical": 0.20,
    "Technical": 0.40,
}

SOC2_CONTROL_LOOKUP = {
    "logical access": "CC6.3",
    "control activities": "CC5.2",
    "system operations": "CC7.1",
    "change management": "CC7.2",
    "incident response": "CC7.3",
    "availability": "A1.2",
    "risk management": "CC3.1",
    "control environment": "CC1.2",
    "communication": "CC2.1",
    "confidentiality": "C1.1",
}

HIPAA_CONTROL_LOOKUP = {
    "administrative": "45 CFR 164.308",
    "physical": "45 CFR 164.310",
    "technical": "45 CFR 164.312",
}

SOC2_DESIGN_GAP_LOOKUP = {
    "logical access": "No enterprise-wide standard for identity, access, and MFA requirements.",
    "control activities": "Control activities are not fully defined, documented, or tied to accountable owners.",
    "system operations": "Patch and vulnerability management standards are not consistently formalized.",
    "change management": "Logging, monitoring, and change evidence requirements are not clearly defined.",
    "incident response": "Incident response roles, escalation paths, and testing requirements are not fully documented.",
    "availability": "Backup and recovery expectations are not consistently defined or evidenced.",
    "risk management": "Formal risk assessment and review processes are not fully established.",
    "control environment": "Security governance roles and oversight responsibilities are not consistently documented.",
    "communication": "Policy communication and awareness expectations are not consistently established.",
    "confidentiality": "Data handling and confidentiality control requirements are not fully standardized.",
}

SOC2_IMPLEMENTATION_GAP_LOOKUP = {
    "logical access": "Access controls exist in part, but MFA and access enforcement are not consistently deployed.",
    "control activities": "Control execution varies across teams and supporting evidence is incomplete.",
    "system operations": "Patching and remediation occur inconsistently across systems and time periods.",
    "change management": "Logging and monitoring are present in some areas, but review and retention are inconsistent.",
    "incident response": "Response activities are informal or partially practiced, with limited testing evidence.",
    "availability": "Backups may exist, but restoration testing and supporting records are incomplete.",
    "risk management": "Risk reviews occur inconsistently and are not always tied to formal decisions.",
    "control environment": "Governance expectations are partially in place but not applied uniformly.",
    "communication": "Security communication occurs, but it is not consistently reinforced or evidenced.",
    "confidentiality": "Confidentiality measures are partially implemented but not consistently evidenced.",
}

HIPAA_DESIGN_GAP_LOOKUP = {
    "administrative": "Administrative safeguard requirements, roles, and governance expectations are not fully documented or standardized.",
    "physical": "Physical safeguard requirements for facilities, devices, and media are not fully defined or formalized.",
    "technical": "Technical safeguard requirements for access, audit controls, integrity, and transmission security are not consistently standardized.",
}

HIPAA_IMPLEMENTATION_GAP_LOOKUP = {
    "administrative": "Administrative safeguards exist in part, but execution, training, and evidence are inconsistent across the organization.",
    "physical": "Physical safeguards are partially in place, but control performance and supporting evidence are inconsistent.",
    "technical": "Technical safeguards are partially implemented, but enforcement, monitoring, and evidence are inconsistent.",
}


def normalize_yes_no_partial(value: Any) -> str:
    value = str(value or "").strip()
    if value in STATUS_SCORE:
        return value
    lowered = value.lower()
    if lowered in {"y", "yes", "true", "1"}:
        return "Yes"
    if lowered in {"partial", "some"}:
        return "Partial"
    return "No"


def normalize_yes_no(value: Any) -> str:
    value = str(value or "").strip()
    if value in {"Yes", "No"}:
        return value
    return "Yes" if value.lower() in {"y", "true", "1", "yes"} else "No"


def calc_boolean_bonus(row: Dict[str, Any]) -> int:
    bonus_fields = ["evidence_available", "owner_assigned", "policy_exists", "procedure_exists", "tested_recently"]
    bonus = 0
    for field in bonus_fields:
        if normalize_yes_no(row.get(field)) == "Yes":
            bonus += 5
    return min(bonus, 25)


def infer_framework(control_id: str, explicit: Optional[str] = None) -> str:
    if explicit and str(explicit).strip():
        value = str(explicit).strip().upper().replace(" ", "")
        if value in {"SOC2", "SOC-2"}:
            return "SOC 2"
        if value in {"HIPAA", "HIPPA"}:
            return "HIPAA"
    cid = str(control_id or "").upper()
    if cid.startswith("HIPAA-"):
        return "HIPAA"
    if cid.startswith("SOC2-") or cid.startswith("CC") or cid.startswith("A1") or cid.startswith("C1"):
        return "SOC 2"
    return "SOC 2"


def load_control_intake(file_obj_or_path: Any) -> pd.DataFrame:
    if hasattr(file_obj_or_path, "read"):
        name = getattr(file_obj_or_path, "name", "").lower()
        if name.endswith(".csv"):
            return pd.read_csv(file_obj_or_path)
        return pd.read_excel(file_obj_or_path, sheet_name="Control Intake")
    path = str(file_obj_or_path)
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name="Control Intake")


def row_score(row: Dict[str, Any]) -> Optional[float]:
    if normalize_yes_no(row.get("in_scope")) != "Yes":
        return None
    base = STATUS_SCORE[normalize_yes_no_partial(row.get("status"))]
    return float(min(base + calc_boolean_bonus(row), 100))


def readiness_band(score: float) -> str:
    if score >= 85:
        return "Ready"
    if score >= 70:
        return "Near Ready"
    if score >= 50:
        return "Developing"
    return "Not Ready"


def prepare_controls(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.strip() for c in df.columns}).copy()
    if "framework" not in df.columns:
        df["framework"] = ""
    required = [
        "control_id", "control_area", "control_name", "in_scope", "status",
        "evidence_available", "owner_assigned", "policy_exists", "procedure_exists", "tested_recently", "framework"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    yn_fields = ["in_scope", "evidence_available", "owner_assigned", "policy_exists", "procedure_exists", "tested_recently"]
    for col in yn_fields:
        df[col] = df[col].apply(normalize_yes_no)
    df["status"] = df["status"].apply(normalize_yes_no_partial)
    df["framework"] = df.apply(lambda r: infer_framework(r.get("control_id"), r.get("framework")), axis=1)
    df["row_score"] = df.apply(lambda row: row_score(row.to_dict()), axis=1)
    df["priority_hint"] = df["row_score"].apply(lambda x: None if pd.isna(x) else ("High" if x < 50 else "Medium" if x < 70 else "Low"))
    return df


def _framework_config(framework: str):
    if framework == "HIPAA":
        return HIPAA_WEIGHTS, HIPAA_CONTROL_LOOKUP, HIPAA_DESIGN_GAP_LOOKUP, HIPAA_IMPLEMENTATION_GAP_LOOKUP, "HIPAA"
    return SOC2_WEIGHTS, SOC2_CONTROL_LOOKUP, SOC2_DESIGN_GAP_LOOKUP, SOC2_IMPLEMENTATION_GAP_LOOKUP, "SOC 2"


def build_gap_analysis(in_scope: pd.DataFrame, framework: str) -> List[Dict[str, Any]]:
    if in_scope.empty:
        return []
    _, citations, design_lookup, impl_lookup, fw_label = _framework_config(framework)
    gaps=[]
    gap_candidates = in_scope.sort_values(["row_score", "control_area", "control_id"]).copy()
    for _, row in gap_candidates.iterrows():
        if row["row_score"] >= 85:
            continue
        area = str(row["control_area"]).strip()
        area_key = area.lower()
        gaps.append({
            "control": row["control_name"],
            "control_id": row["control_id"],
            "control_area": area,
            "design_gap": design_lookup.get(area_key, "The control requirement is not fully defined, documented, or standardized."),
            "implementation_gap": impl_lookup.get(area_key, "The control exists in part, but execution and evidence are inconsistent."),
            "citation": citations.get(area_key, row["control_id"]),
            "framework": fw_label,
            "status": row["status"],
            "row_score": float(row["row_score"]),
            "priority": "High" if row["row_score"] < 50 else "Medium",
        })
    return gaps[:8]


def build_executive_summary(overall: float, band: str, area_scores: Dict[str, float], gaps: List[Dict[str, Any]], framework: str) -> str:
    weakest_areas = sorted(area_scores.items(), key=lambda item: item[1])[:3]
    weakest_text = ", ".join(area for area, _ in weakest_areas) if weakest_areas else "core control areas"
    top_gap_lines = "\n".join(f"- {gap['control_id']} ({gap['citation']}): {gap['control']}" for gap in gaps[:3]) or "- No major blockers identified"
    if framework == "HIPAA":
        fw_phrase = "HIPAA safeguard readiness"
        compliance_name = "HIPAA"
        extra = "These issues may limit the organization’s ability to demonstrate appropriate administrative, physical, and technical safeguards for protected health information."
    elif framework == "Combined":
        fw_phrase = "combined SOC 2 and HIPAA readiness"
        compliance_name = "SOC 2 and HIPAA"
        extra = "These issues may limit the organization’s ability to demonstrate readiness across both audit-driven and healthcare-specific compliance expectations."
    else:
        fw_phrase = "SOC 2 readiness"
        compliance_name = "SOC 2"
        extra = "These issues may limit the organization’s ability to demonstrate readiness for SOC 2 and related stakeholder expectations."
    return (
        f"The RiskNavigator™ assessment identified several key cybersecurity and compliance risks that require executive attention. "
        f"The organization currently reflects a {band} level of control maturity, with an overall {fw_phrase} score of {overall:.1f}. "
        f"Current exposure is driven primarily by gaps in {weakest_text}, where control design and consistency remain underdeveloped.\n\n"
        "Several foundational controls are partially in place, but weaknesses in formal control design, ownership, and evidence collection "
        "increase the risk of operational disruption, audit exceptions, and delayed remediation. "
        f"{extra}\n\n"
        "Immediate focus should be placed on formalizing core security controls, standardizing implementation across in-scope systems, and closing the most material blockers listed below.\n\n"
        f"Top blockers for {compliance_name}:\n{top_gap_lines}"
    )


def _calculate_for_framework(df: pd.DataFrame, framework: str) -> Dict[str, Any]:
    weights, _, _, _, fw_label = _framework_config(framework)
    in_scope = df[(df["in_scope"] == "Yes") & (df["framework"] == fw_label)].copy()
    if in_scope.empty:
        return {
            "framework": fw_label,
            "overall_score": 0.0,
            "readiness_band": "Not Ready",
            "area_scores": {},
            "counts": {"in_scope": 0, "ready": 0, "partial": 0, "missing": 0},
            "top_gaps": [],
            "recommendations": [],
            "gaps": [],
            "executive_summary": f"No in-scope {fw_label} controls were provided, so readiness could not be determined.",
        }
    area_scores = in_scope.groupby("control_area")["row_score"].mean().round(2).to_dict()
    weighted_total = 0.0
    total_weight = 0.0
    for area, score in area_scores.items():
        weight = weights.get(area, 0.05)
        weighted_total += score * weight
        total_weight += weight
    overall = round(weighted_total / total_weight, 2) if total_weight else 0.0
    band = readiness_band(overall)
    counts = {
        "in_scope": int(len(in_scope)),
        "ready": int((in_scope["row_score"] >= 85).sum()),
        "partial": int(((in_scope["row_score"] >= 50) & (in_scope["row_score"] < 85)).sum()),
        "missing": int((in_scope["row_score"] < 50).sum()),
    }
    top_gaps_df = in_scope.sort_values(["row_score", "control_area", "control_id"]).head(8)
    top_gaps = top_gaps_df[["control_id","control_area","control_name","status","row_score","priority_hint"]].to_dict(orient="records")
    recommendations=[]
    for area, score in sorted(area_scores.items(), key=lambda item: item[1])[:5]:
        recommendations.append({
            "area": area,
            "score": score,
            "priority": "High" if score < 50 else "Medium",
            "recommendation": (
                "Establish and formally document the control standard, assign accountable ownership, and gather audit-ready evidence."
                if score < 70 else
                "Complete operating evidence, validate control performance, and prepare walkthrough support for review."
            ),
        })
    gaps = build_gap_analysis(in_scope, fw_label)
    executive_summary = build_executive_summary(overall, band, area_scores, gaps, fw_label)
    return {
        "framework": fw_label,
        "overall_score": overall,
        "readiness_band": band,
        "area_scores": area_scores,
        "counts": counts,
        "top_gaps": top_gaps,
        "recommendations": recommendations,
        "gaps": gaps,
        "executive_summary": executive_summary,
    }


def calculate_soc2_readiness(df: pd.DataFrame) -> Dict[str, Any]:
    return _calculate_for_framework(df, "SOC 2")


def calculate_hipaa_readiness(df: pd.DataFrame) -> Dict[str, Any]:
    return _calculate_for_framework(df, "HIPAA")


def calculate_combined_readiness(df: pd.DataFrame) -> Dict[str, Any]:
    soc2 = calculate_soc2_readiness(df)
    hipaa = calculate_hipaa_readiness(df)
    area_scores={}
    for k,v in soc2["area_scores"].items():
        area_scores[f"SOC 2 — {k}"]=v
    for k,v in hipaa["area_scores"].items():
        area_scores[f"HIPAA — {k}"]=v
    scores = [x for x in [soc2["overall_score"], hipaa["overall_score"]] if x > 0]
    overall = round(sum(scores) / len(scores), 2) if scores else 0.0
    band = readiness_band(overall)
    counts = {
        "in_scope": soc2["counts"]["in_scope"] + hipaa["counts"]["in_scope"],
        "ready": soc2["counts"]["ready"] + hipaa["counts"]["ready"],
        "partial": soc2["counts"]["partial"] + hipaa["counts"]["partial"],
        "missing": soc2["counts"]["missing"] + hipaa["counts"]["missing"],
    }
    gaps = sorted(soc2["gaps"] + hipaa["gaps"], key=lambda x: (0 if x["priority"]=="High" else 1, x["row_score"]))[:10]
    recommendations = (soc2["recommendations"][:3] + hipaa["recommendations"][:3])[:6]
    executive_summary = build_executive_summary(overall, band, area_scores, gaps, "Combined")
    return {
        "framework": "Combined",
        "overall_score": overall,
        "readiness_band": band,
        "area_scores": area_scores,
        "counts": counts,
        "top_gaps": [{**g, "priority_hint": g["priority"]} for g in gaps],
        "recommendations": recommendations,
        "gaps": gaps,
        "executive_summary": executive_summary,
        "framework_breakdown": {"SOC 2": soc2, "HIPAA": hipaa},
    }
