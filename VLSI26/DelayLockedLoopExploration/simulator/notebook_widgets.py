"""Notebook-native ipywidgets frontend for the DLL simulator."""

from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
import sys
from pathlib import Path

from IPython.display import HTML, Image, display
import matplotlib.pyplot as plt

try:
    import ipywidgets as widgets
except ImportError:  # pragma: no cover - optional dependency in notebooks
    widgets = None

MODULE_ROOT = Path(__file__).resolve().parents[1]

if __package__ in (None, ""):
    sys.path.insert(0, str(MODULE_ROOT))
    from simulator.gui_common import (
        DCDLS,
        CONTROLLERS,
        PHASE_DETECTORS,
        default_init_ctrl_for_dcdl,
        run_closed_loop_simulation,
        trace_summary_lines,
    )
else:
    from .gui_common import (
        DCDLS,
        CONTROLLERS,
        PHASE_DETECTORS,
        default_init_ctrl_for_dcdl,
        run_closed_loop_simulation,
        trace_summary_lines,
    )


def _styled_caption(text: str):
    if widgets is None:
        raise ImportError("ipywidgets is required to render the notebook GUI.")
    return widgets.HTML(
        value=(
            "<div style='color:#666; font-size:0.95em; margin:2px 0 10px 0;'>"
            f"{text}"
            "</div>"
        )
    )


def _render_clk_plot(trace) -> None:
    cycles = [entry.cycle for entry in trace]
    clk_in_values = [entry.clk_in for entry in trace]
    clk_out_values = [entry.clk_out for entry in trace]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(cycles, clk_in_values, marker="o", linewidth=2, label="clk_in")
    ax.plot(cycles, clk_out_values, marker="o", linewidth=2, label="clk_out")
    ax.set_title("clk_in vs clk_out")
    ax.set_xlabel("Cycle")
    ax.set_ylabel("Edge Time (ps)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    display(Image(data=buffer.getvalue()))
    plt.close(fig)


def _render_phase_error_plot(trace) -> None:
    cycles = [entry.cycle for entry in trace]
    phase_error_values = [entry.phase_error_ps for entry in trace]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(cycles, phase_error_values, marker="o", linewidth=2, color="#d62728")
    ax.axhline(0.0, color="black", linewidth=1, linestyle="--", alpha=0.7)
    ax.set_title("phase_error_ps over time")
    ax.set_xlabel("Cycle")
    ax.set_ylabel("phase_error_ps")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    display(Image(data=buffer.getvalue()))
    plt.close(fig)


def display_dll_simulator():
    """Render the simulator controls and outputs inside a notebook cell."""
    if widgets is None:
        raise ImportError(
            "ipywidgets is not installed. Install it with `pip install ipywidgets` "
            "in the notebook environment, then rerun this cell."
        )

    phase_detector = widgets.Dropdown(
        options=list(PHASE_DETECTORS.keys()),
        value="FF1",
        description="Phase Detector",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%"),
    )
    controller = widgets.Dropdown(
        options=list(CONTROLLERS.keys()),
        value="Saturate",
        description="Controller",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%"),
    )
    dcdl = widgets.Dropdown(
        options=list(DCDLS.keys()),
        value="NandDCDL",
        description="DCDL",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%"),
    )

    defaults = DCDLS[dcdl.value]

    clk_period_ps = widgets.FloatText(
        value=float(defaults["default_clk_period_ps"]),
        step=10.0,
        description="Reference Clock Period (ps)",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%"),
    )
    clk_in_start = widgets.FloatText(
        value=0.0,
        step=10.0,
        description="clk_in Start (ps)",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%"),
    )
    auto_clk_out_start = widgets.Checkbox(
        value=True,
        description="Auto clk_out Start",
        indent=False,
        layout=widgets.Layout(width="100%"),
    )
    auto_caption = _styled_caption(
        "Using auto start: clk_out = clk_period - initial cell_delay"
    )
    clk_out_start = widgets.FloatText(
        value=float(clk_period_ps.value - 100.0),
        step=10.0,
        description="clk_out Start (ps)",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%", display="none"),
    )
    num_cycles = widgets.IntSlider(
        value=20,
        min=5,
        max=100,
        step=1,
        description="Number of Cycles",
        style={"description_width": "initial"},
        layout=widgets.Layout(width="100%"),
    )
    run_button = widgets.Button(
        description="Run Simulation",
        button_style="primary",
        layout=widgets.Layout(width="200px"),
    )

    results_output = widgets.Output()

    def sync_dcdl_defaults(*_args) -> None:
        selected = DCDLS[dcdl.value]
        clk_period_ps.value = float(selected["default_clk_period_ps"])
        if auto_clk_out_start.value:
            clk_out_start.value = float(clk_period_ps.value - 100.0)

    def sync_clk_out_visibility(*_args) -> None:
        if auto_clk_out_start.value:
            auto_caption.layout.display = ""
            clk_out_start.layout.display = "none"
        else:
            auto_caption.layout.display = "none"
            clk_out_start.layout.display = ""

    def sync_clk_out_default(*_args) -> None:
        if auto_clk_out_start.value:
            clk_out_start.value = float(clk_period_ps.value - 100.0)

    def render(*_args) -> None:
        trace = run_closed_loop_simulation(
            phase_detector_name=phase_detector.value,
            controller_name=controller.value,
            dcdl_name=dcdl.value,
            clk_period_ps=float(clk_period_ps.value),
            init_ctrl=default_init_ctrl_for_dcdl(dcdl.value),
            num_cycles=int(num_cycles.value),
            clk_in_start=float(clk_in_start.value),
            clk_out_start=None if auto_clk_out_start.value else float(clk_out_start.value),
        )
        start_summary, end_summary = trace_summary_lines(trace)

        with results_output:
            results_output.clear_output(wait=True)
            display(HTML("<h3>Phase Error Plot</h3>"))
            display(HTML("<div style='font-size:1.05rem; margin-bottom:8px;'>phase_error_ps = clk_out - clk_in</div>"))
            _render_phase_error_plot(trace)
            display(HTML("<h3>Clock Plot</h3>"))
            _render_clk_plot(trace)
            display(HTML("<h3>Summary</h3>"))
            display(HTML(f"<div style='font-size:1.15rem; margin-bottom:6px;'>{start_summary}</div>"))
            display(HTML(f"<div style='font-size:1.15rem;'>{end_summary}</div>"))

    dcdl.observe(sync_dcdl_defaults, names="value")
    auto_clk_out_start.observe(sync_clk_out_visibility, names="value")
    clk_period_ps.observe(sync_clk_out_default, names="value")
    run_button.on_click(render)

    sync_clk_out_visibility()

    ui = widgets.VBox(
        [
            widgets.HTML("<h2>DLL Simulator Frontend</h2>"),
            widgets.HBox(
                [phase_detector, controller, dcdl],
                layout=widgets.Layout(width="100%"),
            ),
            widgets.HBox(
                [clk_period_ps],
                layout=widgets.Layout(width="100%"),
            ),
            widgets.HBox(
                [
                    clk_in_start,
                    widgets.VBox([auto_clk_out_start, auto_caption, clk_out_start]),
                ],
                layout=widgets.Layout(width="100%"),
            ),
            num_cycles,
            run_button,
            results_output,
        ]
    )
    return ui
