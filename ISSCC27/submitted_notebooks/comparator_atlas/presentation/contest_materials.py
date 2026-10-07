"""Generate the evidence-led poster and guide from checked release facts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon

import layout_evidence as physical
import single_row_evidence as area
from presentation.release_facts import load_facts
from presentation.pvt45_results import RC_MODEL_LABEL, RC_SCOPE_NOTE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "study"
PRESENTATION_TITLE = "Comparator Atlas: correct before the deadline - or NONE?"
INK, BLUE, MUTED, RULE = "#20252b", "#365d7d", "#505963", "#dce1e5"
PAGE_INCHES = (24, 18)
DESIGN_REFERENCES = [
    "https://mitcommlab.mit.edu/nse/commkit/poster/",
    "https://mitcommlab.mit.edu/nse/wp-content/uploads/sites/4/2019/07/PosterExampleJepeal.jpg",
    "https://mitcommlab.mit.edu/nse/wp-content/uploads/sites/4/2019/07/PosterAnnotatedExample.jpg",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def poster_figure(facts: dict):
    """Draw three aligned columns; measure the actual text before export."""
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})
    figure = plt.figure(figsize=PAGE_INCHES, facecolor="white", dpi=100)
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    texts, images = [], []
    width_px = figure.bbox.width
    left, center, right, column_width = 0.04, 0.355, 0.67, 0.29
    author = facts["authors"][0]
    geometry = facts["area_optimization"]
    sampled = facts["sampled_schematic"]
    none, selected, control = sampled["poster_choices"]

    def text(x, y, value, size=18, color=INK, weight="normal", url=None,
             width=None, role="body"):
        if width is not None:
            lines = []
            font = FontProperties(family="DejaVu Sans", size=size, weight=weight)
            for paragraph in value.split("\n"):
                line = ""
                for word in paragraph.split():
                    candidate = f"{line} {word}".strip()
                    measured = renderer.get_text_width_height_descent(candidate, font, False)[0]
                    if line and measured > width * width_px:
                        lines.append(line)
                        line = word
                    else:
                        line = candidate
                lines.append(line)
            value = "\n".join(lines)
        artist = figure.text(x, y, value, fontsize=size, color=color, weight=weight,
                             va="top", linespacing=1.25, url=url)
        texts.append((artist, role))
        return artist

    def rule(x, y, width=column_width):
        figure.add_artist(plt.Line2D([x, x + width], [y, y],
                                     transform=figure.transFigure, color=RULE, linewidth=0.8))

    def image(path, bounds, role):
        pixels = plt.imread(path)
        axes = figure.add_axes(bounds)
        axes.imshow(pixels)
        axes.axis("off")
        images.append({"path": str(path.relative_to(ROOT)), "role": role,
                       "source_pixels": list(pixels.shape[:2][::-1]),
                       "allocated_bounds": list(bounds)})

    text(left, 0.966, "Correct before the deadline - or NONE?",
         34, weight="bold", role="title")
    text(left, 0.919, "Comparator Atlas  |  specify, qualify, then compare energy",
         22, BLUE, role="subtitle")
    text(left, 0.881, f"{author['name']}  |  {author['affiliation']}", 18, role="author")
    text(right, 0.881, "IEEE SSCS Code-a-Chip  /  ISSCC 2027", 16, role="contest")
    rule(left, 0.856, 0.92)
    for x, heading in ((left, "What a choice must satisfy"),
                       (center, "Specify, qualify, then choose"),
                       (right, "Separate matched layout example")):
        text(x, 0.838, heading, 23, weight="bold", role="heading")

    text(left, 0.797, "Calibration alone is not qualification.\n"
         "Every included point must be correct on time.", width=column_width)
    circuit = physical.circuit_guide_path()
    waveform = OUTPUT / "figures" / "single_row_worst.png"
    image(circuit, [left, 0.426, column_width, 0.307], "original_27_mos_schematic")
    text(left, 0.413, "Recorded circuit topology. Nine declared sizing candidates; "
         "the lower-energy control was evaluated after selection.",
         16, MUTED, width=column_width, role="caption")
    text(left, 0.343, "Correct, wrong or unresolved", 22, weight="bold", role="heading")
    text(left, 0.305, "A correct decision reaches complementary 80% / 20% "
         "output rails with the expected polarity before the deadline. "
         "Wrong polarity and unresolved outputs are counted separately.",
         width=column_width)
    text(left, 0.218, "Calibration and full-cycle core energy are evaluated "
         "from archived measurements. A later readout does not rerun "
         "SPICE or shorten the measured energy cycle.", 17, width=column_width)

    text(center, 0.797, "Calibrated SCHEMATIC: local_boundary; all 49 "
         "controlled-width-stress conditions. Both signs at finite "
         "sampled inputs through 30 mV; 1 ns deadline.",
         17, width=column_width, role="schematic_scope")
    for y, choice, label in zip((0.690, 0.590, 0.490),
                                (none, selected, control), ("NONE", "Selected", "Control")):
        rule(center, y + 0.012)
        text(center, y, f">= {choice['minimum_abs_input_mv']:g} mV", 21, BLUE, weight="bold",
             role="specification")
        x = center + 0.078
        if choice["winner"] is None:
            text(x, y, "NONE", 21, weight="bold", role="selection")
            text(x, y - 0.033, "No feasible compared design", 17)
            text(x, y - 0.060, "Mean energy / limits: not defined", 15, MUTED)
        else:
            text(x, y, f"{label}: {choice['winner']}", 17, weight="bold", role="selection")
            text(x, y - 0.033,
                 f"{choice['correct']}/{choice['points']} correct at all included samples", 16)
            text(x, y - 0.060, f"{choice['mean_core_energy_fj']:.3f} fJ mean core / cycle",
                 17, BLUE, role="mean_energy")
    text(center, 0.392, "Post-hoc: qualify, then rank three designs. "
         "Different-band energies are not a same-spec gain. "
         "No interpolation or global optimum.", 16, MUTED, width=column_width)
    limits = selected["sampled_limits"]
    text(center, 0.316, f"Selected >= 3 mV band  /  same {selected['points']} samples",
         17, weight="bold")
    text(center, 0.283, f"{limits['minimum_decision_margin_ps']:.3f} ps", 25, BLUE, weight="bold",
         role="sampled_margin")
    text(center + 0.153, 0.283, f"{limits['maximum_core_energy_fj']:.3f} fJ",
         25, BLUE, weight="bold", role="sampled_max_energy")
    text(center, 0.248, "Min. deadline - recorded\n decision time (sampled)", 15)
    text(center + 0.153, 0.248, "Maximum sampled core energy", 14)
    wrong = sampled["selected_wrong"]
    text(center, 0.211, f"{wrong['count_1ns']} wrong samples remain at 2 ns", 21, weight="bold")
    text(center, 0.177, "Exactly the same keyed set at 1 ns and 2 ns, all "
         "at signed +/-1 mV. Locations and trim codes do not identify "
         "a physical failure cause.", 16, width=column_width)

    text(right, 0.797, "Local-pitch b1 vs adopted a1; known nonblind, code-zero: 45 PVT conditions "
         "x four signed inputs (-10, -3, +3, +10 mV). "
         "180 keys per layout / C or RC; ngspice-47.",
         17, width=column_width, role="rc_scope")
    axes = figure.add_axes([right, 0.611, column_width, 0.106])
    layers = physical.gds_polygons((area.FOLDER / "native/candidate/atlas.gds").read_bytes())
    for index, (_, polygons) in enumerate(sorted(layers.items())):
        axes.add_collection(PatchCollection(
            [Polygon(points, closed=True) for points in polygons],
            facecolor=BLUE if index % 2 else "#b4bec7", edgecolor="none", alpha=0.75))
    bounds = [-55.0, -4.84, 55.0, 12.19]
    axes.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]), aspect="equal")
    axes.axis("off")
    text(right, 0.598, f"Bbox (um2): adopted {geometry['candidate_area_um2']:.3f} / "
         f"matched a1 {geometry['control_area_um2']:.3f} (9.69% less).\n"
         "Historical native proofs reused, not rerun; no signoff.",
         16, MUTED, width=column_width, role="caption")
    for x, label in ((right, "Correct / 180"), (right + 0.12, "1 ns"),
                     (right + 0.20, "2 ns")):
        text(x, 0.535, label, 17, weight="bold")
    rule(right, 0.509)
    for y, name, first, second in (
        (0.498, "Both C", 170, 180),
        (0.466, "a1 RC", 156, 180),
        (0.434, "b1 RC", 158, 180),
    ):
        text(right, y, name, 18)
        text(right + 0.12, y, f"{first}/180", 18)
        text(right + 0.20, y, f"{second}/180", 18)
    text(right, 0.399, "RC mean: 421.04 -> 412.88 fJ / cycle", 17, BLUE, role="rc_energy")
    text(right, 0.370, "1 ns RC unresolved: a1 24 -> b1 22; zero wrong.\n"
         "Only SS / 1.62 V / 125 C / +/-10 mV improve; FS remains late.\n"
         "2 ns primary, prospectively declared; no lost correct keys.",
         16, width=column_width)
    image(waveform, [right, 0.210, column_width, 0.115], "retained_nominal_rc_waveform")
    text(right, 0.197, "Matched a1 -> b1; worst RC: 1.811 -> 1.760 ns.\n"
         "~1.94% energy change is not robust global PPA.",
         16, MUTED, width=column_width, role="caption")

    rule(left, 0.132, 0.92)
    text(left, 0.119, RC_MODEL_LABEL + ".", 18, weight="bold", role="rc_warning")
    text(left, 0.094, "No qualified PEX or silicon prediction. C-only is not independent ground truth; "
         "RC-versus-C differences do not isolate resistance.", 16, role="rc_limit")
    text(left, 0.071, "Finite samples, not foundry Monte Carlo/yield, noise/jitter/PVT confidence, "
         "timing signoff or a worst-cycle guarantee. Core excludes drivers and calibration/controller infrastructure.",
         14, role="sampled_limit")
    text(left, 0.049, "References: Razavi (2015), DOI 10.1109/MSSC.2015.2418155; "
         "Li, Xu & Iizuka (2022), DOI 10.1007/s10470-022-01992-6.", 14, MUTED, role="reference")
    text(left, 0.028, "Original code: MIT; SKY130: Apache-2.0. GitHub Copilot assisted implementation, "
         "experiment automation, figures and documentation; the author is responsible.", 14, role="acknowledgment")
    text(right + 0.075, 0.119, "Source Notebook", 15, BLUE, url=facts["notebook_url"], role="link")
    text(right + 0.22, 0.119, "Source Colab", 14, BLUE, url=facts["colab_url"], role="link")
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    measured = []
    for artist, role in texts:
        box = artist.get_window_extent(renderer).transformed(figure.transFigure.inverted())
        measured.append({"role": role, "text": artist.get_text(), "font_pt": artist.get_fontsize(),
                         "color": artist.get_color(), "bounds": list(box.bounds)})
    for item in measured:
        x, y, w, h = item["bounds"]
        if x < 0.035 or y < 0.008 or x + w > 0.969 or y + h > 0.975:
            raise ValueError(f"Poster text outside page margins: {item['text']}")
    for index, item in enumerate(measured):
        x, y, w, h = item["bounds"]
        for other in measured[index + 1:]:
            a, b, c, d = other["bounds"]
            if min(x + w, a + c) > max(x, a) and min(y + h, b + d) > max(y, b):
                raise ValueError(f"Poster text overlap: {item['text']} / {other['text']}")
    return figure, {"page_inches": list(PAGE_INCHES), "columns": [left, center, right],
                    "column_width": column_width, "text": measured, "images": images,
                    "all_text_in_bounds": True, "text_overlaps": 0}


def build() -> Path:
    from presentation.judge_decision import OPENING, write_reader_docs

    facts = load_facts()
    write_reader_docs()
    guide = ROOT / "REVIEWER_GUIDE.md"
    figure, audit = poster_figure(facts)
    author = facts["authors"][0]
    full = facts["postlayout_pvt45"]
    _, selected, control = facts["sampled_schematic"]["poster_choices"]
    pdf, preview = OUTPUT / "Comparator_Atlas_Poster.pdf", OUTPUT / "poster_preview.png"
    figure.savefig(pdf, dpi=300, metadata={
        "Title": PRESENTATION_TITLE, "Subject": "Code-a-Chip schematic-to-layout characterization",
        "Author": author["name"], "CreationDate": None, "ModDate": None,
    })
    figure.savefig(preview, dpi=100)
    plt.close(figure)
    abstract = (
        f"{PRESENTATION_TITLE}\n{author['name']} - {author['affiliation']}\n\n"
        + OPENING + "\n\n"
        "A declared nine-candidate sizing comparison "
        "is followed by a lower-energy control and a nominal 27-device layout. "
        "For three locally calibrated schematic designs, a post-hoc strict specification "
        "map uses all 49 controlled-width-stress conditions and both signs at the "
        "included finite sampled inputs through 30 mV. At 1 ns, no compared design "
        "qualifies for the >=1 mV band. "
        f"For >=3 mV, {selected['winner']} gives {selected['correct']}/{selected['points']} "
        f"correct at {selected['mean_core_energy_fj']:.3f} fJ mean core energy; for >=30 mV, "
        f"{control['winner']} gives {control['correct']}/{control['points']} at "
        f"{control['mean_core_energy_fj']:.3f} fJ. "
        "Qualification requires every included point to be correct before mean energy "
        "ranks designs; the original training selection is unchanged. The selected "
        f"design retains the same {facts['sampled_schematic']['selected_wrong']['count_1ns']} "
        "wrong keyed samples at 1 ns and 2 ns, all at +/-1 mV; "
        "their locations do not establish a physical failure cause.\n\n"
        "The adopted local-pitch b1 layout reduces all-material bbox area from "
        "matched adopted a1's 2074.254 to 1873.3 um2 (9.688013%), preserving 27 guarded MOS devices "
        "and 15 ports. A separate paired 45-PVT qualification at nominal geometry, "
        "code zero and signed +/-3 and +/-10 mV completed 1440 transients and "
        "720 qualified 10/5 ps pairs. Both layouts and C/RC modes retain 180/180 "
        "correct points at the fixed 2 ns primary deadline. At 1 ns, C-only retains "
        "170 correct / 10 unresolved; RC improves from 156 correct / 24 unresolved "
        "to 158 correct / 22 unresolved, only at SS / 1.62 V / 125 C / +/-10 mV. "
        "Mean RC core energy decreases from 421.044730 to "
        "412.879469 fJ (-1.939286%, ratio of means; -1.945659%, mean per-point change), "
        "and worst recorded latency from 1.810632 to 1.760276 ns. "
        "All matched energy and delay pairs decrease, but their physical accuracy "
        "is unqualified. The approximately 1.94% energy change is not a robust PPA "
        "result; the 1% / 20 ps numerical criteria are not uncertainty bounds.\n\n"
        "The historical original compact control's nominal, code-zero study covers 45 PVT conditions and four signed "
        f"inputs each. Schematic gives {full['schematic_correct_1ns']}/180 correct at both "
        f"deadlines; archived RC gives {full['rc_correct_1ns']}/180 at 1 ns "
        f"(24 unresolved, zero wrong) and {full['rc_correct_2ns']}/180 at its separately "
        f"declared 2 ns deadline. Worst sampled RC decision time is {full['worst_rc_delay_ns']:.3f} ns. "
        f"Mean core energy is {full['mean_schematic_energy_fj']:.2f} fJ schematic and "
        f"{full['mean_rc_energy_fj']:.2f} fJ RC. Recorded DRC/LVS and negative controls "
        "check structure, not parasitic fidelity. The earlier five-condition pilot "
        "remains separate: 12/20 at original 1 ns, 20/20 at post-hoc 2 ns. "
        "Results are finite observations, not continuous coverage, yield, timing signoff "
        "or a worst-cycle guarantee. Core energy excludes drivers and calibration/controller "
        "infrastructure.\n\n" + area.NOTICE + ".\n\nScope: " + RC_SCOPE_NOTE + "\n\n"
        "Original code: MIT. GitHub Copilot assisted implementation, experiment automation, "
        "figures and documentation; the author is responsible for the work.\n"
    )
    abstract_path = OUTPUT / "abstract.txt"
    abstract_path.write_text(abstract, encoding="utf-8", newline="\n")
    manifest = {
        "status": "current_competition_materials_from_verified_evidence",
        "generator_sha256": sha256(Path(__file__)),
        "release_facts_source_sha256": sha256(ROOT / "presentation" / "release_facts.py"),
        "facts": facts, "data_evidence_sha256": facts["evidence_sha256"],
        "illustration_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (physical.circuit_guide_path(),
                         OUTPUT / "figures" / "single_row_worst.png")
        },
        "validation_manifest_sha256": sha256(OUTPUT / "validation_manifest.json"),
        "stress_manifest_sha256": sha256(OUTPUT / "stress_manifest.json"),
        "layout_receipt_sha256": physical.RECEIPT_SHA256,
        "artifact_sha256": {path.name: sha256(path) for path in (pdf, preview, abstract_path)},
        "reviewer_guide_sha256": sha256(guide),
        "presentation": audit,
        "design_provenance": {
            "references": DESIGN_REFERENCES,
            "principles": "One message, figure-led panels, aligned narrative, restrained color, small-scale proof",
            "original_layout": True, "copied_reference_assets": False,
            "palette": {"ink": INK, "accent": BLUE, "secondary_ink": MUTED, "rule": RULE},
            "font": "Existing DejaVu Sans", "native_size_changed": False,
        },
        "public_upload_performed": False, "new_physical_experiments": 0,
    }
    (OUTPUT / "poster_manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated evidence-led poster, abstract and reviewer guide: {pdf.name}")
    return pdf


if __name__ == "__main__":
    build()
