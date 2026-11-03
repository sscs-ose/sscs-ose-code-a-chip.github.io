"""Shared loaders and style for accuracy-side figures. All numbers come from JSON."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "python", "out")
VEC = os.path.join(ROOT, "python", "vectors")

# Okabe-Ito colorblind-safe palette
C = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
     "red": "#D55E00", "purple": "#CC79A7", "sky": "#56B4E9",
     "yellow": "#F0E442", "black": "#000000", "grey": "#7a7a7a"}


def load(name, folder=OUT):
    with open(os.path.join(folder, name)) as f:
        return json.load(f)


# accent for SidecarCIM, the same orange as the schematics (schstyle.tex acc)
ACC = "#C85000"
IEEE = {
    # IEEE look: Times text (STIX), closed box, inward ticks on all sides
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 7.5, "axes.linewidth": 0.6, "axes.spines.top": True,
    "axes.spines.right": True, "axes.grid": True, "grid.linestyle": ":",
    "grid.linewidth": 0.5, "grid.color": "#b0b0b0", "grid.alpha": 1.0,
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True,
    "ytick.right": True, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "xtick.major.size": 3, "ytick.major.size": 3, "xtick.minor.visible": False,
    "lines.linewidth": 1.0, "lines.markersize": 4.5, "legend.frameon": True,
    "legend.fancybox": False, "legend.edgecolor": "black",
    "legend.framealpha": 1.0, "patch.linewidth": 0.6,
    "figure.dpi": 100, "savefig.dpi": 300, "savefig.bbox": "tight",
    "pdf.fonttype": 42, "ps.fonttype": 42,
}


def style():
    plt.rcParams.update(IEEE)


def save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(HERE, stem + "." + ext), dpi=300)
    plt.close(fig)
    print("wrote", stem)


def by_scheme(rows):
    return {r["scheme"]: r for r in rows}


def spec():
    """spec/spec.yaml as a dict (single source of truth for widths)."""
    import yaml
    with open(os.path.join(ROOT, "spec", "spec.yaml")) as f:
        return yaml.safe_load(f)
