"""Consistent final-size figure settings based on IEEE's public graphics guidance."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.text import Text
import numpy as np

IEEE_GUIDANCE = (
    "https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/"
    "create-graphics-for-your-article/"
)


@dataclass(frozen=True)
class FigureProfile:
    width_in: float = 7.16
    height_in: float = 1.95
    font_pt: float = 9.0
    line_pt: float = 0.7
    png_dpi: int = 600


def available_font() -> str:
    for family in ("Arial", "Liberation Sans", "DejaVu Sans"):
        try:
            font_manager.findfont(font_manager.FontProperties(family=family), fallback_to_default=False)
        except ValueError:
            continue
        return family
    raise RuntimeError("A local sans-serif figure font is required; no font is downloaded automatically")


@contextmanager
def publication_style(profile: FigureProfile = FigureProfile()):
    family = available_font()
    with mpl.rc_context({
        "font.family": family,
        "text.usetex": False,
        "font.size": profile.font_pt,
        "axes.labelsize": profile.font_pt,
        "axes.titlesize": profile.font_pt + 0.5,
        "xtick.labelsize": profile.font_pt,
        "ytick.labelsize": profile.font_pt,
        "legend.fontsize": profile.font_pt,
        "axes.linewidth": profile.line_pt,
        "lines.linewidth": 1.2,
        "xtick.major.width": profile.line_pt,
        "ytick.major.width": profile.line_pt,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.pad": 2.0,
        "ytick.major.pad": 2.0,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": None,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "svg.hashsalt": "comparator-atlas-publication-figures",
        "mathtext.fontset": "dejavusans",
    }):
        yield family


def luminance(color) -> float:
    rgb = np.asarray(color[:3], dtype=float)
    if rgb.shape != (3,) or not np.isfinite(rgb).all() or ((rgb < 0) | (rgb > 1)).any():
        raise ValueError("Figure color must contain three finite sRGB channels in [0, 1]")
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return float(np.dot(linear, [0.2126, 0.7152, 0.0722]))


def contrast_ink(color) -> str:
    value = luminance(color)
    black = (value + 0.05) / 0.05
    white = 1.05 / (value + 0.05)
    return "black" if black >= white else "white"


def contrast_ratio(ink: str, color) -> float:
    value = luminance(color)
    if ink == "black":
        return (value + 0.05) / 0.05
    if ink == "white":
        return 1.05 / (value + 0.05)
    raise ValueError("The annotation contrast check supports black or white text")


def review_artists(figure, profile: FigureProfile) -> dict:
    if not np.allclose(figure.get_size_inches(), [profile.width_in, profile.height_in], rtol=0, atol=1e-8):
        raise ValueError("The figure's actual physical size does not match the publication profile")
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    labels = []
    boxes = []
    for text in figure.findobj(match=Text):
        if not text.get_visible() or not text.get_text().strip():
            continue
        size = text.get_fontsize()
        if not profile.font_pt <= size <= profile.font_pt + 1:
            raise ValueError(f"Figure text is outside the final-size 9-10 pt range: {text.get_text()!r}")
        box = text.get_window_extent(renderer=renderer)
        page = figure.bbox
        if box.x0 < page.x0 - 1 or box.y0 < page.y0 - 1 \
                or box.x1 > page.x1 + 1 or box.y1 > page.y1 + 1:
            raise ValueError(f"Figure text extends outside its fixed-size canvas: {text.get_text()!r}")
        labels.append({"text": text.get_text(), "font_pt": size})
        boxes.append((text.get_text(), box))
    if not labels:
        raise ValueError("The publication figure has no labels")
    for index, (label, box) in enumerate(boxes):
        for other_label, other in boxes[index + 1:]:
            overlap_x = min(box.x1, other.x1) - max(box.x0, other.x0)
            overlap_y = min(box.y1, other.y1) - max(box.y0, other.y0)
            if overlap_x > 0.5 and overlap_y > 0.5:
                raise ValueError(f"Figure labels overlap at final size: {label!r} and {other_label!r}")
    return {
        "profile": asdict(profile),
        "text_artists": len(labels),
        "minimum_font_pt": min(label["font_pt"] for label in labels),
        "maximum_font_pt": max(label["font_pt"] for label in labels),
        "outside_canvas_text": False,
        "overlapping_text_artists": False,
    }


def export_figure(figure, directory: Path, basename: str, profile: FigureProfile) -> dict:
    if not basename or Path(basename).name != basename:
        raise ValueError("A plain figure basename is required")
    review = review_artists(figure, profile)
    directory.mkdir(parents=True, exist_ok=True)
    with publication_style(profile) as family:
        paths = {
            "pdf": directory / f"{basename}.pdf",
            "svg": directory / f"{basename}.svg",
            "png": directory / f"{basename}.png",
        }
        figure.savefig(paths["pdf"], metadata={
            "Creator": "Comparator Atlas", "Title": basename,
            "CreationDate": None, "ModDate": None,
        })
        figure.savefig(paths["svg"], metadata={"Creator": "Comparator Atlas", "Date": None})
        figure.savefig(paths["png"], dpi=profile.png_dpi, metadata={"Software": "Comparator Atlas"})
    return {
        **review,
        "font_family": family,
        "guidance_url": IEEE_GUIDANCE,
        "publication_master": paths["pdf"].name,
        "svg_role": "Editable browser/notebook companion, not an asserted IEEE submission format.",
        "artifact_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()
        },
        "ieee_certification_or_publication_acceptance": False,
    }
