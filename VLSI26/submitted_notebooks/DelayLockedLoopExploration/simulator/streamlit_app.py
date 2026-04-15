"""Streamlit frontend for the DLL simulator."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator.gui_common import (
        DCDLS,
        CONTROLLERS,
        PHASE_DETECTORS,
        default_init_ctrl_for_dcdl,
        run_closed_loop_simulation,
        trace_rows,
        trace_summary_lines,
    )
else:
    from .gui_common import (
        DCDLS,
        CONTROLLERS,
        PHASE_DETECTORS,
        default_init_ctrl_for_dcdl,
        run_closed_loop_simulation,
        trace_rows,
        trace_summary_lines,
    )


st.set_page_config(page_title="DLL Simulator", layout="wide")
st.title("DLL Simulator Frontend")
st.caption("clk_in -> phase detector -> controller -> DCDL, with clk_out fed back into the phase detector")
st.caption("phase_error_ps = clk_out - clk_in")

col1, col2, col3 = st.columns(3)
with col1:
    phase_detector_name = st.selectbox("Phase Detector", list(PHASE_DETECTORS.keys()), index=0)
with col2:
    controller_name = st.selectbox("Controller", list(CONTROLLERS.keys()), index=0)
with col3:
    dcdl_name = st.selectbox("DCDL", list(DCDLS.keys()), index=0)

defaults = DCDLS[dcdl_name]

clk_period_ps = st.number_input(
    "Reference Clock Period (ps)",
    min_value=1.0,
    value=float(defaults["default_clk_period_ps"]),
    step=10.0,
)

col6, col7 = st.columns(2)
with col6:
    clk_in_start = st.number_input(
        "clk_in Start (ps)",
        value=0.0,
        step=10.0,
    )
with col7:
    use_auto_clk_out_start = st.checkbox("Auto clk_out Start", value=True)
    if use_auto_clk_out_start:
        clk_out_start = None
        st.caption("Using auto start: clk_out = clk_period - initial cell_delay")
    else:
        clk_out_start = st.number_input(
            "clk_out Start (ps)",
            value=float(clk_period_ps - 100.0),
            step=10.0,
        )

num_cycles = st.slider("Number of Cycles", min_value=5, max_value=100, value=20, step=1)

trace = run_closed_loop_simulation(
    phase_detector_name=phase_detector_name,
    controller_name=controller_name,
    dcdl_name=dcdl_name,
    clk_period_ps=clk_period_ps,
    init_ctrl=default_init_ctrl_for_dcdl(dcdl_name),
    num_cycles=num_cycles,
    clk_in_start=clk_in_start,
    clk_out_start=clk_out_start,
)

start_summary, end_summary = trace_summary_lines(trace)

st.subheader("Closed-Loop Trace")
st.dataframe(trace_rows(trace), use_container_width=True)

st.subheader("Summary")
st.write(start_summary)
st.write(end_summary)
