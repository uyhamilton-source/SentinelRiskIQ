
from __future__ import annotations
from io import BytesIO
import pandas as pd

PLATFORM_NAME = "RiskNavigator by SentinelRiskIQ™"
COMPANY_NAME = "Sentinel Risk Compliance Group"
STATUS_SCORE = {"Yes": 100, "Partial": 50, "No": 0}
SOC2_WEIGHTS = {"Logical Access": 0.16, "System Operations": 0.12, "Vendor Management": 0.10, "Communication": 0.06, "Control Activities": 0.10, "Incident Response": 0.10}
HIPAA_WEIGHTS = {"Technical": 0.30, "Risk Management": 0.15, "Administrative": 0.30, "Physical": 0.15, "Third-Party Oversight": 0.10}
CRITICAL = {"mfa enforcement", "data encryption", "real-time monitoring", "annual risk assessment", "vendor risk management"}

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

def normalize_yes_no_partial(value):
    s = str(value or "").strip().lower()
    if s in {"yes", "y", "true", "1"}:
        return "Yes"
    if s in {"partial", "some"}:
        return "Partial"
    return "No"

def normalize_yes_no(value):
    s = str(value or "").strip().lower()
    return "Yes" if s in {"yes", "y", "true", "1"} else "No"

def readiness_band(score):
    if score >= 85: return "Ready"
    if score >= 70: return "Near Ready"
    if score >= 50: return "Developing"
    return "Not Ready"

def build_control_intake_from_client_form(client_df):
    rows = []
    for _, row in client_df.iterrows():
        q = str(row.get("Question", "")).strip()
        a = normalize_yes_no_partial(row.get("Answer", ""))
        if q not in CLIENT_FORM_MAPPING:
            continue
        cid, fw, area, cname, critical = CLIENT_FORM_MAPPING[q]
        if a == "Yes":
            vals = ("Yes","Yes","Yes","Yes","Yes","Yes")
        elif a == "Partial":
            vals = ("Partial","Yes","No","Yes","No","No")
        else:
            vals = ("No","No","No","No","No","No")
        rows.append({
            "Control ID": cid, "Framework": fw, "Control Area": area, "Control Name": cname,
            "Status": vals[0], "Policy Exists": vals[1], "Procedure Exists": vals[2],
            "Owner Assigned": vals[3], "Evidence Available": vals[4], "Tested Recently": vals[5],
            "Critical Control": critical
        })
    return pd.DataFrame(rows)

def load_any_intake(file_obj_or_path):
    if hasattr(file_obj_or_path, "read"):
        data = file_obj_or_path.read()
        file_obj_or_path.seek(0)
        name = getattr(file_obj_or_path, "name", "").lower()
        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))
        xls = pd.ExcelFile(BytesIO(data))
        if "Client Form" in xls.sheet_names:
            return build_control_intake_from_client_form(pd.read_excel(BytesIO(data), sheet_name="Client Form"))
        return pd.read_excel(BytesIO(data), sheet_name="Control Intake")
    path = str(file_obj_or_path)
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    xls = pd.ExcelFile(path)
    if "Client Form" in xls.sheet_names:
        return build_control_intake_from_client_form(pd.read_excel(path, sheet_name="Client Form"))
    return pd.read_excel(path, sheet_name="Control Intake")

def score_control(row):
    status = normalize_yes_no_partial(row.get("Status"))
    policy = normalize_yes_no(row.get("Policy Exists"))
    procedure = normalize_yes_no(row.get("Procedure Exists"))
    owner = normalize_yes_no(row.get("Owner Assigned"))
    evidence = normalize_yes_no(row.get("Evidence Available"))
    tested = normalize_yes_no(row.get("Tested Recently"))
    fw = str(row.get("Framework", "")).strip()
    area = str(row.get("Control Area", "")).strip()
    cname = str(row.get("Control Name", "")).strip()
    score = float(STATUS_SCORE[status])
    if policy == "No": score -= 20
    if procedure == "No": score -= 15
    if owner == "No": score -= 10
    if evidence == "No": score -= 10
    if tested == "No": score -= 15
    critical = normalize_yes_no(row.get("Critical Control", "No")) == "Yes" or cname.lower() in CRITICAL
    if critical and status != "Yes": score -= 25
    score = max(0.0, min(100.0, score))
    if policy == "No":
        gap = "Design Gap"
    elif procedure == "No" or owner == "No":
        gap = "Implementation Gap"
    elif tested == "No":
        gap = "Operating Effectiveness Gap"
    else:
        gap = "No Major Gap"
    return {
        "Control ID": row.get("Control ID", ""), "Framework": fw, "Control Area": area, "Control Name": cname,
        "Status": status, "Policy Exists": policy, "Procedure Exists": procedure, "Owner Assigned": owner,
        "Evidence Available": evidence, "Tested Recently": tested, "Critical Control": "Yes" if critical else "No",
        "Critical Finding": "2026 critical control not fully implemented." if critical and status != "Yes" else "",
        "Framework Citation": area, "Row Score": round(score, 2), "Readiness Band": readiness_band(score),
        "Priority": "High" if critical and status != "Yes" else ("High" if score < 50 else "Medium" if score < 75 else "Low"),
        "Gap Type": gap,
        "Design Gap": "Required standard is not fully documented." if gap == "Design Gap" else "",
        "Implementation Gap": "Control is not consistently executed, evidenced, or tested." if gap != "No Major Gap" else "",
        "Recommended Actions": "Document policy, define procedure, assign owner, retain evidence, and perform testing." if gap != "No Major Gap" else "Maintain and monitor control performance."
    }

