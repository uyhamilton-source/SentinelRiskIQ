
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Tuple
import pandas as pd

STATUS_SCORE = {"Yes": 100, "Partial": 50, "No": 0}
DESIGN_PENALTY = 20
IMPLEMENTATION_PENALTY = 15
OWNERSHIP_PENALTY = 10
EVIDENCE_PENALTY = 10
TESTING_PENALTY = 15

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
    "Vendor Management": 0.10,
}
HIPAA_WEIGHTS = {
    "Administrative": 0.30,
    "Physical": 0.15,
    "Technical": 0.30,
    "Risk Management": 0.15,
    "Third-Party Oversight": 0.10,
}

SOC2_CONTROL_LOOKUP = {
    "logical access": "CC6.3",
    "control activities": "CC5.2",
    "system operations": "CC7.1",
    "change management": "CC8.1",
    "incident response": "CC7.3",
    "availability": "A1.2",
    "risk management": "CC3.2",
    "control environment": "CC1.1",
    "communication": "CC2.2",
    "confidentiality": "C1.1",
    "vendor management": "CC9.2",
}
HIPAA_CONTROL_LOOKUP = {
    "administrative": "45 CFR 164.308",
    "physical": "45 CFR 164.310",
    "technical": "45 CFR 164.312",
    "risk management": "45 CFR 164.308(a)(1)(ii)(A)",
    "third-party oversight": "45 CFR 164.308(b)(1)",
}

CLIENT_FORM_MAPPING = {
    "Do users use multi-factor authentication (MFA)?": ("CTRL-001", "SOC 2", "Logical Access", "MFA Enforcement", "Yes"),
    "Is sensitive data encrypted at rest and in transit?": ("CTRL-002", "HIPAA", "Technical", "Data Encryption", "Yes"),
    "Are systems monitored in real time for suspicious activity?": ("CTRL-003", "SOC 2", "System Operations", "Real-Time Monitoring", "Yes"),
    "Do you perform a formal risk assessment at least annually?": ("CTRL-004", "HIPAA", "Risk Management", "Annual Risk Assessment", "Yes"),
    "Are vendors reviewed for security and compliance risk?": ("CTRL-005", "SOC 2", "Vendor Management", "Vendor Risk Management", "Yes"),
    "Do you have a documented incident response plan?": ("CTRL-006", "SOC 2", "Incident Response", "Incident Response Plan", "No"),
    "Are user access permissions reviewed regularly?": ("CTRL-007", "SOC 2", "Control Activities", "Access Reviews", "No"),
    "Do you have documented security policies that staff can access?": ("CTRL-008", "SOC 2", "Communication", "Policy Governance", "No"),
    "Do employees receive security awareness training?": ("CTRL-009", "HIPAA", "Administrative", "Security Training", "No"),
    "Are backups performed and restoration tested regularly?": ("CTRL-010", "HIPAA", "Physical", "Backup and Recovery", "No"),
}

def normalize_yes_no_partial(value: Any) -> str:
    value = str(value or "").strip()
    lowered = value.lower()
    if lowered in {"yes", "y", "true", "1"}:
        return "Yes"
    if lowered in {"partial", "some"}:
        return "Partial"
    return "No"

def normalize_yes_no(value: Any) -> str:
    value = str(value or "").strip()
    lowered = value.lower()
    return "Yes" if lowered in {"yes", "y", "true", "1"} else "No"

