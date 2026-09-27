"""One checked set of contest facts for the README, poster and reviewer guide."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import entry_tools as entry
import layout_evidence as physical
from presentation import pvt45_results

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "ISSCC27/submitted_notebooks/comparator_atlas"
BRANCH = "wlhsu0827-comparator-atlas-isscc27"
FORK = "WLHsu0827/sscs-ose-code-a-chip.github.io"
NOTEBOOK = "Comparator_Atlas.ipynb"
PR_URL = "https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/pull/195"
NOTEBOOK_URL = f"https://github.com/{FORK}/blob/{BRANCH}/{PREFIX}/{NOTEBOOK}"
COLAB_URL = f"https://colab.research.google.com/github/{FORK}/blob/{BRANCH}/{PREFIX}/{NOTEBOOK}"
TREE_URL = f"https://github.com/{FORK}/tree/{BRANCH}/{PREFIX}"


def load_facts() -> dict:
    schematic = entry.load_evidence()
    layout = physical.load_layout()
    pvt45 = pvt45_results.load_results()
    full_table = pvt45_results.comparison_table(pvt45["frame"]).set_index("implementation")
    metadata = schematic["metadata"]
    narrow = entry.summary(schematic, minimum_mv=1.0)
    wide = entry.summary(schematic, minimum_mv=3.0)
    rc_summary = physical.deadline_summary(layout).set_index(["mode", "deadline_ns"])
    costs = physical.matched_tt_comparison(layout).set_index("implementation")
    selected = schematic["selection"]["selected_design"]
    old = costs.loc["Previous balanced RC"]
    repaired = costs.loc["Repaired Distributed RC"]
    ideal = costs.loc["Schematic"]
    return {
        "authors": metadata["authors"],
        "title": metadata["title"],
        "notebook": NOTEBOOK,
        "notebook_url": NOTEBOOK_URL,
        "colab_url": COLAB_URL,
        "source_tree_url": TREE_URL,
        "pull_request_url": PR_URL,
        "rc_model_applicability": {
            **metadata["rc_model_applicability"],
            "notice": pvt45_results.RC_MODEL_NOTICE,
        },
        "schematic": {
            "condition_count": 49,
            "primary_deadline_ns": 1.0,
            "policy": "local_boundary",
            "selected": selected,
            "baseline_correct_at_1mv": int(narrow.loc["baseline", "correct"]),
            "selected_correct_at_1mv": int(narrow.loc[selected, "correct"]),
            "points_at_1mv": int(narrow.loc[selected, "points"]),
            "selected_correct_at_3mv": int(wide.loc[selected, "correct"]),
            "points_at_3mv": int(wide.loc[selected, "points"]),
            "original_mean_core_energy_fj": float(narrow.loc["baseline", "mean_core_energy_fj"]),
            "selected_mean_core_energy_fj": float(narrow.loc[selected, "mean_core_energy_fj"]),
            "efficient_control_correct_at_1mv": int(narrow.loc["lvt_base_3b", "correct"]),
            "efficient_control_energy_fj": float(narrow.loc["lvt_base_3b", "mean_core_energy_fj"]),
        },
        "layout": {
            "scope": "original_five_condition_pilot",
            "simulator": "ngspice-42",
            "nominal_geometry": True,
            "trim_code": 0,
            "condition_count": len(layout["receipt"]["protocol"]["sampled_conditions"]),
            "rc_sampled_points": int(rc_summary.loc[("Distributed RC", 1), "sampled_points"]),
            "rc_correct_1ns": int(rc_summary.loc[("Distributed RC", 1), "correct"]),
            "rc_unresolved_1ns": int(rc_summary.loc[("Distributed RC", 1), "unresolved"]),
            "rc_correct_posthoc_2ns": int(rc_summary.loc[("Distributed RC", 2), "correct"]),
            "structural_checks": layout["receipt"]["physical"]["pass"],
            "drc_errors": layout["receipt"]["physical"]["full_named_drc_errors"],
            "bbox_um2": layout["receipt"]["geometry"]["bbox"]["bbox_area_um2"],
            "previous_legal_rc_delay_ns": float(old.mean_delay_ns),
            "repaired_rc_delay_ns": float(repaired.mean_delay_ns),
            "previous_legal_rc_energy_fj": float(old.mean_core_energy_fj),
            "repaired_rc_energy_fj": float(repaired.mean_core_energy_fj),
            "matched_schematic_energy_fj": float(ideal.mean_core_energy_fj),
            "delay_reduction_percent": float(100 * (1 - repaired.mean_delay_ns / old.mean_delay_ns)),
            "energy_reduction_percent": float(100 * (1 - repaired.mean_core_energy_fj / old.mean_core_energy_fj)),
            "original_1ns_pilot_qualified": False,
            "pilot_full_45_condition_extracted_sweep_performed": False,
            "posthoc_2ns_is_new_qualification": False,
            "physical_run_url": layout["receipt"]["run"]["run_url"],
            "physical_run_conclusion": "failure_at_original_1ns_performance_gate",
        },
        "postlayout_pvt45": {
            "scope": "subsequent_separately_declared_full_grid_study",
            "full_45_condition_extracted_sweep_performed": True,
            "conditions": 45,
            "points_per_mode": 180,
            "primary_deadline_ns": 2,
            "parallel_deadline_ns": 1,
            "rc_correct_1ns": int(full_table.loc["Extracted RC", "correct_at_1ns"]),
            "rc_correct_2ns": int(full_table.loc["Extracted RC", "correct_at_2ns"]),
            "rc_unresolved_1ns": 24,
            "mean_schematic_energy_fj": float(full_table.loc["Schematic", "mean_core_energy_fj"]),
            "mean_rc_energy_fj": float(full_table.loc["Extracted RC", "mean_core_energy_fj"]),
            "worst_rc_delay_ns": float(full_table.loc["Extracted RC", "worst_delay_ns_at_2ns"]),
            "worst_rc_condition": pvt45["summary"]["matched_statistics"]["observed_worst_point"],
            "mean_per_point_energy_overhead_percent":
                pvt45["summary"]["matched_statistics"]["mean_per_point_energy_overhead_percent"],
            "nominal_geometry": True,
            "trim_code": 0,
            "simulator": "ngspice-47",
            "actual_transients": 720,
            "all_360_numerical_histories_qualified": True,
            "previously_observed_conditions": 5,
            "new_postlayout_conditions": 40,
            "blinded_external_test": False,
            "old_five_condition_1ns_gate_reinterpreted": False,
        },
        "limits": [
            pvt45_results.RC_MODEL_NOTICE,
            "The calibrated schematic 49-condition study, original ngspice-42 five-condition pilot, "
            "and subsequent ngspice-47 full-grid study are separate experiments.",
            "The original ngspice-42 pilot has twenty RC points, not eighty independent RC tests; "
            "that pilot did not perform a full 45-condition extracted sweep. The subsequent separately "
            "declared ngspice-47 study completed 45 conditions and 180 RC points.",
            "Only the original ngspice-42 pilot's 2 ns result is post-hoc; its 1 ns gate remains failed. "
            "The subsequent ngspice-47 study has a prospectively declared 2 ns primary deadline "
            "(180/180 RC correct), with parallel 1 ns results (156/180 RC correct).",
            "Core energy excludes external drivers and calibration infrastructure.",
            "No silicon measurement, foundry signoff, yield, continuous-input guarantee or global optimum is claimed.",
            "A submitted PR is not acceptance, a rank or an award.",
        ],
        "evidence_sha256": {
            "entry_metadata.json": entry.digest(ROOT / "entry_metadata.json"),
            "results/study/selection.json": entry.digest(entry.STUDY / "selection.json"),
            "results/study/verified_measurements.csv": entry.digest(entry.STUDY / "verified_measurements.csv"),
            "results/study/professional/measurements.csv": entry.digest(
                entry.STUDY / "professional" / "measurements.csv"
            ),
            "layout_compact_repair/verification-receipt.json": physical.RECEIPT_SHA256,
            **{
                f"results/study/postlayout_pvt45/{name}": expected
                for name, expected in pvt45_results.REFERENCE_FILES.items()
            },
        },
    }


def readme_text(facts: dict, design_table: str) -> str:
    layout = facts["layout"]
    full = facts["postlayout_pvt45"]
    return f"""# Comparator Atlas: When Calibration Is Not Enough

