
from pathlib import Path
import pandas as pd
import streamlit as st
from compliance_readiness import (
    PLATFORM_NAME, COMPANY_NAME, load_any_intake, prepare_controls,
    calculate_framework_readiness, calculate_combined_readiness, build_output_tables,
    build_risk_register, generate_policy_text, CONTROL_CROSSWALK
)
from pdf_report import build_client_report
from vmaas_module import load_vmaas_input, normalize_vmaas_findings, summarize_vmaas_findings, apply_vmaas_to_controls

BASE_DIR = Path(__file__).parent
SAMPLE_CSV = BASE_DIR / "sample_data" / "stable_sample_intake.csv"
VMAAS_TOOL_SAMPLE = BASE_DIR / "sample_data" / "vmaas_tool_import_sample.csv"
VMAAS_MANUAL_SAMPLE = BASE_DIR / "sample_data" / "vmaas_manual_upload_sample.csv"
FALLBACK_USER = "admin"
FALLBACK_PASS = "admin123"

TIER_MODULES = {
    "core": {"vmaas": False, "risk_register": False, "policy_generator": False},
    "pro": {"vmaas": True, "risk_register": True, "policy_generator": True},
    "enterprise": {"vmaas": True, "risk_register": True, "policy_generator": True},
}

st.set_page_config(page_title=PLATFORM_NAME, page_icon=":shield:", layout="wide")

def get_credentials():
    try:
        return st.secrets["auth"]["username"], st.secrets["auth"]["password"]
    except Exception:
        return FALLBACK_USER, FALLBACK_PASS

def init_state():
    for k, v in {"logged_in": False, "tier": "core", "controls_df": None, "soc2": None, "hipaa": None, "combined": None, "vmaas_findings": None, "vmaas_summary": None}.items():
        if k not in st.session_state:
            st.session_state[k] = v

def login_view():
    uexp, pexp = get_credentials()
    st.title(PLATFORM_NAME)
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            if u == uexp and p == pexp:
                st.session_state.logged_in = True
                st.rerun()
            st.error("Invalid credentials.")
    st.caption("Demo: admin / admin123")

def recalc(controls):
    st.session_state.controls_df = controls
    st.session_state.soc2 = calculate_framework_readiness(controls, "SOC 2")
    st.session_state.hipaa = calculate_framework_readiness(controls, "HIPAA")
    st.session_state.combined = calculate_combined_readiness(controls)

def process_intake(uploaded):
    raw = load_any_intake(uploaded)
    recalc(prepare_controls(raw))

def process_vmaas(uploaded):
    raw = load_vmaas_input(uploaded)
    findings = normalize_vmaas_findings(raw)
    summary = summarize_vmaas_findings(findings)
    st.session_state.vmaas_findings = findings
    st.session_state.vmaas_summary = summary
    if st.session_state.controls_df is not None:
        recalc(apply_vmaas_to_controls(st.session_state.controls_df, summary))

def render_overview():
    c = st.session_state.combined
    s2 = st.session_state.soc2
    h = st.session_state.hipaa
    st.subheader("Combined Dashboard")
    st.write(c["executive_summary"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Combined Score", f"{c['overall_score']:.1f}")
    col2.metric("SOC 2", f"{s2['overall_score']:.1f}")
    col3.metric("HIPAA", f"{h['overall_score']:.1f}")
    st.dataframe(pd.DataFrame(c["top_controls"]), use_container_width=True)

def render_framework(name, result):
    st.subheader(name)
    st.write(result["executive_summary"])
    df = st.session_state.controls_df
    detail = df[df["Framework"] == name]
    st.dataframe(detail, use_container_width=True)
    st.download_button(f"Download {name} PDF", build_client_report(detail, result, name), file_name=f"{name}.pdf", mime="application/pdf")

def render_modules():
    if TIER_MODULES[st.session_state.tier]["risk_register"]:
        st.subheader("Risk Register")
        st.dataframe(pd.DataFrame(build_risk_register(st.session_state.controls_df)), use_container_width=True)
    else:
        st.info("Risk Register available in Pro and Enterprise tiers.")
    if TIER_MODULES[st.session_state.tier]["policy_generator"]:
        st.subheader("Policy Generator")
        names = st.session_state.controls_df["Control Name"].dropna().unique().tolist()
        if names:
            selected = st.selectbox("Select control", names)
            fw = st.session_state.controls_df.loc[st.session_state.controls_df["Control Name"] == selected, "Framework"].iloc[0]
            st.text_area("Generated policy", generate_policy_text(selected, fw), height=180)
    else:
        st.info("Policy Generator available in Pro and Enterprise tiers.")

def render_vmaas():
    if not TIER_MODULES[st.session_state.tier]["vmaas"]:
        st.info("VMaaS available in Pro and Enterprise tiers.")
        return
    st.subheader("VMaaS")
    c1, c2 = st.columns(2)
    c1.download_button("Download automatic sample", VMAAS_TOOL_SAMPLE.read_bytes(), file_name=VMAAS_TOOL_SAMPLE.name)
    c2.download_button("Download manual sample", VMAAS_MANUAL_SAMPLE.read_bytes(), file_name=VMAAS_MANUAL_SAMPLE.name)
    uploaded = st.file_uploader("Upload VMaaS findings", type=["csv","xlsx","xls"], key="vmaas_upload")
    if uploaded is not None:
        try:
            process_vmaas(uploaded)
            st.success("VMaaS findings processed.")
        except Exception as exc:
            st.error(str(exc))
    if st.session_state.vmaas_findings is not None:
        st.dataframe(st.session_state.vmaas_findings, use_container_width=True)
    if st.session_state.vmaas_summary is not None:
        st.dataframe(st.session_state.vmaas_summary, use_container_width=True)
    if st.session_state.controls_df is not None and "Adjusted Score" in st.session_state.controls_df.columns:
        cols = [c for c in ["Framework","Control Area","Control Name","Row Score","VMaaS Penalty","Adjusted Score","VMaaS Summary"] if c in st.session_state.controls_df.columns]
        st.dataframe(st.session_state.controls_df[cols], use_container_width=True)

def main():
    init_state()
    if not st.session_state.logged_in:
        login_view()
        return
    st.title(PLATFORM_NAME)
    with st.sidebar:
        st.session_state.tier = st.selectbox("Client tier", ["core","pro","enterprise"], index=["core","pro","enterprise"].index(st.session_state.tier))
        st.download_button("Download sample intake CSV", SAMPLE_CSV.read_bytes(), file_name=SAMPLE_CSV.name)
        intake = st.file_uploader("Upload control intake", type=["csv","xlsx","xls"])
        if intake is not None:
            try:
                process_intake(intake)
                st.success("Control intake processed.")
            except Exception as exc:
                st.error(str(exc))
    if st.session_state.controls_df is None:
        st.caption("Upload a control intake file to begin.")
        return
    tabs = st.tabs(["Combined","SOC 2","HIPAA","Modules","VMaaS"])
    with tabs[0]:
        render_overview()
    with tabs[1]:
        render_framework("SOC 2", st.session_state.soc2)
    with tabs[2]:
        render_framework("HIPAA", st.session_state.hipaa)
    with tabs[3]:
        render_modules()
    with tabs[4]:
        render_vmaas()

if __name__ == "__main__":
    main()
