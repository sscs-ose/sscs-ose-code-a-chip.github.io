"""
NeuroSAR plotting — Plotly-based figures for waveforms, FoM surfaces,
training curves, and comparison plots.

All functions return Plotly Figure objects that render beautifully
in Jupyter notebooks and can be exported to PNG / HTML / SVG.
"""

import os
from typing import Dict, List, Optional

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import FIGURES
from src.utils import ensure_dir


# =========================================================================
# Colour palette (ISSCC / VLSI style)
# =========================================================================
COLORS = {
    "primary":   "#1f77b4",
    "secondary": "#ff7f0e",
    "tertiary":  "#2ca02c",
    "accent":    "#d62728",
    "muted":     "#7f7f7f",
    "dark":      "#17202a",
}

TEMPLATE = "plotly_white"


# =========================================================================
# Waveform plots
# =========================================================================

def plot_dac_waveform(
    vdac: np.ndarray,
    n_bits: int = 10,
    title: str = "DAC Trial Voltages",
) -> go.Figure:
    """
    Plot DAC node voltage across bit trials.
    vdac: (n_bits+1,) or (n_bits,)
    """
    fig = go.Figure()
    x = list(range(len(vdac)))
    fig.add_trace(go.Scatter(
        x=x, y=vdac,
        mode="lines+markers",
        name="V_DAC",
        line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=8),
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Bit Trial",
        yaxis_title="Voltage (V)",
        template=TEMPLATE,
        width=700, height=400,
    )
    return fig