def prepare_controls(df):
    if "Critical Control" not in df.columns:
        df["Critical Control"] = "No"
    return pd.DataFrame([score_control(r.to_dict()) for _, r in df.iterrows()])

def calculate_framework_readiness(df, framework):
    scope = df[df["Framework"] == framework].copy()
    if scope.empty:
        return {"framework": framework, "overall_score": 0.0, "readiness_band": "Not Ready", "counts": {"controls": 0, "high_priority": 0, "critical_findings": 0}, "area_scores": {}, "critical_items": [], "top_controls": [], "top_actions": [], "executive_summary": f"No {framework} controls found."}
    weights = HIPAA_WEIGHTS if framework == "HIPAA" else SOC2_WEIGHTS
    area_scores = scope.groupby("Control Area")["Row Score"].mean().round(2).to_dict()
    weighted_total = 0.0
    total_weight = 0.0
    for area, score in area_scores.items():
        w = weights.get(area, 0.05)
        weighted_total += score * w
        total_weight += w
    overall = round(weighted_total / total_weight, 2) if total_weight else round(scope["Row Score"].mean(), 2)
    critical_items = scope[(scope["Critical Control"] == "Yes") & (scope["Status"] != "Yes")][["Control ID","Control Name","Status","Priority","Critical Finding","Framework Citation"]].to_dict(orient="records")
    counts = {"controls": int(len(scope)), "high_priority": int((scope["Priority"] == "High").sum()), "critical_findings": int(len(critical_items))}
    sorted_scope = scope.sort_values(["Priority","Row Score"], ascending=[True,True])
    top_controls = sorted_scope[["Control ID","Control Area","Control Name","Status","Row Score","Priority","Gap Type","Framework Citation"]].head(8).to_dict(orient="records")
    top_actions = sorted_scope[["Control Name","Priority","Recommended Actions"]].head(6).to_dict(orient="records")
    summary = f"The {framework} assessment combines RiskNavigator-style reporting with SentinelRiskIQ scoring and supports both client-friendly workbook uploads and direct control intake uploads."
    return {"framework": framework, "overall_score": overall, "readiness_band": readiness_band(overall), "counts": counts, "area_scores": area_scores, "critical_items": critical_items, "top_controls": top_controls, "top_actions": top_actions, "executive_summary": summary}

def calculate_combined_readiness(df):
    soc2 = calculate_framework_readiness(df, "SOC 2")
    hipaa = calculate_framework_readiness(df, "HIPAA")
    overall = round((soc2["overall_score"] + hipaa["overall_score"]) / 2, 2)
    return {"framework": "Combined", "overall_score": overall, "readiness_band": readiness_band(overall), "soc2": soc2, "hipaa": hipaa, "critical_findings": soc2["critical_items"] + hipaa["critical_items"], "top_controls": pd.concat([pd.DataFrame(soc2["top_controls"]), pd.DataFrame(hipaa["top_controls"])], ignore_index=True).head(10).to_dict(orient="records"), "top_actions": (soc2["top_actions"] + hipaa["top_actions"])[:8], "executive_summary": f"Combined readiness is {overall:.1f}. This full package unifies RiskNavigator and SentinelRiskIQ."}

def build_output_tables(df):
    controls = df.copy()
    gap_table = controls[["Framework","Control ID","Control Name","Critical Control","Critical Finding","Gap Type","Design Gap","Implementation Gap","Priority","Framework Citation"]].copy()
    recs = controls[["Framework","Control ID","Control Name","Critical Control","Priority","Recommended Actions"]].copy()
    return controls, gap_table, recs
