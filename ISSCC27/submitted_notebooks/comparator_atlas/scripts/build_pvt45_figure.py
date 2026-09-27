"""Export the verified full-grid result at its actual two-column publication size."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
from presentation.figure_style import FigureProfile, export_figure
from presentation.pvt45_results import (
    DATA, REFERENCE_FILES, RC_MODEL_NOTICE, case_table, load_results, review_examples, timing_figure,
    tradeoff_figure, worst_case_figure,
)

DATA_SHA256 = "0710979ebc65c955a8d7071e5704e51a34ef9c03993ebe9138c7461d6856d9ca"
AUDIT_SHA256 = "5f1c3b7284d990a4e1296a0662e0a195e5f27a5987bcb10b3b5b01d911840a39"
REVIEW = DATA


def main() -> None:
    data_path = REVIEW / "measurements.csv"
    audit_path = REVIEW / "independent-audit.json"
    if hashlib.sha256(data_path.read_bytes()).hexdigest() != DATA_SHA256 \
            or hashlib.sha256(audit_path.read_bytes()).hexdigest() != AUDIT_SHA256:
        raise RuntimeError("Figure input or its independent audit changed")
    data = load_results()
    frame, result = data["frame"], data["summary"]
    reviewed_examples = review_examples(data)
    if len(reviewed_examples) != 20:
        raise RuntimeError("The ten representative traces have not been independently remeasured")
    cases = case_table(frame)
    marked_conditions = int(cases.rc_correct_1ns.lt(4).sum())
    figure = timing_figure(frame)
    destination = REVIEW / "figures"
    review = export_figure(figure, destination, "pvt45_timing", FigureProfile())
    plt.close(figure)
    caption = (
        "Maximum sampled decision time of the nominal, code-zero extracted RC comparator. "
        "Panels (a)-(e) show TT, SS, FF, SF and FS process corners. Each cell is the maximum "
        "over differential inputs -10, -3, +3 and +10 mV, rounded to 0.01 ns. "
        f"Black outlines mark the {marked_conditions} PVT conditions containing a missed 1 ns decision; "
        "all 180 samples meet the prospective 2 ns deadline. Each output has a 5 fF load; "
        "the clock period is 10 ns with 50 ps edges. " + RC_MODEL_NOTICE
    )
    caption_path = destination / "pvt45_timing_caption.txt"
    caption_path.write_text(caption + "\n", encoding="utf-8", newline="\n")
    captions = {
        "pvt45_timing": caption,
        "pvt45_comparison": (
            "Pointwise schematic-to-extracted-RC comparison for all 180 matched nominal, code-zero "
            "PVT/input points: (a) sampled decision time and (b) full-cycle core-VDD energy. "
            "Marker shape and color identify the process corner; dashed lines denote parity. "
            "The horizontal dotted line in (a) marks the 2 ns primary deadline. "
            "Both modes use the same ngspice-47 model, stimulus and 5 ps retained timestep. "
            + RC_MODEL_NOTICE
        ),
        "pvt45_worst_waveform": (
            "Matched schematic and extracted-RC output waveforms at the slowest sampled RC point "
            "(FS, 1.62 V, -40 deg C, -3 mV). Solid and dashed traces denote Q+ and Q-, respectively. "
            "Dotted horizontal lines mark 0.2 and 0.8 VDD; vertical lines mark 1 and 2 ns. "
            "The RC trace misses 1 ns but reaches its correct complementary rails at 1.835 ns. "
            "The waveforms are original retained ngspice-47 data, not a fitted response. "
            + RC_MODEL_NOTICE
        ),
    }
    figures = {"pvt45_timing": review}
    for name, factory, height in (
        ("pvt45_comparison", lambda: tradeoff_figure(frame), 2.90),
        ("pvt45_worst_waveform", lambda: worst_case_figure(data), 2.55),
    ):
        additional = factory()
        figures[name] = export_figure(additional, destination, name, FigureProfile(height_in=height))
        plt.close(additional)
        (destination / f"{name}_caption.txt").write_text(
            captions[name] + "\n", encoding="utf-8", newline="\n",
        )
    manifest = {
        "status": "publication_style_local_figure_from_verified_measurements",
        "source_csv_sha256": DATA_SHA256,
        "independent_audit_sha256": AUDIT_SHA256,
        "figure_code_sha256": hashlib.sha256((ROOT / "presentation" / "pvt45_results.py").read_bytes()).hexdigest(),
        "style_code_sha256": hashlib.sha256((ROOT / "presentation" / "figure_style.py").read_bytes()).hexdigest(),
        "figure": review,
        "figures": figures,
        "caption": caption,
        "caption_sha256": hashlib.sha256(caption_path.read_bytes()).hexdigest(),
        "data_cells": cases[[
            "corner", "vdd_v", "temperature_c", "max_correct_rc_delay_ns", "rc_correct_1ns",
        ]].to_dict("records"),
        "secondary_deadline_outline_count": marked_conditions,
        "primary_correct": result["rc_primary_correct"],
        "minimum_sampled_primary_headroom_ns": 2 - result["matched_statistics"]["observed_max_rc_delay_ns"],
        "figure_scope": "Fixed sampled conditions, not a continuous-input or statistical-yield guarantee. "
        + RC_MODEL_NOTICE,
        "new_physical_simulations": 0,
        "public_upload_performed": False,
        "source_artifact_sha256": REFERENCE_FILES,
        "caption_sha256_by_figure": {
            name: hashlib.sha256((destination / f"{name}_caption.txt").read_bytes()).hexdigest()
            for name in figures
        },
        "independently_remeasured_representative_traces": 10,
    }
    (destination / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n",
    )
    print(f"Created three vector PDF/SVG and original {FigureProfile().png_dpi}-dpi PNG figures at 7.16-inch width.")
    print(f"Annotated {len(cases)} actual PVT cells; {marked_conditions} secondary-deadline outlines.")
    print("The figure caption is separate from the artwork.")


if __name__ == "__main__":
    main()
