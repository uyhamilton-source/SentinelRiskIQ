
from __future__ import annotations

from typing import Any, Dict, Tuple
import pandas as pd

BRAND_NAME = "SentinelRiskIQ™"

STATUS_SCORE = {"Yes": 100, "Partial": 50, "No": 0}

# Penalties are applied after the base status score.
DESIGN_PENALTY = 20              # Policy Exists = No
IMPLEMENTATION_PENALTY = 15      # Procedure Exists = No
OWNERSHIP_PENALTY = 10           # Owner Assigned = No
EVIDENCE_PENALTY = 10            # Evidence Available = No
TESTING_PENALTY = 15             # Tested Recently = No

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

DESIGN_GAP_LOOKUP = {
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
    "administrative": "Administrative safeguards are not fully documented, assigned, or standardized.",
    "physical": "Physical safeguards are not fully defined or consistently documented.",
    "technical": "Technical safeguards are not fully standardized or formally required.",
}

IMPLEMENTATION_GAP_LOOKUP = {
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
    "administrative": "Administrative safeguards are partially implemented, but execution and evidence are inconsistent.",
    "physical": "Physical safeguards exist in part, but operational enforcement is inconsistent.",
    "technical": "Technical safeguards are partially implemented, but effectiveness and evidence are inconsistent.",
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
    return "Yes" if value.lower() in {"y", "yes", "true", "1"} else "No"


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


def readiness_band(score: float) -> str:
    if score >= 85:
        return "Ready"
    if score >= 70:
        return "Near Ready"
    if score >= 50:
        return "Developing"
    return "Not Ready"


def priority_from_score(score: float) -> str:
    if score < 50:
        return "High"
    if score < 75:
        return "Medium"
    return "Low"


def classify_gap_type(policy_exists: str, procedure_exists: str, tested_recently: str, owner_assigned: str) -> str:
    if policy_exists == "No":
        return "Design Gap"
    if procedure_exists == "No" or owner_assigned == "No":
        return "Implementation Gap"
    if tested_recently == "No":
        return "Operating Effectiveness Gap"
    return "No Major Gap"


def score_control(row: Dict[str, Any]) -> Dict[str, Any]:
    status = normalize_yes_no_partial(row.get("Status"))
    policy = normalize_yes_no(row.get("Policy Exists"))
    procedure = normalize_yes_no(row.get("Procedure Exists"))
    tested = normalize_yes_no(row.get("Tested Recently"))
    owner = normalize_yes_no(row.get("Owner Assigned"))
    evidence = normalize_yes_no(row.get("Evidence Available"))

    score = float(STATUS_SCORE[status])

    if policy == "No":
        score -= DESIGN_PENALTY
    if procedure == "No":
        score -= IMPLEMENTATION_PENALTY
    if owner == "No":
        score -= OWNERSHIP_PENALTY
    if evidence == "No":
        score -= EVIDENCE_PENALTY
    if tested == "No":
        score -= TESTING_PENALTY

    score = max(0.0, min(100.0, score))

    framework = str(row.get("Framework", "")).strip()
    area = str(row.get("Control Area", "")).strip()
    area_key = area.lower()
    gap_type = classify_gap_type(policy, procedure, tested, owner)

    if framework == "HIPAA":
        framework_citation = HIPAA_CONTROL_LOOKUP.get(area_key, "")
    else:
        framework_citation = SOC2_CONTROL_LOOKUP.get(area_key, row.get("Control ID", ""))

    design_gap = ""
    implementation_gap = ""

    if gap_type == "Design Gap":
        design_gap = DESIGN_GAP_LOOKUP.get(
            area_key, "The control requirement is not fully defined, documented, or standardized."
        )
    elif gap_type == "Implementation Gap":
        design_gap = "Control design is partially present, but execution standards are incomplete."
        implementation_gap = IMPLEMENTATION_GAP_LOOKUP.get(
            area_key, "The control exists in part, but execution and evidence are inconsistent."
        )
    elif gap_type == "Operating Effectiveness Gap":
        design_gap = "Control design appears present."
        implementation_gap = "Control is not consistently tested or evidenced."

    actions = []
    if policy == "No":
        actions.append("Document and approve a formal policy standard.")
    if procedure == "No":
        actions.append("Define and implement an operating procedure.")
    if owner == "No":
        actions.append("Assign accountable control ownership.")
    if evidence == "No":
        actions.append("Collect and retain audit-ready evidence.")
    if tested == "No":
        actions.append("Perform and document control testing.")
    if not actions:
        actions.append("Maintain and monitor control performance.")

    return {
        "Control ID": row.get("Control ID", ""),
        "Framework": framework,
        "Control Area": area,
        "Control Name": row.get("Control Name", ""),
        "Status": status,
        "Evidence Available": evidence,
        "Owner Assigned": owner,
        "Policy Exists": policy,
        "Procedure Exists": procedure,
        "Tested Recently": tested,
        "Row Score": round(score, 2),
        "Readiness Band": readiness_band(score),
        "Priority": priority_from_score(score),
        "Gap Type": gap_type,
        "Design Gap": design_gap,
        "Implementation Gap": implementation_gap,
        "Framework Citation": framework_citation,
        "Recommended Actions": " ".join(actions),
    }


def prepare_controls(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.strip() for c in df.columns}).copy()
    alias_map = {
        "control_id": "Control ID",
        "framework": "Framework",
        "control_area": "Control Area",
        "control_name": "Control Name",
        "status": "Status",
        "evidence_available": "Evidence Available",
        "owner_assigned": "Owner Assigned",
        "policy_exists": "Policy Exists",
        "procedure_exists": "Procedure Exists",
        "tested_recently": "Tested Recently",
    }
    df = df.rename(columns=alias_map)

    required = [
        "Control ID",
        "Framework",
        "Control Area",
        "Control Name",
        "Status",
        "Evidence Available",
        "Owner Assigned",
        "Policy Exists",
        "Procedure Exists",
        "Tested Recently",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    rows = [score_control(r.to_dict()) for _, r in df.iterrows()]
    return pd.DataFrame(rows)


def calculate_framework_readiness(df: pd.DataFrame, framework: str) -> Dict[str, Any]:
    scope = df[df["Framework"] == framework].copy()
    if scope.empty:
        return {
            "framework": framework,
            "overall_score": 0.0,
            "readiness_band": "Not Ready",
            "counts": {"controls": 0, "high_priority": 0, "medium_priority": 0, "low_priority": 0},
            "area_scores": {},
            "top_controls": [],
            "top_actions": [],
            "executive_summary": f"No {framework} controls were found in the uploaded intake.",
        }

    weights = HIPAA_WEIGHTS if framework == "HIPAA" else SOC2_WEIGHTS
    area_scores = scope.groupby("Control Area")["Row Score"].mean().round(2).to_dict()

    weighted_total = 0.0
    total_weight = 0.0
    for area, score in area_scores.items():
        weight = weights.get(area, 0.05)
        weighted_total += score * weight
        total_weight += weight
    overall = round(weighted_total / total_weight, 2) if total_weight else 0.0

    counts = {
        "controls": int(len(scope)),
        "high_priority": int((scope["Priority"] == "High").sum()),
        "medium_priority": int((scope["Priority"] == "Medium").sum()),
        "low_priority": int((scope["Priority"] == "Low").sum()),
    }

    sorted_scope = scope.sort_values(["Row Score", "Control Area", "Control ID"])
    top_controls = sorted_scope[
        ["Control ID", "Control Area", "Control Name", "Status", "Row Score", "Priority", "Gap Type", "Framework Citation"]
    ].head(8).to_dict(orient="records")

    top_actions = (
        sorted_scope[sorted_scope["Priority"].isin(["High", "Medium"])]
        [["Control Name", "Priority", "Recommended Actions"]]
        .head(5)
        .to_dict(orient="records")
    )

    weakest = ", ".join([a for a, _ in sorted(area_scores.items(), key=lambda x: x[1])[:3]]) or "core control areas"

    executive_summary = (
        f"The {framework} assessment indicates a {readiness_band(overall)} level of readiness, with an overall score of "
        f"{overall:.1f}. The weakest areas are {weakest}. Scoring is mapped directly from the intake: Status sets the "
        f"base score, Policy Exists drives design maturity, Procedure Exists and Owner Assigned drive implementation "
        f"maturity, and Evidence Available plus Tested Recently drive operating effectiveness."
    )

    return {
        "framework": framework,
        "overall_score": overall,
        "readiness_band": readiness_band(overall),
        "counts": counts,
        "area_scores": area_scores,
        "top_controls": top_controls,
        "top_actions": top_actions,
        "executive_summary": executive_summary,
    }


def calculate_combined_readiness(df: pd.DataFrame) -> Dict[str, Any]:
    soc2 = calculate_framework_readiness(df, "SOC 2")
    hipaa = calculate_framework_readiness(df, "HIPAA")
    overall = round((soc2["overall_score"] + hipaa["overall_score"]) / 2, 2)

    return {
        "framework": "Combined",
        "overall_score": overall,
        "readiness_band": readiness_band(overall),
        "counts": {"controls": int(len(df))},
        "top_controls": pd.concat(
            [pd.DataFrame(soc2["top_controls"]), pd.DataFrame(hipaa["top_controls"])],
            ignore_index=True,
        ).head(10).to_dict(orient="records"),
        "top_actions": (soc2["top_actions"] + hipaa["top_actions"])[:6],
        "executive_summary": (
            f"Combined readiness is {overall:.1f}, with SOC 2 at {soc2['overall_score']:.1f} and HIPAA at "
            f"{hipaa['overall_score']:.1f}. This combined view uses the same direct intake-to-output scoring model "
            f"and preserves framework-specific gap visibility."
        ),
        "soc2": soc2,
        "hipaa": hipaa,
    }


def build_output_tables(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scored_controls = df.copy()
    design_impl = scored_controls[
        ["Framework", "Control ID", "Control Name", "Gap Type", "Design Gap", "Implementation Gap", "Priority", "Framework Citation"]
    ].copy()
    recommendations = scored_controls[
        ["Framework", "Control ID", "Control Name", "Priority", "Recommended Actions"]
    ].copy()
    return scored_controls, design_impl, recommendations