**Wei-Lun Hsu — National Tsing Hua University**  
IEEE SSCS Code-a-Chip · ISSCC 2027 · MIT License

[Notebook]({facts["notebook_url"]}) |
[Run in Colab]({facts["colab_url"]}) |
[Reproduction instructions](REPRODUCIBILITY.md)

Download the [interactive report](results/study/report.html) and open the
HTML file locally; GitHub's file viewer does not execute its JavaScript.
The Waveform Lab provides eight recorded
examples with a deadline cursor and complementary-rail thresholds.
View or download the [poster PDF](results/study/Comparator_Atlas_Poster.pdf)
or its [preview image](results/study/poster_preview.png).

## Overview

Offset calibration alone does not ensure that a comparator finishes its
decision in time. This notebook follows a SKY130 StrongARM comparator from
device sizing and calibration through PVT evaluation, layout and parasitic
extraction. Interactive waveforms explain the difference between a wrong
decision and an unresolved one.

The workflow includes a nine-candidate design comparison, an additional
lower-energy control, and a physical implementation of the selected
27-transistor circuit.

## Results

**{pvt45_results.RC_MODEL_LABEL}.**
{facts["rc_model_applicability"]["notice"]}
See [the model-applicability evidence](REPRODUCIBILITY.md#archived-rc-model-applicability).

The schematic comparison uses the same local calibration policy, a 1 ns
deadline and sampled absolute inputs of at least 1 mV:

{design_table}

These are finite-grid results: 45 PVT combinations at controlled width
stress plus four nominal controls. The lower-energy candidate was evaluated
after the original selection.

The physical implementation passes the recorded DRC/LVS and negative controls.
Its full nominal, code-zero study covers **45 PVT conditions and four signed
inputs per condition**. Schematic and extracted RC were simulated under the
same ngspice-47 settings and checked at 10/5 ps.

| Nominal full-grid result | Schematic | Extracted RC |
| --- | ---: | ---: |
| Correct at 1 ns | 180/180 | {full["rc_correct_1ns"]}/180 |
| Correct at the declared 2 ns deadline | 180/180 | {full["rc_correct_2ns"]}/180 |
| Mean core energy (fJ/cycle) | {full["mean_schematic_energy_fj"]:.2f} | {full["mean_rc_energy_fj"]:.2f} |

The slowest RC sample is **{full["worst_rc_delay_ns"]:.3f} ns at FS / 1.62 V /
-40 C / -3 mV**. The 24 remaining 1 ns points are unresolved, not wrong.
The earlier five-condition ngspice-42 layout pilot remains a separate record:
12/20 RC points met its original 1 ns target; 20/20 met a retained 2 ns window.
The full-grid 2 ns criterion was declared separately rather than rewriting that
pilot's result.

![Full post-layout PVT timing](results/study/postlayout_pvt45/figures/pvt45_timing.png)

Each cell is the maximum over four signed inputs. Black outlines mark
conditions with a missed 1 ns sample. [Vector PDF](results/study/postlayout_pvt45/figures/pvt45_timing.pdf).

## Run

Open the notebook in Colab and run all cells, or run locally:

```text
python -m pip install -r requirements-review.txt
python -m pytest --nbmake --nbmake-timeout=600 Comparator_Atlas.ipynb
```

Default execution analyzes the supplied data and remeasures saved waveforms.
Fresh SPICE examples and the full campaign are optional notebook modes.
The Colab link uses the submitted fork before upstream merge.
The project requires no commercial EDA license or paid API key.
Local CPU execution is supported; Colab's free tier has resource limits.

## Files

- `Comparator_Atlas.ipynb` — circuit, methods, plots and discussion.
- `comparator_atlas/` — simulation, calibration and analysis code.
- `results/study/` — measurements, figures, report, poster and abstract.
- `layout_compact_repair/` — final layout, extraction and physical evidence.
- `REPRODUCIBILITY.md` — tool versions, data map and complete run commands.

## Scope

The calibrated schematic and nominal-layout experiments have different scopes.
Full-grid layout inputs are limited to -10, -3, +3 and +10 mV at code zero;
five conditions had been observed previously, and this is not a blinded test.
Core energy excludes external drivers and calibration infrastructure.
The results are deterministic simulations, not silicon measurements or
foundry statistical yield. References and detailed conditions are in the
notebook.

## License and acknowledgment

Original code is [MIT licensed](LICENSE). Third-party notices are retained
in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
GitHub Copilot assisted implementation, experiment automation, figures and
documentation; the author is responsible for the work.
"""


def write_judge_guide(facts: dict) -> Path:
    schematic, layout = facts["schematic"], facts["layout"]
    full = facts["postlayout_pvt45"]
    text = f"""# Comparator Atlas - quick tour

**Wei-Lun Hsu - National Tsing Hua University**

[Notebook]({facts["notebook_url"]}) |
[Run in Colab]({facts["colab_url"]}) |
[Setup and data](REPRODUCIBILITY.md)

Download the [interactive report](results/study/report.html) and open the
HTML file locally; GitHub's file viewer does not execute its JavaScript.
View or download the [poster PDF](results/study/Comparator_Atlas_Poster.pdf)
or its [preview image](results/study/poster_preview.png).

## Suggested reading order

**{pvt45_results.RC_MODEL_LABEL}.**
{facts["rc_model_applicability"]["notice"]}
See [the model-applicability evidence](REPRODUCIBILITY.md#archived-rc-model-applicability).

1. **Question and circuit.** Read the abstract and 27-transistor circuit guide.
   The work asks when a calibrated regenerative comparator reaches a correct
   decision before a finite deadline, and what physical costs are involved.
2. **Compare the complete schematic grid.** At 1 ns and sampled absolute
   input at least 1 mV, the original and selected designs have
   {schematic["baseline_correct_at_1mv"]}/{schematic["points_at_1mv"]} and
   {schematic["selected_correct_at_1mv"]}/{schematic["points_at_1mv"]} correct
   points with the same local policy. Compare the lower-energy control too;
   no design is declared best for every specification.
3. **Inspect actual layout evidence.** View the hash-checked GDS, DRC/LVS
   negative controls and matched schematic/connectivity/C/RC results.
   The full 45-condition nominal RC study gives
   {full["rc_correct_1ns"]}/{full["points_per_mode"]} correct at 1 ns and
   {full["rc_correct_2ns"]}/{full["points_per_mode"]} at its declared 2 ns
   deadline. Its worst sample is {full["worst_rc_delay_ns"]:.3f} ns at
   FS / 1.62 V / -40 C / -3 mV. The earlier five-condition pilot is retained
   separately and is not retrospectively relabeled.

The **Waveform lab** makes the distinction concrete: eight representative
saved examples have a movable deadline, complementary output thresholds and
source run identities. A wrong-sign schematic decision, its calibrated
counterpart, and late extracted RC decisions are all visible. These examples
are not every raw trace in the atlas and add no new validation coverage.
Moving the display deadline does not rerun SPICE or reduce full-cycle energy.

Run all notebook
cells to regenerate the analysis from the included data; full simulations
are separate optional modes. Detailed commands, versions and limitations are
collected in [Reproducibility](REPRODUCIBILITY.md).
"""
    destination = ROOT / "REVIEWER_GUIDE.md"
    destination.write_text(text, encoding="utf-8")
    manifest = {
        "status": "competition_guide_generated_from_checked_evidence",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "facts": facts,
        "guide_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "new_physical_simulations": 0,
        "public_upload_performed": False,
    }
    output = ROOT / "results" / "presentation" / "reviewer_guide_manifest.json"
    output.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(write_judge_guide(load_facts()))
