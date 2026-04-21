
from pathlib import Path
import pandas as pd
import streamlit as st
from compliance_readiness import PLATFORM_NAME, COMPANY_NAME, load_any_intake, prepare_controls, calculate_framework_readiness, calculate_combined_readiness, build_output_tables
from pdf_report import build_client_report

TAGLINE = "Where Risk Becomes Strategy"
FALLBACK_USER = "admin"
FALLBACK_PASS = "admin123"
BASE_DIR = Path(__file__).parent
CLIENT_TEMPLATE = BASE_DIR / "SentinelRiskIQ_ClientForm_AutoMapped.xlsx"
SAMPLE_CSV = BASE_DIR / "sample_data" / "combined_control_intake.csv"

st.set_page_config(page_title=PLATFORM_NAME, page_icon="🛡️", layout="wide")

def get_credentials():
    try:
        return st.secrets["auth"]["username"], st.secrets["auth"]["password"]
    except Exception:
        return FALLBACK_USER, FALLBACK_PASS

def init_state():
    for key in ["logged_in","controls_df","soc2","hipaa","combined","gap_table","recs","source_name"]:
        if key not in st.session_state:
            st.session_state[key] = False if key=="logged_in" else None

def metric_card(title, value, subtitle=""):
    st.markdown(f'''
    <div style="padding:16px;border-radius:16px;background:#ffffff;border:1px solid #e2e8f0;">
      <div style="font-size:13px;color:#64748b;">{title}</div>
      <div style="font-size:28px;font-weight:700;color:#0f172a;">{value}</div>
      <div style="font-size:12px;color:#94a3b8;">{subtitle}</div>
    </div>''', unsafe_allow_html=True)

def login_view():
    st.markdown(f"## {PLATFORM_NAME}")
    st.caption(f"{COMPANY_NAME} • {TAGLINE}")
    uexp, pexp = get_credentials()
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
        if ok:
            if u == uexp and p == pexp:
                st.session_state.logged_in = True
                st.rerun()
            st.error("Invalid credentials.")
    with st.expander("Demo access"):
        st.code("admin / admin123")

def header():
    st.markdown(f'''
    <div style="padding:18px;border-radius:18px;background:linear-gradient(90deg,#0A1F44,#1E3A8A);color:white;">
      <div style="font-size:30px;font-weight:700;">{PLATFORM_NAME}</div>
      <div style="font-size:14px;">{COMPANY_NAME}</div>
      <div style="font-size:12px;color:#e9d5ff;">{TAGLINE}</div>
    </div>''', unsafe_allow_html=True)

def process(uploaded):
    raw = load_any_intake(uploaded)
    controls = prepare_controls(raw)
    soc2 = calculate_framework_readiness(controls, "SOC 2")
    hipaa = calculate_framework_readiness(controls, "HIPAA")
    combined = calculate_combined_readiness(controls)
    _, gap_table, recs = build_output_tables(controls)
    st.session_state.controls_df = controls
    st.session_state.soc2 = soc2
    st.session_state.hipaa = hipaa
    st.session_state.combined = combined
    st.session_state.gap_table = gap_table
    st.session_state.recs = recs
    st.session_state.source_name = uploaded.name

