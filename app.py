
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st

from compliance_readiness import (
    load_any_intake,
    prepare_controls,
    calculate_framework_readiness,
    calculate_combined_readiness,
    build_output_tables,
)
from pdf_report import build_client_report

BRAND_NAME = "SentinelRiskIQ™"
COMPANY_NAME = "Sentinel Risk Compliance Group"
TAGLINE = "Where Risk Becomes Strategy"
TEMPLATE_PATH = Path(__file__).parent / "SentinelRiskIQ_ClientForm_AutoMapped.xlsx"

st.set_page_config(page_title=f"{BRAND_NAME} Upload Flow", page_icon="🛡️", layout="wide")


def metric_card(title, value, subtitle=""):
    st.markdown(
        f"""
        <div style="padding:16px;border-radius:16px;background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 2px 6px rgba(15,23,42,.06);">
          <div style="font-size:13px;color:#64748b;">{title}</div>
          <div style="font-size:28px;font-weight:700;color:#0f172a;">{value}</div>
          <div style="font-size:12px;color:#94a3b8;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    for key in ["controls_df", "soc2", "hipaa", "combined", "gap_table", "recs", "source_name"]:
        if key not in st.session_state:
            st.session_state[key] = None


def render_header():
    st.markdown(
        f"""
        <div style="padding:18px;border-radius:18px;background:linear-gradient(90deg,#0A1F44,#1E3A8A);color:white;margin-bottom:14px;">
          <div style="font-size:30px;font-weight:700;">{BRAND_NAME}</div>
          <div style="font-size:14px;">{COMPANY_NAME}</div>
          <div style="font-size:12px;color:#e9d5ff;">{TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_upload(uploaded):
    raw = load_any_intake(uploaded)
    controls_df = prepare_controls(raw)
    soc2 = calculate_framework_readiness(controls_df, "SOC 2")
    hipaa = calculate_framework_readiness(controls_df, "HIPAA")
    combined = calculate_combined_readiness(controls_df)
    _, gap_table, recs = build_output_tables(controls_df)

    st.session_state.controls_df = controls_df
    st.session_state.soc2 = soc2
    st.session_state.hipaa = hipaa
    st.session_state.combined = combined
    st.session_state.gap_table = gap_table
    st.session_state.recs = recs
    st.session_state.source_name = uploaded.name


def render_framework_view(framework_name, result):
    controls_df = st.session_state.controls_df
    gap_table = st.session_state.gap_table

    st.subheader(f"{framework_name} Executive Summary")
    st.write(result["executive_summary"])

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Overall Score", f"{result['overall_score']:.1f}", framework_name)
    with c2:
        metric_card("Readiness Band", result["readiness_band"], "Maturity signal")
    with c3:
        metric_card("High Priority", str(result["counts"].get("high_priority", 0)), "Immediate attention")

    st.subheader(f"{framework_name} Gap Register")
    gap_df = gap_table[gap_table["Framework"] == framework_name]
    st.dataframe(gap_df, use_container_width=True, height=280)

    st.subheader(f"{framework_name} Scored Controls")
    detail_df = controls_df[controls_df["Framework"] == framework_name]
    st.dataframe(detail_df, use_container_width=True, height=320)

    pdf_bytes = build_client_report(detail_df, result, framework_name)
    st.download_button(
        f"Download {framework_name} PDF report",
        data=pdf_bytes,
        file_name=f"SentinelRiskIQ_{framework_name.replace(' ', '_')}_Report.pdf",
        mime="application/pdf",
    )


def render_combined_view():
    combined = st.session_state.combined
    soc2 = st.session_state.soc2
    hipaa = st.session_state.hipaa

    st.subheader("Combined Executive Summary")
    st.write(combined["executive_summary"])

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Combined Score", f"{combined['overall_score']:.1f}", "Average")
    with c2:
        metric_card("SOC 2", f"{soc2['overall_score']:.1f}", soc2["readiness_band"])
    with c3:
        metric_card("HIPAA", f"{hipaa['overall_score']:.1f}", hipaa["readiness_band"])

    st.subheader("Cross-Framework Top Controls")
    st.dataframe(pd.DataFrame(combined["top_controls"]), use_container_width=True, height=260)


def main():
    init_state()
    render_header()

    st.info(
        "This version accepts either a direct Control Intake workbook/CSV or the client-friendly workbook. "
        "If you upload the client-friendly workbook, the app reads the Client Form sheet and automatically builds the backend Control Intake rows."
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if TEMPLATE_PATH.exists():
            st.download_button(
                "Download client-friendly workbook",
                data=TEMPLATE_PATH.read_bytes(),
                file_name="SentinelRiskIQ_ClientForm_AutoMapped.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    with c2:
        uploaded = st.file_uploader("Upload completed workbook or CSV", type=["xlsx", "xls", "csv"])
        if uploaded is not None:
            try:
                process_upload(uploaded)
                st.success("Workbook processed and scored successfully.")
            except Exception as exc:
                st.error(f"Could not process file: {exc}")

    if st.session_state.controls_df is None:
        st.caption("Upload a completed workbook to generate scoring automatically.")
        return

    if st.session_state.source_name:
        st.caption(f"Loaded source: {st.session_state.source_name}")

    view = st.radio("View", ["Combined", "SOC 2", "HIPAA"], horizontal=True)
    if view == "Combined":
        render_combined_view()
    elif view == "SOC 2":
        render_framework_view("SOC 2", st.session_state.soc2)
    else:
        render_framework_view("HIPAA", st.session_state.hipaa)


if __name__ == "__main__":
    main()
