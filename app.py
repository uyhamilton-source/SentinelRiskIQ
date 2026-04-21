
from __future__ import annotations
import json
from typing import Dict, Tuple

import pandas as pd
import streamlit as st

from compliance_readiness import (
    calculate_combined_readiness,
    calculate_hipaa_readiness,
    calculate_soc2_readiness,
    load_control_intake,
    prepare_controls,
)
from pdf_report import build_pdf

st.set_page_config(page_title="RiskNavigator Compliance Dashboard", page_icon="🛡️", layout="wide")

FALLBACK_USER = "admin"
FALLBACK_PASS = "admin123"

def get_credentials() -> Tuple[str, str]:
    try:
        return st.secrets["auth"]["username"], st.secrets["auth"]["password"]
    except Exception:
        return FALLBACK_USER, FALLBACK_PASS

def init_state() -> None:
    defaults = {"logged_in": False, "controls_df": None, "views": {}, "source_name": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def color_for_band(band: str) -> str:
    return {"Ready": "#15803d", "Near Ready": "#ca8a04", "Developing": "#ea580c", "Not Ready": "#b91c1c"}.get(band, "#334155")

def metric_card(title: str, value: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div style="padding:16px;border-radius:16px;background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(15,23,42,.06);">
        <div style="font-size:13px;color:#64748b;">{title}</div>
        <div style="font-size:28px;font-weight:700;margin-top:4px;color:#0f172a;">{value}</div>
        <div style="font-size:12px;color:#94a3b8;margin-top:6px;">{subtitle}</div></div>""",
        unsafe_allow_html=True,
    )

def login_view() -> None:
    st.title("RiskNavigator™ Compliance Dashboard")
    st.caption("Upload a combined SOC 2 + HIPAA intake file to score readiness, identify blockers, and generate next actions.")
    expected_user, expected_pass = get_credentials()
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if username == expected_user and password == expected_pass:
                st.session_state.logged_in = True
                st.success("Signed in.")
                st.rerun()
            else:
                st.error("Invalid credentials.")
    with st.expander("Demo access"):
        st.code(f"{FALLBACK_USER} / {FALLBACK_PASS}")

def process_upload(uploaded) -> None:
    raw_df = load_control_intake(uploaded)
    controls_df = prepare_controls(raw_df)
    st.session_state.controls_df = controls_df
    st.session_state.views = {
        "SOC 2": calculate_soc2_readiness(controls_df),
        "HIPAA": calculate_hipaa_readiness(controls_df),
        "Combined": calculate_combined_readiness(controls_df),
    }
    st.session_state.source_name = uploaded.name

def render_readiness_header(readiness: Dict) -> None:
    cols = st.columns(4)
    with cols[0]:
        metric_card("Overall Score", f"{readiness['overall_score']:.1f}", "Weighted readiness estimate")
    with cols[1]:
        metric_card("Readiness Band", readiness["readiness_band"], "Client-friendly maturity label")
    with cols[2]:
        metric_card("In-Scope Controls", str(readiness["counts"]["in_scope"]), "Controls marked in scope")
    with cols[3]:
        metric_card("Priority Gaps", str(readiness["counts"]["missing"]), "Controls scoring below 50")
    st.markdown(
        f"""<div style="margin-top:8px;">
        <div style="font-size:13px;color:#64748b;margin-bottom:6px;">Readiness meter</div>
        <div style="background:#e2e8f0;border-radius:999px;height:18px;overflow:hidden;">
        <div style="width:{min(readiness['overall_score'], 100)}%;background:{color_for_band(readiness['readiness_band'])};height:18px;"></div>
        </div></div>""",
        unsafe_allow_html=True,
    )

def render_framework_comparison(views: Dict[str, Dict]) -> None:
    st.subheader("Overview")
    c1, c2, c3 = st.columns(3)
    for col, key in zip([c1, c2, c3], ["SOC 2", "HIPAA", "Combined"]):
        with col:
            metric_card(key, f"{views[key]['overall_score']:.1f}", views[key]["readiness_band"])

def render_executive_summary(readiness: Dict) -> None:
    st.subheader("Executive Summary")
    st.text_area("Generated summary", value=readiness.get("executive_summary",""), height=260)

def render_area_scores(readiness: Dict) -> None:
    st.subheader("Area Scores")
    area_df = pd.DataFrame([{"Area": a, "Score": s} for a, s in readiness["area_scores"].items()]).sort_values("Score", ascending=True)
    if area_df.empty:
        st.info("No area scores yet.")
    else:
        st.bar_chart(area_df.set_index("Area"))

def render_top_actions(readiness: Dict) -> None:
    st.subheader("Top Recommended Next Actions")
    recs = readiness.get("recommendations", [])[:3]
    if not recs:
        st.info("No recommendations available.")
    for idx, rec in enumerate(recs, start=1):
        st.markdown(
            f"""<div style="padding:14px;border-radius:14px;background:#fff7ed;border:1px solid #fed7aa;margin-bottom:10px;">
            <div style="font-size:12px;color:#9a3412;">Decision {idx}</div>
            <div style="font-size:18px;font-weight:700;color:#7c2d12;">{rec['area']}</div>
            <div style="font-size:13px;margin-top:4px;">Current score: <b>{rec['score']:.1f}</b> | Priority: <b>{rec['priority']}</b></div>
            <div style="font-size:13px;margin-top:6px;color:#7c2d12;">{rec['recommendation']}</div></div>""",
            unsafe_allow_html=True,
        )

def render_blockers(readiness: Dict) -> None:
    st.subheader("Top Blockers")
    blockers_df = pd.DataFrame(readiness.get("top_gaps", []))
    if blockers_df.empty:
        st.info("No blockers identified.")
    else:
        st.dataframe(blockers_df, use_container_width=True, height=260)

def render_gap_table(readiness: Dict) -> None:
    st.subheader("Design vs Implementation Gaps")
    gaps = readiness.get("gaps", [])
    if not gaps:
        st.info("No design or implementation gaps were identified.")
        return
    df = pd.DataFrame(gaps)[["control_id","framework","control_area","control","design_gap","implementation_gap","citation","priority"]]
    df.columns = ["Control ID","Framework","Control Area","Control","Design Gap","Implementation Gap","Citation","Priority"]
    st.dataframe(df, use_container_width=True, height=320)

def render_framework_mapping(readiness: Dict) -> None:
    label = "Framework Mapping"
    st.subheader(label)
    gaps = readiness.get("gaps", [])
    if not gaps:
        st.info("No framework mapping available.")
        return
    mapping_df = pd.DataFrame(gaps)[["framework","control","design_gap","citation","priority"]]
    mapping_df.columns = ["Framework","Design Gap","Description","Citation","Priority"]
    st.dataframe(mapping_df, use_container_width=True, height=260)

def render_remediation_plan(readiness: Dict) -> None:
    st.subheader("Prioritized Remediation Plan")
    high_priority = [g for g in readiness.get("gaps", []) if g.get("priority") == "High"]
    medium_priority = [g for g in readiness.get("gaps", []) if g.get("priority") == "Medium"]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**0–30 Days**")
        if high_priority:
            for item in high_priority[:3]:
                st.markdown(f"- Establish and document **{item['control']}** requirements")
        else:
            st.markdown("- No immediate high-priority actions identified")
    with col2:
        st.markdown("**30–60 Days**")
        if medium_priority:
            for item in medium_priority[:3]:
                st.markdown(f"- Standardize execution and evidence for **{item['control']}**")
        else:
            st.markdown("- Validate evidence and testing for in-scope controls")
    with col3:
        st.markdown("**60–90 Days**")
        st.markdown("- Confirm operating effectiveness through testing")
        st.markdown("- Prepare walkthrough evidence and support materials")

def render_controls_detail(controls_df: pd.DataFrame, selected_view: str) -> None:
    st.subheader("Scored Control Detail")
    view_df = controls_df.copy()
    if selected_view != "Combined":
        view_df = view_df[view_df["framework"] == selected_view]
    display_cols = ["framework","control_id","control_area","control_name","in_scope","status","evidence_available","owner_assigned","policy_exists","procedure_exists","tested_recently","row_score","priority_hint"]
    st.dataframe(view_df[display_cols], use_container_width=True, height=320)

def render_downloads(readiness: Dict, controls_df: pd.DataFrame, selected_view: str) -> None:
    st.subheader("Downloads")
    view_df = controls_df if selected_view == "Combined" else controls_df[controls_df["framework"] == selected_view]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Download scored controls CSV", data=view_df.to_csv(index=False).encode("utf-8"), file_name=f"{selected_view.lower().replace(' ','_')}_scored_controls.csv", mime="text/csv")
    with col2:
        st.download_button("Download readiness JSON", data=json.dumps(readiness, indent=2), file_name=f"{selected_view.lower().replace(' ','_')}_readiness_summary.json", mime="application/json")
    with col3:
        st.download_button("Download executive PDF", data=build_pdf(readiness), file_name=f"{selected_view.lower().replace(' ','_')}_executive_report.pdf", mime="application/pdf")

def render_dashboard() -> None:
    st.title("RiskNavigator™ Compliance Dashboard")
    st.caption("Client-ready SOC 2 + HIPAA scoring, blockers, and recommended next actions.")
    with st.sidebar:
        st.header("Controls")
        if st.button("Log out"):
            st.session_state.logged_in = False
            st.session_state.controls_df = None
            st.session_state.views = {}
            st.session_state.source_name = None
            st.rerun()
        uploaded = st.file_uploader("Upload Control Intake (.xlsx or .csv)", type=["xlsx","xls","csv"], help="Upload the combined workbook template or sample CSV.")
        if uploaded is not None:
            try:
                process_upload(uploaded)
                st.success("File processed successfully.")
            except Exception as exc:
                st.error(f"Could not process file: {exc}")
    if not st.session_state.views:
        st.info("Upload a combined SOC 2 + HIPAA intake workbook or CSV to populate the dashboard.")
        return
    if st.session_state.source_name:
        st.caption(f"Loaded source: {st.session_state.source_name}")
    render_framework_comparison(st.session_state.views)
    selected_view = st.radio("View", ["SOC 2", "HIPAA", "Combined"], horizontal=True)
    readiness = st.session_state.views[selected_view]
    render_readiness_header(readiness)
    tabs = st.tabs(["Executive Summary", "Area Scores", "Top Actions", "Top Blockers", "Gap Analysis", "Framework Mapping", "Remediation", "Control Detail", "Downloads"])
    with tabs[0]:
        render_executive_summary(readiness)
    with tabs[1]:
        render_area_scores(readiness)
    with tabs[2]:
        render_top_actions(readiness)
    with tabs[3]:
        render_blockers(readiness)
    with tabs[4]:
        render_gap_table(readiness)
    with tabs[5]:
        render_framework_mapping(readiness)
    with tabs[6]:
        render_remediation_plan(readiness)
    with tabs[7]:
        render_controls_detail(st.session_state.controls_df, selected_view)
    with tabs[8]:
        render_downloads(readiness, st.session_state.controls_df, selected_view)

def main():
    init_state()
    if not st.session_state.logged_in:
        login_view()
    else:
        render_dashboard()

if __name__ == "__main__":
    main()
