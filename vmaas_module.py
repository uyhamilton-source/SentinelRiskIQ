
from __future__ import annotations
from io import BytesIO
from typing import Any
import pandas as pd

SEVERITY_PENALTIES = {"Critical": 35, "High": 25, "Medium": 15, "Low": 5, "Informational": 0}

VMASS_CONTROL_MAPPING = {
    "Authentication": ("Logical Access", "MFA Enforcement", "SOC 2", "Yes"),
    "Encryption": ("Technical", "Data Encryption", "HIPAA", "Yes"),
    "Monitoring": ("System Operations", "Real-Time Monitoring", "SOC 2", "Yes"),
    "Third Party": ("Vendor Management", "Vendor Risk Management", "SOC 2", "Yes"),
    "Governance": ("Risk Management", "Annual Risk Assessment", "HIPAA", "Yes"),
}

KEYWORD_CONTROL_MAPPING = [
    ("mfa", ("Logical Access", "MFA Enforcement", "SOC 2", "Yes")),
    ("encryption", ("Technical", "Data Encryption", "HIPAA", "Yes")),
    ("tls", ("Technical", "Data Encryption", "HIPAA", "Yes")),
    ("monitor", ("System Operations", "Real-Time Monitoring", "SOC 2", "Yes")),
    ("vendor", ("Vendor Management", "Vendor Risk Management", "SOC 2", "Yes")),
    ("risk assessment", ("Risk Management", "Annual Risk Assessment", "HIPAA", "Yes")),
]

def load_vmaas_input(file_obj_or_path: Any) -> pd.DataFrame:
    if hasattr(file_obj_or_path, "read"):
        data = file_obj_or_path.read()
        file_obj_or_path.seek(0)
        name = getattr(file_obj_or_path, "name", "").lower()
        if name.endswith(".csv"):
            return pd.read_csv(BytesIO(data))
        return pd.read_excel(BytesIO(data))
    path = str(file_obj_or_path)
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)

def detect_input_mode(df: pd.DataFrame) -> str:
    cols = {c.strip().lower() for c in df.columns}
    if {"asset", "vulnerability", "severity", "status"}.issubset(cols):
        return "automatic"
    if {"asset", "issue", "severity", "status"}.issubset(cols):
        return "manual"
    raise ValueError("Unsupported VMaaS file format.")

def map_finding_to_control(title: str, finding_type=None):
    if finding_type and finding_type in VMASS_CONTROL_MAPPING:
        return VMASS_CONTROL_MAPPING[finding_type]
    text = (title or "").lower()
    for keyword, mapping in KEYWORD_CONTROL_MAPPING:
        if keyword in text:
            return mapping
    return ("System Operations", "General Vulnerability Management", "SOC 2", "No")

def normalize_vmaas_findings(df: pd.DataFrame) -> pd.DataFrame:
    mode = detect_input_mode(df)
    rows = []
    if mode == "automatic":
        for i, row in df.iterrows():
            area, control, framework, critical = map_finding_to_control(str(row.get("Vulnerability", "")), str(row.get("Finding Type", "")).strip() or None)
            rows.append({"Finding ID": f"VM-{i+1:03d}", "Asset": row.get("Asset", ""), "Title": row.get("Vulnerability", ""), "Severity": row.get("Severity", "Low"), "Status": row.get("Status", "Open"), "Mapped Framework": framework, "Mapped Control Area": area, "Mapped Control Name": control, "Critical Control": critical})
    else:
        for i, row in df.iterrows():
            area, control, framework, critical = map_finding_to_control(str(row.get("Issue", "")))
            rows.append({"Finding ID": f"VM-{i+1:03d}", "Asset": row.get("Asset", ""), "Title": row.get("Issue", ""), "Severity": row.get("Severity", "Low"), "Status": row.get("Status", "Open"), "Mapped Framework": framework, "Mapped Control Area": area, "Mapped Control Name": control, "Critical Control": critical})
    return pd.DataFrame(rows)

def summarize_vmaas_findings(findings_df: pd.DataFrame) -> pd.DataFrame:
    if findings_df.empty:
        return pd.DataFrame(columns=["Framework","Control Area","Control Name","Critical Control","Open Findings","Max Severity","VMaaS Penalty","VMaaS Summary"])
    open_df = findings_df[findings_df["Status"].astype(str).str.lower() != "closed"].copy()
    if open_df.empty:
        return pd.DataFrame(columns=["Framework","Control Area","Control Name","Critical Control","Open Findings","Max Severity","VMaaS Penalty","VMaaS Summary"])
    severity_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1, "Informational": 0}
    open_df["SeverityRank"] = open_df["Severity"].map(severity_rank).fillna(0)
    inverse = {v: k for k, v in severity_rank.items()}
    grouped = []
    for (fw, area, control, critical), g in open_df.groupby(["Mapped Framework","Mapped Control Area","Mapped Control Name","Critical Control"]):
        max_rank = int(g["SeverityRank"].max())
        max_sev = inverse[max_rank]
        penalty = SEVERITY_PENALTIES.get(max_sev, 0)
        grouped.append({"Framework": fw, "Control Area": area, "Control Name": control, "Critical Control": critical, "Open Findings": int(len(g)), "Max Severity": max_sev, "VMaaS Penalty": penalty, "VMaaS Summary": f"{len(g)} open finding(s), highest severity {max_sev}."})
    return pd.DataFrame(grouped)

def apply_vmaas_to_controls(controls_df: pd.DataFrame, summary_df: pd.DataFrame) -> pd.DataFrame:
    out = controls_df.copy()
    out["VMaaS Penalty"] = 0
    out["VMaaS Summary"] = ""
    out["Adjusted Score"] = out["Row Score"]
    if out.empty or summary_df.empty:
        return out
    for i, row in out.iterrows():
        match = summary_df[(summary_df["Framework"] == row["Framework"]) & (summary_df["Control Area"] == row["Control Area"]) & (summary_df["Control Name"] == row["Control Name"])]
        if not match.empty:
            penalty = int(match["VMaaS Penalty"].max())
            out.at[i, "VMaaS Penalty"] = penalty
            out.at[i, "VMaaS Summary"] = " | ".join(match["VMaaS Summary"].astype(str).tolist())
            out.at[i, "Adjusted Score"] = max(0, float(row["Row Score"]) - penalty)
    return out
