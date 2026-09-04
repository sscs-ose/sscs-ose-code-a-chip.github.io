"""
DLL Locking Visualization

Usage in Jupyter Notebook:
    from bokeh.io import output_notebook
    output_notebook()

    %run plot_dll_locking.py

Or import and call directly:
    from plot_dll_locking import load_vcd_data, plot_static, plot_animated
    data = load_vcd_data("zdb.vcd")
    plot_static(data)
    plot_animated(data)
"""

import sys

sys.path.append("/content/CaC_Spring26/scripts")

import numpy as np
from vcdvcd import VCDVCD
from plot_framework import iplot, ioverlay, istack, ianimate, ianimate_stack

VCD_FILE = "zdb.vcd"
CLK_PERIOD = 4.0   # ns
DELAY_PS = 700     # ps
LOCK_TOL_FRAC = 0.1  # lock when |phase_error| < CLK_PERIOD * this


def _get_signal(vcd, name):
    """Find a signal by partial name match in the VCD hierarchy."""
    for k in vcd.signals:
        if name in k:
            return vcd[k].tv
    raise ValueError(f"Signal '{name}' not found in VCD. "
                     f"Available: {list(vcd.signals)[:10]}...")


def load_vcd_data(vcd_file=VCD_FILE, clk_period=CLK_PERIOD, delay_ps=DELAY_PS):
    """
    Parse a DLL VCD file and return a dict of numpy arrays ready
    for the plotting framework.

    Returns
    -------
    dict with keys:
        clk_in_edges  : 1-D array, rising edge times of clk_in (ns)
        clk_out_edges : 1-D array, rising edge times of clk_out (ns)
        phase_t       : 1-D array, phase error sample times (ns)
        phase_v       : 1-D array, phase error values (ns)
        tol           : float, lock tolerance (ns)
        clk_period    : float (ns)
        delay_ps      : int (ps)
    """
    vcd = VCDVCD(vcd_file, signals=[])

    clk_in_tv  = _get_signal(vcd, "clk_in")
    clk_out_tv = _get_signal(vcd, "clk_out")
    phase_tv   = _get_signal(vcd, "phase_error")

    # Rising edges only, convert ps to ns
    clk_in_edges  = np.array([t for t, v in clk_in_tv  if v == '1']) / 1000.0
    clk_out_edges = np.array([t for t, v in clk_out_tv if v == '1']) / 1000.0

    phase_t = np.array([t for t, _ in phase_tv]) / 1000.0
    phase_v = np.array([float(v) for _, v in phase_tv])

    tol = clk_period * LOCK_TOL_FRAC

    return dict(
        clk_in_edges=clk_in_edges,
        clk_out_edges=clk_out_edges,
        phase_t=phase_t,
        phase_v=phase_v,
        tol=tol,
        clk_period=clk_period,
        delay_ps=delay_ps,
    )


def _make_tolerance_traces(phase_t, tol):
    """
    Build constant-value traces for the lock tolerance band and
    the zero reference, matching the phase_t x-axis.

    Returns a dict suitable for merging into an ioverlay / istack layer.
    """
    zeros   = np.zeros_like(phase_t)
    upper   = np.full_like(phase_t, tol)
    lower   = np.full_like(phase_t, -tol)

    return {
        "zero ref":       (phase_t, zeros),
        f"+tol ({tol:.2f} ns)": (phase_t, upper),
        f"−tol ({tol:.2f} ns)": (phase_t, lower),
    }


def plot_static(data, width=900, layer_height=220):
    """
    Stacked two-panel plot (replaces the matplotlib static figure):
        Top:    clock edge alignment (scatter markers)
        Bottom: phase error convergence with tolerance band

    Uses istack for linked x-axis pan/zoom.
    """
    clk_in_edges  = data["clk_in_edges"]
    clk_out_edges = data["clk_out_edges"]
    phase_t       = data["phase_t"]
    phase_v       = data["phase_v"]
    tol           = data["tol"]

    # Layer 0 — Clock edges (y=0 for clk_in, y=1 for clk_out)
    clock_layer = {
        "clk_in":  (clk_in_edges,  np.zeros_like(clk_in_edges)),
        "clk_out": (clk_out_edges, np.ones_like(clk_out_edges)),
    }

    # Layer 1 — Phase error + tolerance band
    phase_layer = {"phase_error": (phase_t, phase_v)}
    phase_layer.update(_make_tolerance_traces(phase_t, tol))

    istack(
        [clock_layer, phase_layer],
        title="DLL Locking — Clock Alignment & Phase Error",
        xlabel="Time (ns)",
        ylabels=["Clock Edge", "Phase Error (ns)"],
        kind="scatter",         # scatter works well for edge markers
        width=width,
        layer_height=layer_height,
    )