def build_control_intake_from_client_form(client_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in client_df.iterrows():
        question = str(row.get("Question", "")).strip()
        answer = str(row.get("Answer", "")).strip()
        if not question or question not in CLIENT_FORM_MAPPING:
            continue

        control_id, framework, area, control_name, critical = CLIENT_FORM_MAPPING[question]
        answer_norm = normalize_yes_no_partial(answer)

        if answer_norm == "Yes":
            status = "Yes"
            policy = "Yes"
            procedure = "Yes"
            owner = "Yes"
            evidence = "Yes"
            tested = "Yes"
        elif answer_norm == "Partial":
            status = "Partial"
            policy = "Yes"
            procedure = "No"
            owner = "Yes"
            evidence = "No"
            tested = "No"
        else:
            status = "No"
            policy = "No"
            procedure = "No"
            owner = "No"
            evidence = "No"
            tested = "No"

        rows.append({
            "Control ID": control_id,
            "Framework": framework,
            "Control Area": area,
            "Control Name": control_name,
            "Status": status,
            "Policy Exists": policy,
            "Procedure Exists": procedure,
            "Owner Assigned": owner,
            "Evidence Available": evidence,
            "Tested Recently": tested,
            "Critical Control": critical,
        })
    return pd.DataFrame(rows)

def load_any_intake(file_obj_or_path: Any) -> pd.DataFrame:
    if hasattr(file_obj_or_path, "read"):
        data = file_obj_or_path.read()
        file_obj_or_path.seek(0)
        name = getattr(file_obj_or_path, "name", "").lower()

        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))

        xls = pd.ExcelFile(BytesIO(data))
        sheet_names = [s.strip() for s in xls.sheet_names]

        if "Client Form" in sheet_names:
            client_df = pd.read_excel(BytesIO(data), sheet_name="Client Form")
            return build_control_intake_from_client_form(client_df)

        if "Control Intake" in sheet_names:
            return pd.read_excel(BytesIO(data), sheet_name="Control Intake")

        raise ValueError("Workbook must contain either 'Client Form' or 'Control Intake' sheet.")

    path = str(file_obj_or_path)
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    xls = pd.ExcelFile(path)
    if "Client Form" in xls.sheet_names:
        client_df = pd.read_excel(path, sheet_name="Client Form")
        return build_control_intake_from_client_form(client_df)
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
    framework = str(row.get("Framework", "")).strip()
    area = str(row.get("Control Area", "")).strip()

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

    gap_type = classify_gap_type(policy, procedure, tested, owner)

    if framework == "HIPAA":
        citation = HIPAA_CONTROL_LOOKUP.get(area.lower(), "")
    else:
        citation = SOC2_CONTROL_LOOKUP.get(area.lower(), row.get("Control ID", ""))

    return {
        "Control ID": row.get("Control ID", ""),
        "Framework": framework,
        "Control Area": area,
        "Control Name": row.get("Control Name", ""),
        "Status": status,
        "Policy Exists": policy,
        "Procedure Exists": procedure,
        "Owner Assigned": owner,
        "Evidence Available": evidence,
        "Tested Recently": tested,
        "Critical Control": row.get("Critical Control", "No"),
        "Framework Citation": citation,
        "Row Score": round(score, 2),
        "Readiness Band": readiness_band(score),
        "Priority": priority_from_score(score),
        "Gap Type": gap_type,
        "Design Gap": "The required control standard is not fully documented or formally approved." if gap_type == "Design Gap" else "",
        "Implementation Gap": "The control is not consistently executed, evidenced, or tested." if gap_type != "No Major Gap" else "",
        "Recommended Actions": "Document policy, define procedure, assign owner, retain evidence, and perform testing." if gap_type != "No Major Gap" else "Maintain and monitor control performance.",
    }

def prepare_controls(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "Control ID","Framework","Control Area","Control Name","Status",
        "Policy Exists","Procedure Exists","Owner Assigned","Evidence Available","Tested Recently"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return pd.DataFrame([score_control(r.to_dict()) for _, r in df.iterrows()])

def calculate_framework_readiness(df: pd.DataFrame, framework: str) -> Dict[str, Any]:
    scope = df[df["Framework"] == framework].copy()
    if scope.empty:
        return {"framework": framework, "overall_score": 0.0, "readiness_band": "Not Ready", "counts": {"controls": 0, "high_priority": 0}, "area_scores": {}, "top_controls": [], "top_actions": [], "executive_summary": f"No {framework} controls found."}
    weights = HIPAA_WEIGHTS if framework == "HIPAA" else SOC2_WEIGHTS
    area_scores = scope.groupby("Control Area")["Row Score"].mean().round(2).to_dict()
    weighted_total = 0.0
    total_weight = 0.0
    for area, score in area_scores.items():
        w = weights.get(area, 0.05)
        weighted_total += score * w
        total_weight += w
    overall = round(weighted_total / total_weight, 2) if total_weight else 0.0
    counts = {"controls": int(len(scope)), "high_priority": int((scope["Priority"] == "High").sum())}
    sorted_scope = scope.sort_values(["Row Score", "Control Area", "Control ID"])
    top_controls = sorted_scope[["Control ID","Control Area","Control Name","Status","Row Score","Priority","Gap Type","Framework Citation"]].head(8).to_dict(orient="records")
    top_actions = sorted_scope[sorted_scope["Priority"].isin(["High","Medium"])][["Control Name","Priority","Recommended Actions"]].head(5).to_dict(orient="records")
    summary = f"The {framework} assessment was scored automatically from the uploaded workbook. If a client-friendly workbook was uploaded, answers from the Client Form were converted into backend Control Intake rows before scoring."
    return {"framework": framework, "overall_score": overall, "readiness_band": readiness_band(overall), "counts": counts, "area_scores": area_scores, "top_controls": top_controls, "top_actions": top_actions, "executive_summary": summary}

def calculate_combined_readiness(df: pd.DataFrame) -> Dict[str, Any]:
    soc2 = calculate_framework_readiness(df, "SOC 2")
    hipaa = calculate_framework_readiness(df, "HIPAA")
    overall = round((soc2["overall_score"] + hipaa["overall_score"]) / 2, 2)
    return {"framework": "Combined", "overall_score": overall, "readiness_band": readiness_band(overall), "top_controls": pd.concat([pd.DataFrame(soc2["top_controls"]), pd.DataFrame(hipaa["top_controls"])], ignore_index=True).head(10).to_dict(orient="records"), "top_actions": (soc2["top_actions"] + hipaa["top_actions"])[:6], "executive_summary": f"Combined readiness is {overall:.1f}. This result supports both direct Control Intake uploads and client-friendly workbook uploads.", "soc2": soc2, "hipaa": hipaa}

def build_output_tables(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    controls = df.copy()
    gap_table = controls[["Framework","Control ID","Control Name","Gap Type","Design Gap","Implementation Gap","Priority","Framework Citation"]].copy()
    recs = controls[["Framework","Control ID","Control Name","Priority","Recommended Actions"]].copy()
    return controls, gap_table, recs
