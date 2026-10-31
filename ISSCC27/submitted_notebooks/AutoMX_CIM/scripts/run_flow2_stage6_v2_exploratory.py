#!/usr/bin/env python3
"""Build a clearly labeled Stage-6 v2 prototype after CM-blocked PVT smoke.

The failed MHA validation never enters the fitted LUT. This output supports
tiny-MHA numerical exploration; it is not a readout, ADC or wrapper sign-off.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.attention import run_stage1  # noqa: E402
from automx_cim.characterization import build_characterization, evaluate_mha  # noqa: E402
from automx_cim.characterization_v2 import HeldNodeMacroModel  # noqa: E402
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402
from scripts import run_flow2_recovery_pvt_diagnostic as pvt_diag  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402

OUTPUT = Path("results/sky130/stage6_v2/exploratory")
STATUS = "TT_HELD_NODE_EXPLORATORY_CM_UNVERIFIED_V2"


def _verified_pvt(root: Path, inputs: dict, training: list[dict],
                  decoder: dict, recovery_sha: str) -> tuple[dict, str]:
    script_sha = campaign._sha(Path(pvt_diag.__file__))
    path = (root / pvt_diag.OUTPUT /
            f"recovery_{recovery_sha[:12]}_runner_{script_sha[:12]}" /
            "summary.json")
    report = campaign._read(path)
    selected = campaign._pvt_cases(training, decoder)
    selected_names = {case.name for case in selected}
    tt_jobs = [job for job in training if job["case"] in selected_names]
    if (report.get("format") != "automx-cim-flow2-recovery-pvt-diagnostic-v1" or
            report.get("status") != "MEASURED_PVT_DIAGNOSTIC_CM_GATE_BLOCKED" or
            report.get("source_recovery_sha256") != recovery_sha or
            report.get("script_sha256") != script_sha or
            report.get("pex_sha256") != inputs["pex_sha"] or
            report.get("model_sha256") != inputs["model_sha"] or
            report.get("ngspice_version") != inputs["version"] or
            report.get("frozen_decoder_sha256") != decoder["frozen_decoder_sha256"] or
            report.get("selected_training_cases") != sorted(selected_names) or
            report.get("new_simulations_planned") != 16 or
            report.get("new_simulations_completed") != 16 or
            len(report.get("jobs", [])) != 16 or len(tt_jobs) != 8):
        raise ValueError("complete current 16-job PVT diagnostic required")
    fake = {"groups": {"pvt_smoke": {"jobs": report["jobs"]}},
            "pex_sha256": inputs["pex_sha"],
            "model_sha256": inputs["model_sha"],
            "ngspice_version": inputs["version"]}
    stage6._verified_jobs(root, fake, "pvt_smoke")
    pvt_jobs = report["jobs"]
    expected_vectors = {case.name: campaign._vectors(case) for case in selected}
    expected_pairs = {(name, corner) for name in selected_names
                      for corner in ("ss", "ff")}
    actual_pairs = [(job["case"], job["point"]["corner"])
                    for job in pvt_jobs]
    if (any(job.get("turnoff_start_ns") != 2.100 for job in pvt_jobs) or
            set(actual_pairs) != expected_pairs or
            len(set(actual_pairs)) != len(actual_pairs) or
            any({key: job[key] for key in ("case", "activation_x2",
                                          "ternary_weights", "integer_sums")}
                != expected_vectors[job["case"]] for job in pvt_jobs) or
            any(job["point"] != {"corner": corner, "vdd_v": 1.8,
                                  "temperature_c": 25}
                for job, (_, corner) in zip(pvt_jobs, actual_pairs)) or
            campaign._pvt_result(tt_jobs + pvt_jobs, decoder, 0.0008) !=
            report.get("pvt_analysis") or
            pvt_diag._cm_summary(tt_jobs + pvt_jobs) !=
            report.get("common_mode_by_corner")):
        raise ValueError("PVT jobs or analysis changed")
    if report["pvt_analysis"]["conclusion"] != "THREE_POINT_DIAGNOSTIC_CANDIDATE":
        raise ValueError("three-point PVT diagnostic did not meet its frozen gate")
    return report, campaign._sha(path)


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    recovery_report, inputs, training, decoder, recovery_sha = pvt_diag._source(root)
    pvt_report, pvt_sha = _verified_pvt(root, inputs, training,
                                        decoder, recovery_sha)
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    base = build_characterization(root, config)
    vectors = [{"case": job["case"], "phase": job["phase"],
                "activation_x2": job["activation_x2"],
                "ternary_weights": job["ternary_weights"],
                "held_differential_v": [campaign._held(job, lane)[0]
                                        for lane in range(4)]}
               for job in training]
    characterization = {
        "format": "automx-cim-stage6-held-node-characterization-v2",
        "status": STATUS,
        "validation_status": recovery_report["status"],
        "validation_common_mode_outside_training_samples":
            recovery_report["groups"]["fresh_validation"]["analysis"][
                "common_mode_outside_training_samples"],
        "source_recovery_sha256": recovery_sha,
        "source_pvt_diagnostic_sha256": pvt_sha,
        "source_stage6_v1_physical_sha256": campaign._canonical_sha(base["physical"]),
        "config_sha256": campaign._sha(root / "configs/sky130_mha_tiny.json"),
        "pex_sha256": inputs["pex_sha"], "model_sha256": inputs["model_sha"],
        "operating_point": {"corner": "tt", "vdd_v": config.vdd,
                            "temperature_c": config.temperature_c,
                            "load_ff": 820, "sampling_turnoff_start_ns": 2.100,
                            "switch_width_um": campaign.WIDTH_UM,
                            "turnoff_fall_ps": campaign.FALL_PS,
                            "held_measure_time_ns": 2.4},
        "decoder": decoder, "training_vectors": vectors,
        "physical": base["physical"],
        "energy_delay_proxy_origin":
            "Stage-6 v1 passive-core proxy; readout energy/latency unmeasured",
        "limitations": "exploratory only: independent MHA validation has out-of-training common-mode samples; TT differential thresholds and 3-point schematic PVT are diagnostic; no physical ADC, switch PEX, transistor noise, full PVT or wrapper",
    }
    model = HeldNodeMacroModel(characterization)
    comparison = evaluate_mha(run_stage1(config), model)
    comparison.update({
        "format": "automx-cim-stage6-mha-v2",
        "status": "EXPLORATORY_TT_HELD_NODE_LUT_V2_CM_UNVERIFIED",
        "source_recovery_sha256": recovery_sha,
        "source_pvt_diagnostic_sha256": pvt_sha,
        "frozen_decoder_sha256": decoder["frozen_decoder_sha256"],
        "training_pattern_invocations": model.measured_pattern_invocations,
        "nominal_level_estimate_invocations": model.estimated_pattern_invocations,
        "nominal_level_estimate_fraction": (
            model.estimated_pattern_invocations /
            max(1, model.measured_pattern_invocations +
                model.estimated_pattern_invocations)),
        "mha_coverage_status": ("NOMINAL_LEVEL_ESTIMATES_USED" if
                                model.estimated_pattern_invocations else
                                "ALL_PATTERNS_IN_TRAINING_SET"),
        "validation_status": recovery_report["status"],
        "limitations": characterization["limitations"],
    })
    folder = root / OUTPUT / f"recovery_{recovery_sha[:12]}_pvt_{pvt_sha[:12]}"
    stage6._write_once(folder / "characterization.json", characterization)
    stage6._write_once(folder / "tiny_mha_comparison.json", comparison)
    return {"status": comparison["status"],
            "characterization": str((folder / "characterization.json").relative_to(root)),
            "comparison": str((folder / "tiny_mha_comparison.json").relative_to(root)),
            "source_recovery_sha256": recovery_sha,
            "source_pvt_diagnostic_sha256": pvt_sha,
            "training_pattern_invocations": model.measured_pattern_invocations,
            "nominal_level_estimate_invocations": model.estimated_pattern_invocations,
            "remaining_blocker": "physical ADC common-mode input range and new independent validation"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.root), indent=2))
