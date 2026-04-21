
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from compliance_readiness import (
    load_control_intake,
    prepare_controls,
    calculate_framework_readiness,
    calculate_combined_readiness,
    build_output_tables,
)

BRAND_NAME = "SentinelRiskIQ™"
COMPANY_NAME = "Sentinel Risk Compliance Group"
TAGLINE = "Where Risk Becomes Strategy"

st.set_page_config(
    page_title=f"{BRAND_NAME} Compliance Dashboard",
    page_icon="🛡️",
    layout="wide",
)

FALLBACK_USER = "admin"
FALLBACK_PASS = "admin123"


def get_credentials():
    try:
        return st.secrets["auth"]["username"], st.secrets["auth"]["password"]
    except Exception:
        return FALLBACK_USER, FALLBACK_PASS


def init_state():
    defaults = {
        "logged_in": False,
        "controls_df": None,
        "soc2": None,
        "hipaa": None,
        "combined": None,
        "design_impl": None,
        "recs": None,
        "source_name": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def metric_card(title, value, subtitle=""):
    st.markdown(
        f"""
        <div style="padding:16px;border-radius:16px;background:#ffffff;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(15,23,42,.06);">
          <div style="font-size:13px;color:#64748b;">{title}</div>
          <div style="font-size:28px;font-weight:700;color:#0f172a;">{value}</div>
          <div style="font-size:12px;color:#94a3b8;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def login_view():
    st.markdown(f"## {BRAND_NAME} Platform")
    st.caption(f"{COMPANY_NAME} • {TAGLINE}")
    expected_user, expected_pass = get_credentials()

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if username == expected_user and password == expected_pass:
                st.session_state.logged_in = True
                st.rerun()
            st.error("Invalid credentials.")

    with st.expander("Demo access"):
        st.code(f"{FALLBACK_USER} / {FALLBACK_PASS}")


def render_brand_header():
    st.markdown(
        f"""
        <div style="padding:16px;border-radius:16px;background:linear-gradient(90deg,#0A1F44,#1E3A8A);color:white;margin-bottom:14px;">
          <div style="font-size:28px;font-weight:700;">{BRAND_NAME}</div>
          <div style="font-size:14px;">{COMPANY_NAME}</div>
          <div style="font-size:12px;color:#d8b4fe;">{TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scoring_explainer():
    st.info(
        "How the intake drives the output: Status sets the base score. Policy Exists drives Design Gap detection. "
        "Procedure Exists and Owner Assigned drive Implementation Gap detection. Evidence Available and Tested Recently "
        "drive Operating Effectiveness and priority."
    )


def render_summary_cards(result, subtitle):
    cols = st.columns(4)
    with cols[0]:
        metric_card("Overall Score", f"{result['overall_score']:.1f}", subtitle)
    with cols[1]:
        metric_card("Readiness Band", result["readiness_band"], "Client-friendly maturity label")
    with cols[2]:
        metric_card("High Priority", str(result["counts"].get("high_priority", 0)), "Immediate attention")
    with cols[3]:
        metric_card("Total Controls", str(result["counts"].get("controls", 0)), "Selected view")


def render_framework_view(name, result, design_impl, controls_df):
    st.subheader(f"{name} Executive Summary")
    st.write(result["executive_summary"])

    render_summary_cards(result, f"{name} readiness estimate")

    left, right = st.columns([1, 1])
    with left:
        st.subheader(f"{name} Area Scores")
        if result["area_scores"]:
            area_df = pd.DataFrame(
                {"Area": list(result["area_scores"].keys()), "Score": list(result["area_scores"].values())}
            ).sort_values("Score", ascending=True)
            st.bar_chart(area_df.set_index("Area"))
        else:
            st.info("No area scores available for this view.")

    with right:
        st.subheader(f"{name} Top Actions")
        for action in result["top_actions"][:4]:
            st.markdown(
                f"""
                <div style="padding:12px;border-radius:12px;background:#fff7ed;border:1px solid #fed7aa;margin-bottom:10px;">
                  <div style="font-size:12px;color:#9a3412;">Priority: {action['Priority']}</div>
                  <div style="font-size:17px;font-weight:700;color:#7c2d12;">{action['Control Name']}</div>
                  <div style="font-size:13px;color:#7c2d12;">{action['Recommended Actions']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.subheader(f"{name} Gap Table")
    gap_df = design_impl[design_impl["Framework"] == name][
        ["Control ID", "Control Name", "Gap Type", "Design Gap", "Implementation Gap", "Priority", "Framework Citation"]
    ]
    st.dataframe(gap_df, use_container_width=True, height=280)

    st.subheader(f"{name} Scored Controls")
    view_controls = controls_df[controls_df["Framework"] == name][
        [
            "Control ID",
            "Control Area",
            "Control Name",
            "Status",
            "Policy Exists",
            "Procedure Exists",
            "Owner Assigned",
            "Evidence Available",
            "Tested Recently",
            "Row Score",
            "Gap Type",
            "Priority",
            "Framework Citation",
            "Recommended Actions",
        ]
    ]
    st.dataframe(view_controls, use_container_width=True, height=340)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            f"Download {name} scored controls CSV",
            data=view_controls.to_csv(index=False).encode("utf-8"),
            file_name=f"SentinelRiskIQ_{name.replace(' ', '_')}_Scored_Controls.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            f"Download {name} summary JSON",
            data=json.dumps(result, indent=2),
            file_name=f"SentinelRiskIQ_{name.replace(' ', '_')}_Summary.json",
            mime="application/json",
        )


def render_combined_view(combined, soc2, hipaa):
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
    st.dataframe(pd.DataFrame(combined["top_controls"]), use_container_width=True, height=280)

    st.subheader("Combined Priority Actions")
    st.dataframe(pd.DataFrame(combined["top_actions"]), use_container_width=True, height=220)


def main():
    init_state()
    if not st.session_state.logged_in:
        login_view()
        return

    render_brand_header()
    render_scoring_explainer()

    with st.sidebar:
        st.header("Controls")
        if st.button("Log out"):
            st.session_state.logged_in = False
            st.rerun()

        uploaded = st.file_uploader("Upload intake workbook or CSV", type=["xlsx", "xls", "csv"])
        if uploaded is not None:
            raw = load_control_intake(uploaded)
            controls_df = prepare_controls(raw)
            soc2 = calculate_framework_readiness(controls_df, "SOC 2")
            hipaa = calculate_framework_readiness(controls_df, "HIPAA")
            combined = calculate_combined_readiness(controls_df)
            _, design_impl, recs = build_output_tables(controls_df)

            st.session_state.controls_df = controls_df
            st.session_state.soc2 = soc2
            st.session_state.hipaa = hipaa
            st.session_state.combined = combined
            st.session_state.design_impl = design_impl
            st.session_state.recs = recs
            st.session_state.source_name = uploaded.name
            st.success("File processed successfully.")

    if st.session_state.controls_df is None:
        st.info("Upload your intake file to generate output that now matches the intake columns exactly.")
        return

    if st.session_state.source_name:
        st.caption(f"Loaded source: {st.session_state.source_name}")

    view = st.radio("View", ["Combined", "SOC 2", "HIPAA"], horizontal=True)

    if view == "Combined":
        render_combined_view(st.session_state.combined, st.session_state.soc2, st.session_state.hipaa)
    elif view == "SOC 2":
        render_framework_view("SOC 2", st.session_state.soc2, st.session_state.design_impl, st.session_state.controls_df)
    else:
        render_framework_view("HIPAA", st.session_state.hipaa, st.session_state.design_impl, st.session_state.controls_df)


if __name__ == "__main__":
    main()
