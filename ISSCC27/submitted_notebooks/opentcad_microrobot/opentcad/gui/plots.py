"""
opentcad.gui.plots — matplotlib helpers used by the Streamlit app.

Kept out of app.py so we don't rebuild figures on every widget change
just to inspect them, and so the plotting code is unit-testable.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from opentcad.geometry.formats import MATERIAL_NAMES, Material, MeshField


PALETTE = {
    Material.SI:          "#c9a66b",
    Material.SIO2:        "#7fb8d9",
    Material.SI3N4:       "#a6c48a",
    Material.POLY_SI:     "#b58e77",
    Material.AL:          "#c9c9c9",
    Material.PHOTORESIST: "#e0a5c8",
    Material.SIGE:        "#d9a17f",
    Material.GAN:         "#8bb0d9",
    Material.SIC:         "#9a9a9a",
    Material.SUBSTRATE:   "#bfa383",
    Material.VACUUM:      "#ffffff",
}


def _color(material: Material) -> str:
    return PALETTE.get(material, "#bbbbbb")


def plot_structure_stack(structure) -> plt.Figure:
    """Cross-section preview of a Structure: horizontal layer bands
    plus rectangular region overlays."""
    fig, ax = plt.subplots(figsize=(6, 3.6))

    y = 0.0
    width = float(structure.width_um)
    layers = list(structure._layers)
    total_h = sum(l.thickness_um for l in layers) or 1.0

    for layer in layers:
        h = layer.thickness_um
        ax.fill_between([0, width], [y, y], [y + h, y + h],
                        color=_color(layer.material),
                        edgecolor="black", linewidth=0.6,
                        label=MATERIAL_NAMES.get(layer.material, layer.material.name))
        # Text: material name + doping (if any) at the midline
        info = MATERIAL_NAMES.get(layer.material, layer.material.name)
        if layer.doping_Nd:
            info += f" (Nd={layer.doping_Nd:.1e})"
        elif layer.doping_Na:
            info += f" (Na={layer.doping_Na:.1e})"
        ax.text(width / 2, y + h / 2, info,
                ha="center", va="center", fontsize=8,
                color="#222", alpha=0.85)
        y += h

    # Region overlays (rectangular, may punch through layers).
    for region in getattr(structure, "_regions", []):
        rw = region.x_end - region.x_start
        rh = region.y_end - region.y_start
        rect = plt.Rectangle((region.x_start, region.y_start),
                             rw, rh, facecolor=_color(region.material),
                             edgecolor="#333", linewidth=1.0, alpha=0.9,
                             hatch="///")
        ax.add_patch(rect)
        info = f"{MATERIAL_NAMES.get(region.material, region.material.name)}"
        if region.doping_Nd:
            info += f" Nd={region.doping_Nd:.0e}"
        elif region.doping_Na:
            info += f" Na={region.doping_Na:.0e}"
        ax.text(region.x_start + rw / 2, region.y_start + rh / 2,
                info, ha="center", va="center", fontsize=7,
                color="#222")

    # Contact markers along the top/bottom edges.
    for c in getattr(structure, "_contacts", []):
        y_c = 0.0 if c.surface == "bottom" else total_h
        ax.plot([c.x_start, c.x_end], [y_c, y_c],
                color="#c22", lw=3, solid_capstyle="butt")
        ax.text((c.x_start + c.x_end) / 2, y_c,
                f" {c.name} ", ha="center",
                va="bottom" if c.surface == "top" else "top",
                fontsize=8, color="#c22", weight="bold")

    ax.set_xlim(0, width)
    ax.set_ylim(-0.02 * total_h, 1.02 * total_h)
    ax.set_xlabel("x [µm]")
    ax.set_ylabel("y [µm]")
    ax.set_title(f"Structure — {structure.name}", fontsize=10)
    ax.set_aspect("auto")
    handles, labels = ax.get_legend_handles_labels()
    seen = set(); uniq = []
    for h, l in zip(handles, labels):
        if l not in seen:
            uniq.append((h, l)); seen.add(l)
    if uniq:
        ax.legend([h for h, _ in uniq], [l for _, l in uniq],
                  loc="lower right", fontsize=7)
    fig.tight_layout()
    return fig


def plot_topography_polylines(bounds: Tuple[float, float, float, float],
                              polylines: List[Tuple[Material, np.ndarray, np.ndarray]],
                              title: str = "") -> plt.Figure:
    """Stack view: fill between successive layer top curves."""
    fig, ax = plt.subplots(figsize=(6, 3.6))
    xmin, xmax, ymin, ymax = bounds
    prev_x = np.array([xmin, xmax])
    prev_y = np.full(2, ymin)
    for material, xs, ys in polylines:
        n = max(int(xs.size), 2)
        xi = np.linspace(xmin, xmax, n)
        yi = np.interp(xi, xs, ys) if xs.size >= 2 else np.full_like(xi, ys[0])
        yb = np.interp(xi, prev_x, prev_y)
        ax.fill_between(xi, yb, yi, color=_color(material),
                        edgecolor="black", linewidth=0.5,
                        label=MATERIAL_NAMES.get(material, material.name))
        prev_x, prev_y = xi, yi
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, max(ymax, float(prev_y.max()) * 1.05))
    ax.set_xlabel("x [µm]"); ax.set_ylabel("y [µm]")
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.2)
    handles, labels = ax.get_legend_handles_labels()
    seen = set(); uniq = []
    for h, l in zip(handles, labels):
        if l not in seen:
            uniq.append((h, l)); seen.add(l)
    if uniq:
        ax.legend([h for h, _ in uniq], [l for _, l in uniq],
                  loc="upper right", fontsize=7)
    fig.tight_layout()
    return fig


def plot_meshfield(mf: MeshField, title: str = "") -> plt.Figure:
    """Per-material triangulation view of a MeshField."""
    fig, ax = plt.subplots(figsize=(6.5, 4))
    pts = np.asarray(mf.grid.points)[:, :2]
    tris = mf.grid.cells_dict.get(5)   # VTK triangle
    if tris is None:
        ax.text(0.5, 0.5, "MeshField has no triangles",
                ha="center", va="center", transform=ax.transAxes)
        return fig
    for material_id in np.unique(mf.material_ids):
        try:
            mat = Material(int(material_id))
        except ValueError:
            continue
        mask = mf.material_ids == material_id
        color = _color(mat)
        for a, b, c in tris[mask]:
            xs = [pts[a, 0], pts[b, 0], pts[c, 0], pts[a, 0]]
            ys = [pts[a, 1], pts[b, 1], pts[c, 1], pts[a, 1]]
            ax.fill(xs, ys, color=color, edgecolor="k", linewidth=0.12)
    ax.set_xlabel("x [µm]"); ax.set_ylabel("y [µm]")
    ax.set_title(title or f"MeshField — {mf.n_cells} triangles", fontsize=10)
    ax.set_aspect("equal")
    xmin, xmax, ymin, ymax = mf.bounds[:4]
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax * 1.02)
    handles = [plt.Rectangle((0, 0), 1, 1, color=_color(m))
               for m in {Material(int(mid)) for mid in np.unique(mf.material_ids)}]
    labels = [MATERIAL_NAMES.get(m, m.name)
              for m in {Material(int(mid)) for mid in np.unique(mf.material_ids)}]
    ax.legend(handles, labels, loc="upper right", fontsize=7)
    fig.tight_layout()
    return fig


def plot_iv(V, I, title: str = "IV sweep") -> plt.Figure:
    """IV curve with linear + semilog panels."""
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
    V = np.asarray(V); I = np.asarray(I)

    axes[0].plot(V, I, "o-", color="#c22", markersize=4)
    axes[0].set_xlabel("V [V]"); axes[0].set_ylabel("I [A/cm]")
    axes[0].set_title(f"{title} — linear", fontsize=10)
    axes[0].grid(True, alpha=0.25)

    I_abs = np.abs(I)
    axes[1].semilogy(V, np.clip(I_abs, 1e-30, None), "o-",
                     color="#c22", markersize=4)
    axes[1].set_xlabel("V [V]"); axes[1].set_ylabel("|I| [A/cm]")
    axes[1].set_title(f"{title} — semilog", fontsize=10)
    axes[1].grid(True, alpha=0.25, which="both")

    fig.tight_layout()
    return fig


def plot_cv(V, C, title: str = "CV sweep") -> plt.Figure:
    """CV curve with linear + normalized panels."""
    fig, ax = plt.subplots(figsize=(6, 3.6))
    V = np.asarray(V); C = np.asarray(C)
    ax.plot(V, C, "o-", color="#2d6cba", markersize=4)
    ax.set_xlabel("V [V]"); ax.set_ylabel("C [F/cm]")
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig
