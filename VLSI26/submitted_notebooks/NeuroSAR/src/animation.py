"""
NeuroSAR animations — animated visualisations of SAR ADC conversion
cycles, metastability behaviour, and decision progression.

Uses Plotly frames for notebook-compatible animations.
"""

from typing import Dict, List, Optional

import numpy as np
import plotly.graph_objects as go

from src.config import DESIGN


# =========================================================================
# Animated bit-cycle progression
# =========================================================================

def animate_conversion(
    vdac: np.ndarray,
    vdiff: np.ndarray,
    vcomp: np.ndarray,
    t_local: Optional[np.ndarray] = None,
    n_bits: int = DESIGN.n_bits,
    title: str = "SAR ADC Conversion — Bit by Bit",
) -> go.Figure:
    """
    Animated figure showing DAC settling and comparator regeneration
    evolving one bit trial at a time.

    Parameters
    ----------
    vdac  : (n_bits+1,) or (n_bits,)
    vdiff : (n_bits, T)
    vcomp : (n_bits, T)
    t_local : (T,)
    """
    T = vdiff.shape[-1]
    if t_local is None:
        t_local = np.linspace(0, 1, T)

    n_show = min(n_bits, vdiff.shape[0])

    # Initial frame: empty
    fig = go.Figure(
        data=[
            # DAC scatter (top-left area conceptually)
            go.Scatter(x=[], y=[], mode="lines+markers",
                       name="V_DAC", line=dict(color="#1f77b4", width=2),
                       marker=dict(size=8)),
            # Comparator for current bit
            go.Scatter(x=[], y=[], mode="lines",
                       name="V_comp", line=dict(color="#d62728", width=2)),
            # Decision marker
            go.Scatter(x=[], y=[], mode="markers",
                       name="Decision", marker=dict(size=14, symbol="star",
                       color="#2ca02c")),
        ],
    )

    # Build frames
    frames = []
    for k in range(n_show):
        dac_x = list(range(k + 2))
        dac_y = list(vdac[:k + 2])

        comp_y = vcomp[k].tolist()
        decision_val = vcomp[k, -1]

        frame = go.Frame(
            data=[
                go.Scatter(x=dac_x, y=dac_y,
                           mode="lines+markers",
                           line=dict(color="#1f77b4", width=2),
                           marker=dict(size=8)),
                go.Scatter(x=t_local.tolist(), y=comp_y,
                           mode="lines",
                           line=dict(color="#d62728", width=2)),
                go.Scatter(x=[t_local[-1]], y=[float(decision_val)],
                           mode="markers",
                           marker=dict(size=14, symbol="star", color="#2ca02c")),
            ],
            name=f"Bit {k}",
        )
        frames.append(frame)

    fig.frames = frames

    # Slider + play button
    fig.update_layout(
        title=title,
        xaxis=dict(title="Bit Trial / Normalised Time", range=[-0.5, max(n_show + 1, T)]),
        yaxis=dict(title="Voltage (V)", range=[
            min(float(vdac.min()), float(vcomp.min())) - 0.1,
            max(float(vdac.max()), float(vcomp.max())) + 0.1,
        ]),
        template="plotly_white",
        width=800, height=500,
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=1.15, x=0.5, xanchor="center",
            buttons=[
                dict(label="▶ Play",
                     method="animate",
                     args=[None, dict(frame=dict(duration=500, redraw=True),
                                      fromcurrent=True)]),
                dict(label="⏸ Pause",
                     method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0,
            steps=[dict(args=[[f.name], dict(frame=dict(duration=300, redraw=True),
                                             mode="immediate")],
                        label=f.name, method="animate")
                   for f in frames],
            x=0.05, len=0.9,
            xanchor="left",
            y=-0.05,
            currentvalue=dict(prefix="", visible=True),
        )],
    )

    return fig


# =========================================================================
# Metastability boundary animation
# =========================================================================

def animate_metastability(
    vcomp_near: np.ndarray,
    vcomp_safe: np.ndarray,
    t_local: Optional[np.ndarray] = None,
    title: str = "Metastability: Near-Boundary vs Safe",
) -> go.Figure:
    """
    Side-by-side animation comparing comparator regeneration for
    a near-metastable input (small residue) vs a safe input.

    Parameters
    ----------
    vcomp_near : (T,)  — comparator waveform for small residue
    vcomp_safe : (T,)  — comparator waveform for large residue
    """
    T = len(vcomp_near)
    if t_local is None:
        t_local = np.linspace(0, 1, T)

    fig = go.Figure(
        data=[
            go.Scatter(x=[], y=[], mode="lines",
                       name="Near-metastable",
                       line=dict(color="#d62728", width=2.5)),
            go.Scatter(x=[], y=[], mode="lines",
                       name="Safe margin",
                       line=dict(color="#2ca02c", width=2.5)),
            # Decision threshold
            go.Scatter(x=[0, 1], y=[0.9, 0.9], mode="lines",
                       name="Threshold",
                       line=dict(color="#7f7f7f", width=1, dash="dash")),
            go.Scatter(x=[0, 1], y=[-0.9, -0.9], mode="lines",
                       showlegend=False,
                       line=dict(color="#7f7f7f", width=1, dash="dash")),
        ],
    )

    step = max(1, T // 30)
    frames = []
    for end in range(2, T + 1, step):
        frames.append(go.Frame(
            data=[
                go.Scatter(x=t_local[:end].tolist(), y=vcomp_near[:end].tolist(),
                           mode="lines", line=dict(color="#d62728", width=2.5)),
                go.Scatter(x=t_local[:end].tolist(), y=vcomp_safe[:end].tolist(),
                           mode="lines", line=dict(color="#2ca02c", width=2.5)),
                go.Scatter(x=[0, 1], y=[0.9, 0.9], mode="lines",
                           line=dict(color="#7f7f7f", width=1, dash="dash")),
                go.Scatter(x=[0, 1], y=[-0.9, -0.9], mode="lines",
                           line=dict(color="#7f7f7f", width=1, dash="dash")),
            ],
            name=f"t={t_local[min(end-1, T-1)]:.2f}",
        ))

    fig.frames = frames

    fig.update_layout(
        title=title,
        xaxis_title="Normalised Time",
        yaxis_title="V_comp (V)",
        yaxis=dict(range=[-2.0, 2.0]),
        template="plotly_white",
        width=750, height=450,
        updatemenus=[dict(
            type="buttons", showactive=False,
            y=1.12, x=0.5, xanchor="center",
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=80, redraw=True),
                                      fromcurrent=True)]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
    )

    return fig