def plot_phase_overlay(data, width=800, height=450):
    """
    Single-panel overlay of phase error with tolerance band.
    Traces are toggleable via legend click.

    Uses ioverlay.
    """
    phase_t = data["phase_t"]
    phase_v = data["phase_v"]
    tol     = data["tol"]

    traces = {"phase_error": (phase_t, phase_v)}
    traces.update(_make_tolerance_traces(phase_t, tol))

    ioverlay(
        traces,
        title="Phase Error Convergence",
        xlabel="Time (ns)",
        ylabel="Phase Error (ns)",
        kind="line",
        width=width,
        height=height,
    )


def plot_animated(data, width=900, layer_height=200,
                  interval_ms=30, step_size=5):
    """
    Animated stacked view (replaces the imageio GIF):
        Top:    phase error drawn progressively
        Bottom: (optional) clock edges drawn progressively

    Uses ianimate_stack — interactive play/pause + scrub slider,
    no temporary PNG files needed.
    """
    phase_t = data["phase_t"]
    phase_v = data["phase_v"]
    tol     = data["tol"]

    # Build tolerance traces (these also animate progressively,
    # which gives a nice "band filling in" effect)
    tol_traces = _make_tolerance_traces(phase_t, tol)

    phase_layer = {"phase_error": (phase_t, phase_v)}
    phase_layer.update(tol_traces)

    ianimate_stack(
        [phase_layer],
        title="DLL Locking Process (animated)",
        xlabel="Time (ns)",
        ylabels=["Phase Error (ns)"],
        kind="line",
        width=width,
        layer_height=layer_height * 2,  # single layer, give it more room
        interval_ms=interval_ms,
        step_size=step_size,
    )


# Doesn't quite work
# def plot_animated_full(data, width=900, layer_height=200,
#                        interval_ms=30, step_size=5):
#     """
#     Full animated stacked view with both clock edges and phase error
#     drawn progressively in sync.

#     Uses ianimate_stack with two layers.
#     """
#     clk_in_edges  = data["clk_in_edges"]
#     clk_out_edges = data["clk_out_edges"]
#     phase_t       = data["phase_t"]
#     phase_v       = data["phase_v"]
#     tol           = data["tol"]

#     clock_layer = {
#         "clk_in":  (clk_in_edges,  np.zeros_like(clk_in_edges)),
#         "clk_out": (clk_out_edges, np.ones_like(clk_out_edges)),
#     }

#     phase_layer = {"phase_error": (phase_t, phase_v)}
#     phase_layer.update(_make_tolerance_traces(phase_t, tol))

#     ianimate_stack(
#         [clock_layer, phase_layer],
#         title="DLL Locking Process (animated)",
#         xlabel="Time (ns)",
#         ylabels=["Clock Edge", "Phase Error (ns)"],
#         kind="line",
#         width=width,
#         layer_height=layer_height,
#         interval_ms=interval_ms,
#         step_size=step_size,
#     )


def print_lock_summary(data):
    """Print the same textual summary as the original script."""
    phase_v = data["phase_v"]
    tol     = data["tol"]

    final_err = phase_v[-1]

    print("=" * 44)
    print("  FINAL RESULT")
    print("=" * 44)
    print(f"  Final phase error = {final_err:.4f} ns")
    print(f"  Lock tolerance    = ±{tol:.4f} ns")

    if abs(final_err) < tol:
        print("  STATUS: LOCKED")
    else:
        print("  STATUS: DID NOT FULLY LOCK")
    print("=" * 44)


# ===================== MAIN =====================

if __name__ == "__main__":
    data = load_vcd_data()

    print_lock_summary(data)

    plot_static(data)
    plot_phase_overlay(data)
    plot_animated(data, step_size=1)