def framework_view(framework, result):
    controls = st.session_state.controls_df
    gaps = st.session_state.gap_table
    st.subheader(f"{framework} Executive Summary")
    st.write(result["executive_summary"])
    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Overall Score", f"{result['overall_score']:.1f}", framework)
    with c2: metric_card("Readiness Band", result["readiness_band"], "Maturity signal")
    with c3: metric_card("High Priority", str(result["counts"].get("high_priority",0)), "Immediate attention")
    with c4: metric_card("Critical Findings", str(result["counts"].get("critical_findings",0)), "2026 weighted items")
    if result["critical_items"]:
        st.subheader(f"{framework} Critical Findings")
        st.dataframe(pd.DataFrame(result["critical_items"]), use_container_width=True, height=220)
    left,right = st.columns([1,1])
    with left:
        if result["area_scores"]:
            st.subheader(f"{framework} Area Scores")
            adf = pd.DataFrame({"Area": list(result["area_scores"].keys()), "Score": list(result["area_scores"].values())}).sort_values("Score")
            st.bar_chart(adf.set_index("Area"))
    with right:
        st.subheader(f"{framework} Priority Actions")
        st.dataframe(pd.DataFrame(result["top_actions"]), use_container_width=True, height=260)
    st.subheader(f"{framework} Gap Register")
    st.dataframe(gaps[gaps["Framework"] == framework], use_container_width=True, height=320)
    st.subheader(f"{framework} Detailed Control Output")
    detail = controls[controls["Framework"] == framework]
    st.dataframe(detail, use_container_width=True, height=360)
    st.download_button(f"Download {framework} PDF report", data=build_client_report(detail, result, framework), file_name=f"RiskNavigator_SentinelRiskIQ_{framework.replace(' ','_')}_Report.pdf", mime="application/pdf")

def combined_view():
    combined = st.session_state.combined
    soc2 = st.session_state.soc2
    hipaa = st.session_state.hipaa
    st.subheader("Combined Executive Summary")
    st.write(combined["executive_summary"])
    c1,c2,c3 = st.columns(3)
    with c1: metric_card("Combined Score", f"{combined['overall_score']:.1f}", "Unified model")
    with c2: metric_card("SOC 2", f"{soc2['overall_score']:.1f}", soc2["readiness_band"])
    with c3: metric_card("HIPAA", f"{hipaa['overall_score']:.1f}", hipaa["readiness_band"])
    if combined["critical_findings"]:
        st.subheader("Combined Critical Findings")
        st.dataframe(pd.DataFrame(combined["critical_findings"]), use_container_width=True, height=260)
    st.subheader("Cross-Framework Top Controls")
    st.dataframe(pd.DataFrame(combined["top_controls"]), use_container_width=True, height=280)
    st.subheader("Combined Priority Actions")
    st.dataframe(pd.DataFrame(combined["top_actions"]), use_container_width=True, height=240)

def main():
    init_state()
    if not st.session_state.logged_in:
        login_view()
        return
    header()
    st.info("This fresh full package combines RiskNavigator reporting, SentinelRiskIQ branding, SOC 2 + HIPAA scoring, 2026 critical-control weighting, direct PDF exports, and client-friendly workbook upload.")
    with st.sidebar:
        st.header("Templates & Upload")
        if st.button("Log out"):
            st.session_state.logged_in = False
            st.rerun()
        if CLIENT_TEMPLATE.exists():
            st.download_button("Download client-friendly workbook", data=CLIENT_TEMPLATE.read_bytes(), file_name=CLIENT_TEMPLATE.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if SAMPLE_CSV.exists():
            st.download_button("Download sample CSV", data=SAMPLE_CSV.read_bytes(), file_name=SAMPLE_CSV.name, mime="text/csv")
        uploaded = st.file_uploader("Upload completed workbook or CSV", type=["xlsx","xls","csv"])
        if uploaded is not None:
            try:
                process(uploaded)
                st.success("File processed successfully.")
            except Exception as exc:
                st.error(f"Could not process file: {exc}")
    if st.session_state.controls_df is None:
        st.caption("Upload a client-friendly workbook, a Control Intake workbook, or the sample CSV.")
        return
    if st.session_state.source_name:
        st.caption(f"Loaded source: {st.session_state.source_name}")
    view = st.radio("View", ["Combined","SOC 2","HIPAA"], horizontal=True)
    if view == "Combined":
        combined_view()
    elif view == "SOC 2":
        framework_view("SOC 2", st.session_state.soc2)
    else:
        framework_view("HIPAA", st.session_state.hipaa)

if __name__ == "__main__":
    main()
