
from __future__ import annotations
from datetime import date
from io import BytesIO
from typing import Any
import pandas as pd

PLATFORM_NAME = "SentinelRiskIQ Stable Platform"
COMPANY_NAME = "Sentinel Risk Compliance Group"

STATUS_SCORE = {"Yes": 100, "Partial": 50, "No": 0}
SOC2_WEIGHTS = {"Logical Access": 0.16, "System Operations": 0.12, "Vendor Management": 0.10}
HIPAA_WEIGHTS = {"Technical": 0.30, "Risk Management": 0.15}

CRITICAL_CONTROLS = {"mfa enforcement", "data encryption", "real-time monitoring", "annual risk assessment", "vendor risk management"}

CONTROL_CROSSWALK = {
    "MFA Enforcement": {"SOC2": "CC6.3", "HIPAA": "164.312(d)", "NIST": "IA-2"},
    "Data Encryption": {"SOC2": "CC6.7", "HIPAA": "164.312(a)", "NIST": "SC-13"},
    "Real-Time Monitoring": {"SOC2": "CC7.2", "HIPAA": "164.312(b)", "NIST": "AU-6"},
    "Annual Risk Assessment": {"SOC2": "CC3.2", "HIPAA": "164.308(a)(1)(ii)(A)", "NIST": "RA-3"},
    "Vendor Risk Management": {"SOC2": "CC9.2", "HIPAA": "164.308(b)(1)", "NIST": "SR-3"},
}

def normalize_yes_no_partial(value: Any) -> str:
    s = str(value or "").strip().lower()
    if s in {"yes", "y", "true", "1"}:
        return "Yes"
    if s in {"partial", "some"}:
        return "Partial"
    return "No"

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

def load_any_intake(file_obj_or_path: Any) -> pd.DataFrame:
    if hasattr(file_obj_or_path, "read"):
        data = file_obj_or_path.read()
        file_obj_or_path.seek(0)
        name = getattr(file_obj_or_path, "name", "").lower()
        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))
        xls = pd.ExcelFile(BytesIO(data))
        return pd.read_excel(BytesIO(data), sheet_name="Control Intake")
    path = str(file_obj_or_path)
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name="Control Intake")

def score_control(row: dict) -> dict:
    status = normalize_yes_no_partial(row.get("Status"))
    framework = str(row.get("Framework", "")).strip()
    area = str(row.get("Control Area", "")).strip()
    name = str(row.get("Control Name", "")).strip()
    score = float(STATUS_SCORE[status])
    if str(row.get("Policy Exists", "")).strip().lower() != "yes":
        score -= 20
    if str(row.get("Procedure Exists", "")).strip().lower() != "yes":
        score -= 15
    if str(row.get("Owner Assigned", "")).strip().lower() != "yes":
        score -= 10
    if str(row.get("Evidence Available", "")).strip().lower() != "yes":
        score -= 10
    if str(row.get("Tested Recently", "")).strip().lower() != "yes":
        score -= 15
    critical = str(row.get("Critical Control", "No")).strip().lower() == "yes" or name.lower() in CRITICAL_CONTROLS
    if critical and status != "Yes":
        score -= 25
    score = max(0.0, min(100.0, score))
    mapping = CONTROL_CROSSWALK.get(name, {})
    citation = mapping.get("SOC2", "") if framework == "SOC 2" else mapping.get("HIPAA", "")
    return {
        "Control ID": row.get("Control ID", ""),
        "Framework": framework,
        "Control Area": area,
        "Control Name": name,
        "Status": status,
        "Critical Control": "Yes" if critical else "No",
        "Framework Citation": citation,
        "NIST Mapping": mapping.get("NIST", ""),
        "Row Score": round(score, 2),
        "Priority": "High" if score < 50 else ("Medium" if score < 75 else "Low"),
        "Recommended Actions": "Document policy, define procedure, assign owner, retain evidence, and perform testing." if score < 100 else "Maintain and monitor control performance.",
    }

def prepare_controls(df: pd.DataFrame) -> pd.DataFrame:
    if "Critical Control" not in df.columns:
        df["Critical Control"] = "No"
    return pd.DataFrame([score_control(r.to_dict()) for _, r in df.iterrows()])

def calculate_framework_readiness(df: pd.DataFrame, framework: str) -> dict:
    scope = df[df["Framework"] == framework].copy()
    if scope.empty:
        return {"overall_score": 0.0, "readiness_band": "Not Ready", "counts": {"high_priority": 0, "critical_findings": 0}, "executive_summary": f"No {framework} controls found."}
    area_scores = scope.groupby("Control Area")["Row Score"].mean().round(2).to_dict()
    overall = round(scope["Row Score"].mean(), 2)
    critical_findings = int(((scope["Critical Control"] == "Yes") & (scope["Row Score"] < 100)).sum())
    return {
        "overall_score": overall,
        "readiness_band": readiness_band(overall),
        "counts": {"high_priority": int((scope["Priority"] == "High").sum()), "critical_findings": critical_findings},
        "area_scores": area_scores,
        "top_actions": scope[["Control Name", "Priority", "Recommended Actions"]].head(6).to_dict(orient="records"),
        "critical_items": scope[(scope["Critical Control"] == "Yes") & (scope["Row Score"] < 100)][["Control ID","Control Name","Priority","Framework Citation"]].to_dict(orient="records"),
        "top_controls": scope[["Control ID","Control Area","Control Name","Status","Row Score","Priority"]].head(8).to_dict(orient="records"),
        "executive_summary": f"The {framework} assessment score is {overall:.1f}.",
    }

def calculate_combined_readiness(df: pd.DataFrame) -> dict:
    soc2 = calculate_framework_readiness(df, "SOC 2")
    hipaa = calculate_framework_readiness(df, "HIPAA")
    overall = round((soc2["overall_score"] + hipaa["overall_score"]) / 2, 2)
    return {
        "overall_score": overall,
        "soc2": soc2,
        "hipaa": hipaa,
        "critical_findings": soc2["critical_items"] + hipaa["critical_items"],
        "top_controls": (soc2["top_controls"] + hipaa["top_controls"])[:10],
        "top_actions": (soc2["top_actions"] + hipaa["top_actions"])[:8],
        "executive_summary": f"Combined readiness is {overall:.1f}.",
    }

def build_output_tables(df: pd.DataFrame):
    return df.copy(), df.copy(), df.copy()

def build_risk_register(df: pd.DataFrame):
    out = []
    for _, row in df.iterrows():
        out.append({"Risk ID": f"R-{row['Control ID']}", "Risk Description": f"Failure of {row['Control Name']}", "Risk Score": row["Row Score"], "Mitigation": row["Recommended Actions"]})
    return out

def generate_policy_text(control_name: str, framework: str) -> str:
    return f"{control_name} Policy\nFramework: {framework}\nDate: {date.today()}\n\n1. Purpose\nThis policy establishes controls and procedures for {control_name.lower()}."