def plot_comparator_regen(
    vcomp: np.ndarray,
    t_local: Optional[np.ndarray] = None,
    bit_indices: Optional[List[int]] = None,
    title: str = "Comparator Regeneration",
) -> go.Figure:
    """
    Plot comparator output waveform(s).
    vcomp: (n_bits, T) or (T,)
    """
    fig = go.Figure()
    if vcomp.ndim == 1:
        vcomp = vcomp[np.newaxis, :]

    n_bits = vcomp.shape[0]
    T = vcomp.shape[1]
    if t_local is None:
        t_local = np.linspace(0, 1, T)

    bits_to_plot = bit_indices or list(range(min(n_bits, 5)))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
              "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

    for idx, k in enumerate(bits_to_plot):
        fig.add_trace(go.Scatter(
            x=t_local, y=vcomp[k],
            mode="lines",
            name=f"Bit {k}",
            line=dict(color=colors[idx % len(colors)], width=2),
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Normalised Time",
        yaxis_title="V_comp (V)",
        template=TEMPLATE,
        width=700, height=400,
    )
    return fig


def plot_differential_waveform(
    vdiff: np.ndarray,
    t_local: Optional[np.ndarray] = None,
    bit_indices: Optional[List[int]] = None,
    title: str = "Differential Voltage (DAC Settling)",
) -> go.Figure:
    """Plot vdiff(t) for selected bit cycles."""
    fig = go.Figure()
    if vdiff.ndim == 1:
        vdiff = vdiff[np.newaxis, :]

    T = vdiff.shape[1]
    if t_local is None:
        t_local = np.linspace(0, 1, T)

    bits_to_plot = bit_indices or list(range(min(vdiff.shape[0], 5)))
    for k in bits_to_plot:
        fig.add_trace(go.Scatter(
            x=t_local, y=vdiff[k],
            mode="lines",
            name=f"Bit {k}",
            line=dict(width=2),
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Normalised Time",
        yaxis_title="V_diff (V)",
        template=TEMPLATE,
        width=700, height=400,
    )
    return fig


# =========================================================================
# Multi-panel waveform summary
# =========================================================================

def plot_conversion_summary(
    vdac: np.ndarray,
    vdiff: np.ndarray,
    vcomp: np.ndarray,
    t_local: Optional[np.ndarray] = None,
    title: str = "SAR ADC Conversion Summary",
) -> go.Figure:
    """Three-panel plot: DAC trials, differential settling, comparator regen."""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=["DAC Trial Voltages", "Differential Settling", "Comparator Regeneration"],
        vertical_spacing=0.08,
    )

    # DAC trials
    fig.add_trace(go.Scatter(
        x=list(range(len(vdac))), y=vdac,
        mode="lines+markers", name="V_DAC",
        line=dict(color=COLORS["primary"], width=2),
        marker=dict(size=6),
    ), row=1, col=1)

    # Differential
    T = vdiff.shape[-1] if vdiff.ndim > 1 else len(vdiff)
    t = t_local if t_local is not None else np.linspace(0, 1, T)
    for k in range(min(vdiff.shape[0] if vdiff.ndim > 1 else 1, 4)):
        y = vdiff[k] if vdiff.ndim > 1 else vdiff
        fig.add_trace(go.Scatter(
            x=t, y=y, mode="lines", name=f"Bit {k}",
            showlegend=False,
        ), row=2, col=1)

    # Comparator
    for k in range(min(vcomp.shape[0] if vcomp.ndim > 1 else 1, 4)):
        y = vcomp[k] if vcomp.ndim > 1 else vcomp
        fig.add_trace(go.Scatter(
            x=t, y=y, mode="lines", name=f"Bit {k}",
            showlegend=False,
        ), row=3, col=1)

    fig.update_layout(
        title=title,
        template=TEMPLATE,
        height=900, width=800,
        showlegend=True,
    )
    fig.update_xaxes(title_text="Bit Trial", row=1, col=1)
    fig.update_xaxes(title_text="Normalised Time", row=2, col=1)
    fig.update_xaxes(title_text="Normalised Time", row=3, col=1)
    fig.update_yaxes(title_text="V (V)", row=1, col=1)
    fig.update_yaxes(title_text="V (V)", row=2, col=1)
    fig.update_yaxes(title_text="V (V)", row=3, col=1)

    return fig


# =========================================================================
# FoM surfaces
# =========================================================================

def plot_fom_heatmap(
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    z_vals: np.ndarray,
    x_name: str,
    y_name: str,
    z_name: str = "Energy (J)",
    title: str = "FoM Heatmap",
    colorscale: str = "Viridis",
) -> go.Figure:
    """2-D heatmap of a FoM surface."""
    fig = go.Figure(data=go.Heatmap(
        x=x_vals, y=y_vals, z=z_vals,
        colorscale=colorscale,
        colorbar=dict(title=z_name),
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_name,
        yaxis_title=y_name,
        template=TEMPLATE,
        width=650, height=500,
    )
    return fig


def plot_fom_contour(
    x_vals: np.ndarray,
    y_vals: np.ndarray,
    z_vals: np.ndarray,
    x_name: str,
    y_name: str,
    z_name: str = "Walden FoM",
    title: str = "FoM Contour",
) -> go.Figure:
    """Contour plot of a FoM surface."""
    fig = go.Figure(data=go.Contour(
        x=x_vals, y=y_vals, z=z_vals,
        colorscale="RdYlGn_r",
        contours=dict(showlabels=True, labelfont=dict(size=10)),
        colorbar=dict(title=z_name),
    ))
    fig.update_layout(
        title=title,
        xaxis_title=x_name,
        yaxis_title=y_name,
        template=TEMPLATE,
        width=650, height=500,
    )
    return fig


# =========================================================================
# Training curves
# =========================================================================

def plot_training_history(
    history: Dict[str, list],
    title: str = "Training History",
) -> go.Figure:
    """Plot loss terms over epochs from training history."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=["Train", "Validation"])

    loss_keys = ["total", "data", "kcl", "charge", "comp_ode", "smooth"]
    colors_list = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    for side_idx, side in enumerate(["train", "val"]):
        entries = history.get(side, [])
        if not entries:
            continue
        epochs_range = list(range(1, len(entries) + 1))
        for ki, key in enumerate(loss_keys):
            vals = [e.get(key, 0.0) for e in entries]
            if max(vals) == 0:
                continue
            fig.add_trace(go.Scatter(
                x=epochs_range, y=vals,
                mode="lines",
                name=f"{key}" if side_idx == 0 else None,
                line=dict(color=colors_list[ki % len(colors_list)], width=2),
                showlegend=(side_idx == 0),
            ), row=1, col=side_idx + 1)

    fig.update_layout(
        title=title,
        template=TEMPLATE,
        height=400, width=900,
    )
    fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(type="log", row=1, col=2)
    fig.update_xaxes(title_text="Epoch", row=1, col=1)
    fig.update_xaxes(title_text="Epoch", row=1, col=2)
    return fig


# =========================================================================
# Inverse design trajectory
# =========================================================================

def plot_inverse_trajectory(
    trajectory: List[Dict],
    param_names: List[str] = ["cu", "gm"],
    title: str = "Inverse Design Trajectory",
) -> go.Figure:
    """Plot how design params + objectives evolve during optimisation."""
    steps = [t["step"] for t in trajectory]

    n_params = len(param_names)
    n_rows = n_params + 2  # params + meta + energy

    fig = make_subplots(
        rows=n_rows, cols=1,
        subplot_titles=[*param_names, "Max Metastability", "Energy"],
        vertical_spacing=0.06,
    )

    for i, pn in enumerate(param_names):
        vals = [t.get(pn, 0.0) for t in trajectory]
        fig.add_trace(go.Scatter(
            x=steps, y=vals, mode="lines",
            name=pn, line=dict(width=2),
        ), row=i + 1, col=1)

    meta_vals = [t.get("max_meta_s", 0.0) for t in trajectory]
    fig.add_trace(go.Scatter(
        x=steps, y=meta_vals, mode="lines",
        name="Metastability", line=dict(color=COLORS["accent"], width=2),
    ), row=n_params + 1, col=1)

    energy_vals = [t.get("energy_j", 0.0) for t in trajectory]
    fig.add_trace(go.Scatter(
        x=steps, y=energy_vals, mode="lines",
        name="Energy", line=dict(color=COLORS["secondary"], width=2),
    ), row=n_params + 2, col=1)

    fig.update_layout(
        title=title,
        template=TEMPLATE,
        height=250 * n_rows, width=750,
        showlegend=False,
    )
    for i in range(1, n_rows + 1):
        fig.update_xaxes(title_text="Step", row=i, col=1)

    return fig


# =========================================================================
# Save helper
# =========================================================================

def save_figure(fig: go.Figure, name: str, formats: List[str] = ["png", "html"]):
    """Save a Plotly figure to assets/figures/ in given formats."""
    outdir = ensure_dir(FIGURES)
    for fmt in formats:
        path = os.path.join(outdir, f"{name}.{fmt}")
        if fmt == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, scale=2)
        print(f"[NeuroSAR] Saved figure → {path}")
