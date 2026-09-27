"""Generate current contest-facing materials from the same evidence as the notebook."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import FancyBboxPatch, Polygon

import entry_tools as entry
import layout_evidence as physical
from comparator_atlas.spice import CORNERS
from presentation.release_facts import load_facts, write_judge_guide
from presentation.figure_style import contrast_ink
from presentation.pvt45_results import RC_MODEL_LABEL, RC_MODEL_NOTICE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "study"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> Path:
    facts = load_facts()
    evidence = entry.load_evidence()
    layout = physical.load_layout()
    guide = write_judge_guide(facts)
    author = facts["authors"][0]
    schematic, extracted, full = facts["schematic"], facts["layout"], facts["postlayout_pvt45"]
    original_fraction = schematic["baseline_correct_at_1mv"] / schematic["points_at_1mv"]
    selected_fraction = schematic["selected_correct_at_1mv"] / schematic["points_at_1mv"]
    ink, teal, muted, orange = "#15263f", "#008f83", "#63758b", "#d4a343"
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 18,
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42,
    })
    figure = plt.figure(figsize=(24, 18), facecolor="white")
    page = figure.add_axes([0, 0, 1, 1])
    page.axis("off")
    page.add_patch(FancyBboxPatch((0, 0.895), 1, 0.105, boxstyle="square,pad=0",
                                 facecolor=ink, edgecolor=ink))
    figure.text(0.035, 0.955, "Comparator Atlas", fontsize=47, color="white", weight="bold")
    figure.text(0.035, 0.918, "Calibration, decision deadlines and the limits of an archived RC model",
                fontsize=23, color="#bceee4")
    figure.text(0.975, 0.975, "IEEE SSCS CODE-A-CHIP / ISSCC 2027", fontsize=13,
                color="white", ha="right")
    figure.text(0.975, 0.95, f"{author['name']} | {author['affiliation']}", fontsize=14,
                color="#eec86b", ha="right")

    def paragraph(x: float, y: float, value: str, *, width: int, size: int = 18, color: str = ink):
        lines = []
        for part in value.split("\n"):
            lines.extend(textwrap.wrap(part, width=width, break_long_words=False, break_on_hyphens=False)
                         if part else [""])
        figure.text(x, y, "\n".join(lines), color=color, fontsize=size,
                    va="top", linespacing=1.35)

    figure.text(0.035, 0.852, "1 | A reusable experiment", fontsize=26, color=ink, weight="bold")
    paragraph(0.035, 0.814,
              "A small calibrated offset is not enough. "
              "A comparator can decide the wrong way, miss its deadline, "
              "or change behavior after parasitic extraction.\n\n"
              "This notebook makes the complete decision map, costs and "
              "failure boundaries reproducible instead of showing only "
              "one favorable nominal waveform.",
              width=44, size=20)
    figure.text(0.035, 0.625, "Circuit and design choices", fontsize=25, color=teal, weight="bold")
    paragraph(0.035, 0.591,
              "Established StrongARM topology; 27 transistor instances.\n"
              "LVT main/auxiliary input path; standard-VT latch and switches.\n"
              "Physical source-gated trim: sign plus four magnitude bits.\n"
              "Nine declared candidates, followed by an explicit "
              "lower-energy control. No universal best-design claim.",
              width=44, size=19)
    figure.text(0.035, 0.395, "Model applicability", fontsize=25, color=ink, weight="bold")
    paragraph(0.035, 0.36,
              "The pinned Magic/open_pdks RC export retains mutual coupling "
              "while ground capacitance increases. Physical error size and "
              "direction are unknown. C-only is not independent ground truth; "
              "RC-versus-C differences are not pure resistance effects.",
              width=54, size=16)
    figure.text(0.035, 0.232, "Open the current submission in Colab", fontsize=17, color=teal,
                weight="bold", url=facts["colab_url"])
    figure.text(0.035, 0.207, facts["notebook"], fontsize=18, color=ink,
                url=facts["notebook_url"])
    paragraph(0.035, 0.171,
              "Run all: archived evidence and waveform measurements. "
              "DRC/LVS establish structural checks, not model fidelity. "
              "Schematic results are unaffected by this extraction concern. "
              "No corrected counts, energy or silicon PVT guarantee is inferred.",
              width=47, size=16, color=muted)

    figure.text(0.36, 0.852, "2 | Schematic coverage is not free", fontsize=26, color=ink, weight="bold")
    figure.text(0.36, 0.82, "Same local calibration; 1 ns; sampled |input| >= 1 mV; +4% branch-width stress",
                fontsize=16, color=muted)
    cmap = plt.get_cmap("cividis")
    frame = evidence["frame"]
    scored = frame[(frame.policy == "local_boundary") & (frame.deadline_ns == 1)
                   & (frame.input_mv.abs() >= 1) & (frame.pair_skew == 0.04)].copy()
    scored["correct"] = scored.outcome == "correct"
    for row, design in enumerate(("baseline", schematic["selected"])):
        for column, corner in enumerate(CORNERS):
            ax = figure.add_axes([0.403 + 0.112 * column, 0.665 - 0.164 * row, 0.09, 0.115])
            part = scored[(scored.design_name == design) & (scored.corner == corner)]
            table = part.groupby(["temperature_c", "vdd_v"]).correct.mean().unstack().reindex(
                index=[-40, 27, 125], columns=[1.62, 1.8, 1.95],
            )
            if table.isna().any().any():
                raise RuntimeError("A published schematic PVT panel is missing")
            ax.imshow(table.values, cmap=cmap, vmin=0, vmax=1, aspect="auto")
            for y in range(3):
                for x in range(3):
                    ax.text(x, y, f"{100 * table.values[y, x]:.0f}", ha="center", va="center",
                            fontsize=17, color=contrast_ink(cmap(table.values[y, x])))
            ax.set_title(corner.upper(), fontsize=18, weight="bold")
            ax.set_xticks(range(3), ["1.62", "1.80", "1.95"], fontsize=13)
            ax.set_yticks(range(3), ["-40", "27", "125"] if column == 0 else ["", "", ""], fontsize=13)
            if column == 0:
                ax.set_ylabel(("Original" if row == 0 else "Selected") + "\nTemp. (C)", fontsize=14)
            if row == 1:
                ax.set_xlabel("VDD (V)", fontsize=14)
    figure.text(0.36, 0.443,
                f"All 49 conditions: {100 * original_fraction:.1f}% -> {100 * selected_fraction:.1f}% correct"
                f"  |  {schematic['original_mean_core_energy_fj']:.1f} -> "
                f"{schematic['selected_mean_core_energy_fj']:.1f} fJ/cycle",
                fontsize=18, color=teal, weight="bold")
    figure.text(0.36, 0.420,
                "Above: 45 PVT combinations; aggregate also includes four nominal stress controls. Percentages are grid coverage, not yield.",
                fontsize=12, color=muted)

    figure.text(0.36, 0.375, "3 | Structural checks and archived-deck outcomes", fontsize=26, color=ink, weight="bold")
    ax = figure.add_axes([0.36, 0.273, 0.61, 0.079])
    layers = physical.gds_polygons((layout["snapshot"] / "atlas.gds").read_bytes())
    colors = {(65, 20): "#6bb58e", (66, 20): "#dd7783", (68, 20): "#aeb3d5",
              (69, 20): "#50b5ca", (70, 20): "#198f83", (71, 20): "#d4a343"}
    for layer, polygons in sorted(layers.items()):
        ax.add_collection(PatchCollection([Polygon(points, closed=True) for points in polygons],
                                         facecolor=colors.get(layer, "#d6d7df"), edgecolor="none", alpha=0.8))
    bounds = layout["receipt"]["geometry"]["bbox"]["bounds_um"]
    ax.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]))
    ax.set_aspect("equal")
    ax.axis("off")
    figure.text(0.36, 0.246,
                f"Actual 27-device GDS | DRC 0 + LVS / negative controls | {extracted['bbox_um2']:.3f} um2",
                fontsize=16, color=teal, weight="bold")
    figure.text(0.36, 0.213,
                f"Archived 45-PVT RC: {full['rc_correct_1ns']}/180 at 1 ns"
                f"  |  {full['rc_correct_2ns']}/180 at declared 2 ns",
                fontsize=20, color=ink, weight="bold")
    paragraph(0.36, 0.184,
              f"Worst sampled RC decision: {full['worst_rc_delay_ns']:.3f} ns at FS / 1.62 V / -40 C / -3 mV. "
              "Four signed inputs per condition; 24 unresolved at 1 ns. "
              "Separate ngspice-42 pilot: 12/20 at failed original 1 ns; 20/20 at post-hoc 2 ns. "
              "No continuous-input or statistical-yield guarantee.",
              width=115, size=14, color=muted)
    figure.text(0.36, 0.126,
                "Matched 180-point mean core energy, same ngspice-47 conditions:",
                fontsize=17, color=ink, weight="bold")
    figure.text(0.36, 0.101,
                f"Schematic: {full['mean_schematic_energy_fj']:.1f} fJ"
                f"  |  Extracted RC: {full['mean_rc_energy_fj']:.1f} fJ",
                fontsize=19, color=teal)
    figure.text(0.035, 0.061,
                RC_MODEL_LABEL + ". Core energy excludes external drivers and calibration infrastructure.",
                fontsize=15, color=ink)
    figure.text(0.035, 0.038,
                "Established circuitry: Razavi, 2015, DOI 10.1109/MSSC.2015.2418155; Li, Xu & Iizuka, 2022, DOI 10.1007/s10470-022-01992-6.",
                fontsize=12, color=muted)
    figure.text(0.035, 0.019,
                "Original code: MIT. SKY130 keeps Apache-2.0. GitHub Copilot assistance disclosed. "
                "Source, models and reproduction instructions are linked in the notebook.",
                fontsize=12, color=muted)

    pdf, preview = OUTPUT / "Comparator_Atlas_Poster.pdf", OUTPUT / "poster_preview.png"
    figure.savefig(pdf, metadata={
        "Title": facts["title"], "Subject": "Code-a-Chip schematic-to-layout characterization",
        "Author": author["name"], "CreationDate": None, "ModDate": None,
    })
    figure.savefig(preview, dpi=100)
    plt.close(figure)
    abstract = (
        f"{facts['title']}\n{author['name']} - {author['affiliation']}\n\n"
        "Comparator Atlas is an open-source, notebook-driven study of when a regenerative "
        "comparator produces a correct decision before a deadline. It connects a declared "
        "nine-candidate SKY130 design search, a lower-energy comparison, numerical refinement "
        "and a real physical-layout flow. On the 49-condition schematic grid at 1 ns with "
        "sampled absolute input at least 1 mV, the same local calibration policy gives "
        f"{schematic['baseline_correct_at_1mv']}/{schematic['points_at_1mv']} original versus "
        f"{schematic['selected_correct_at_1mv']}/{schematic['points_at_1mv']} selected correct points, "
        f"at {schematic['original_mean_core_energy_fj']:.2f} and "
        f"{schematic['selected_mean_core_energy_fj']:.2f} fJ core energy. Actual GDS, DRC/LVS "
        "negative controls and distributed RC extraction connect that schematic study to "
        "a physical implementation. A separately declared full-grid study evaluates the "
        "nominal, code-zero schematic and RC circuits over 45 PVT conditions "
        f"and four signed inputs each. All {full['points_per_mode']} RC samples meet the 2 ns primary "
        f"deadline; {full['rc_correct_1ns']} meet 1 ns, with the rest unresolved. The worst RC decision "
        f"is {full['worst_rc_delay_ns']:.3f} ns at FS/1.62 V/-40 C/-3 mV. Both modes use ngspice 47 "
        "with all 360 pointwise 10/5 ps comparisons confirmed. Mean full-grid core energy is "
        f"{full['mean_schematic_energy_fj']:.2f} fJ schematic versus {full['mean_rc_energy_fj']:.2f} fJ "
        "RC for those archived decks, not a qualified physical parasitic-cost estimate. "
        "The earlier failed 1 ns pilot remains recorded separately. Source-bound tables, "
        "retained waveforms, vector figures and an interactive decision explorer support "
        "inspection and reuse. Results are deterministic sampled simulations, not silicon "
        "measurements, foundry yield or a continuous input-range guarantee; core energy "
        "excludes external drivers and calibration infrastructure.\n\n" + RC_MODEL_NOTICE + "\n"
    )
    abstract_path = OUTPUT / "abstract.txt"
    abstract_path.write_text(abstract, encoding="utf-8")
    manifest = {
        "status": "current_competition_materials_from_verified_evidence",
        "generator_sha256": sha256(Path(__file__)),
        "release_facts_source_sha256": sha256(ROOT / "presentation" / "release_facts.py"),
        "facts": facts,
        "data_evidence_sha256": facts["evidence_sha256"],
        "validation_manifest_sha256": sha256(OUTPUT / "validation_manifest.json"),
        "stress_manifest_sha256": sha256(OUTPUT / "stress_manifest.json"),
        "layout_receipt_sha256": physical.RECEIPT_SHA256,
        "artifact_sha256": {path.name: sha256(path) for path in (pdf, preview, abstract_path)},
        "reviewer_guide_sha256": sha256(guide),
        "public_upload_performed": False,
        "new_physical_experiments": 0,
    }
    (OUTPUT / "poster_manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8",
    )
    print(f"Generated the current schematic-to-layout poster, abstract and reviewer guide: {pdf.name}")
    return pdf


if __name__ == "__main__":
    build()
