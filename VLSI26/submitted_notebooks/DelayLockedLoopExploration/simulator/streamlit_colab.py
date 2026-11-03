"""Colab/Jupyter-friendly Streamlit frontend using streamlit-jupyter-supported APIs."""

from __future__ import annotations

from dataclasses import asdict

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simulator.gui_common import DCDLS, CONTROLLERS, PHASE_DETECTORS, run_closed_loop_simulation
else:
    from .gui_common import DCDLS, CONTROLLERS, PHASE_DETECTORS, run_closed_loop_simulation

DISPLAY_COLUMNS = ["cycle", "clk_in", "clk_out", "up", "down", "phase_error_ps"]


def _parse_float(label: str, value: str, min_value: float | None = None) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a number.") from exc

    if min_value is not None and parsed < min_value:
        raise ValueError(f"{label} must be at least {min_value}.")

    return parsed
def render_streamlit_colab_app() -> None:
    """Render the simulator with Streamlit APIs supported by streamlit-jupyter."""

    st.title("DLL Simulator Frontend")
    st.caption("Notebook-friendly Streamlit version for streamlit-jupyter")
    st.caption("clk_in -> phase detector -> controller -> DCDL, with clk_out fed back into the phase detector")
    st.caption("phase_error_ps = clk_out - clk_in")

    st.subheader("Configuration")

    st.write("Phase Detector")
    phase_detector_name = st.selectbox("", list(PHASE_DETECTORS.keys()), index=0, key="phase_detector_name")

    st.write("Controller")
    controller_name = st.selectbox("", list(CONTROLLERS.keys()), index=0, key="controller_name")

    st.write("DCDL")
    dcdl_name = st.selectbox("", list(DCDLS.keys()), index=0, key="dcdl_name")

    defaults = DCDLS[dcdl_name]

    st.write("Reference Clock Period (ps)")
    clk_period_ps_str = st.text_input(
        "",
        value=str(float(defaults["default_clk_period_ps"])),
        key="clk_period_ps",
    )

    st.write("clk_in Start (ps)")
    clk_in_start_str = st.text_input(
        "",
        value="0.0",
        key="clk_in_start",
    )

    use_auto_clk_out_start = st.checkbox("Auto clk_out Start", value=True)
    st.write("clk_out Start (ps)")
    clk_out_start_str = st.text_input(
        "",
        value=str(float(defaults["default_clk_period_ps"] - 100.0)),
        key="clk_out_start",
    )
    if use_auto_clk_out_start:
        st.caption("Auto mode is enabled: manual clk_out Start is ignored.")
    else:
        st.caption("Manual mode is enabled: the clk_out Start value above will be used.")

    cycle_options = list(range(5, 101))
    default_cycle_index = cycle_options.index(20)
    st.write("Number of Cycles")
    num_cycles = st.selectbox("", cycle_options, index=default_cycle_index, key="num_cycles")

    try:
        clk_period_ps = _parse_float("Reference Clock Period (ps)", clk_period_ps_str, min_value=1.0)
        clk_in_start = _parse_float("clk_in Start (ps)", clk_in_start_str)
        if use_auto_clk_out_start:
            clk_out_start = None
        else:
            clk_out_start = _parse_float("clk_out Start (ps)", clk_out_start_str)
    except ValueError as exc:
        st.write(f"Input error: {exc}")
        return

    trace = run_closed_loop_simulation(
        phase_detector_name=phase_detector_name,
        controller_name=controller_name,
        dcdl_name=dcdl_name,
        clk_period_ps=clk_period_ps,
        init_ctrl=0,
        num_cycles=num_cycles,
        clk_in_start=clk_in_start,
        clk_out_start=clk_out_start,
    )

    first = trace[0]
    last = trace[-1]

    st.subheader("Closed-Loop Trace")
    st.dataframe(pd.DataFrame([{key: asdict(entry)[key] for key in DISPLAY_COLUMNS} for entry in trace]))

    st.subheader("Summary")
    st.write(
        f"Start: clk_out={first.clk_out:.2f} ps, "
        f"phase_err={first.phase_error_ps:.2f} ps"
    )
    st.write(
        f"End: clk_out={last.clk_out:.2f} ps, "
        f"phase_err={last.phase_error_ps:.2f} ps"
    )


if __name__ == "__main__":
    render_streamlit_colab_app()
