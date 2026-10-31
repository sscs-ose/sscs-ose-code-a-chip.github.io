#!/usr/bin/env python3
"""Build a TT held-node Stage-6 v2 diagnostic from a passing recovery run."""

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
from scripts import run_flow2_recovery as recovery  # noqa: E402
from scripts import run_flow2_stage6_v2 as stage6  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

OUTPUT = Path("results/sky130/stage6_v2")


def _verify_vectors(jobs: list[dict], cases: list) -> None:
    expected = {case.name: campaign._vectors(case) for case in cases}
    if len(jobs) != len(expected) or {job["case"] for job in jobs} != set(expected):
        raise ValueError("measured cases differ from reserved cohort")
    for job in jobs:
        if {key: job[key] for key in ("case", "activation_x2",
                                       "ternary_weights", "integer_sums")} != expected[job["case"]]:
            raise ValueError(f"measured stimulus changed: {job['case']}")


def run(root: str | Path, recovery_summary: str | Path | None = None) -> dict:
    root = Path(root).resolve()
    if recovery_summary is None:
        source_sha = campaign._sha(root / campaign.SUMMARY)
        runner_sha = campaign._sha(Path(recovery.__file__))
        recovery_summary = (recovery.OUTPUT /
                            f"source_{source_sha[:12]}_runner_{runner_sha[:12]}" /
                            "summary.json")
    path = Path(recovery_summary)
    path = path if path.is_absolute() else root / path
    path = path.resolve()
    if not path.is_relative_to((root / recovery.OUTPUT).resolve()):
        raise ValueError("recovery summary must be under its dedicated output tree")
    report = campaign._read(path)
    if (report.get("format") != "automx-cim-flow2-recovery-v1" or
            report.get("status") != "MEASURED_RECOVERY_READOUT_DIAGNOSTICS_NO_WRAPPER" or
            report.get("script_sha256") != campaign._sha(Path(recovery.__file__)) or
            report.get("sample_turnoff_start_ns") != 2.100):
        raise ValueError("passing current recovery campaign required")
    original, inputs, old_jobs, source_sha = recovery._source(root)
    if (report["source_campaign_sha256"] != source_sha or
            report["pex_sha256"] != inputs["pex_sha"] or
            report["model_sha256"] != inputs["model_sha"] or
            report["ngspice_version"] != inputs["version"]):
        raise ValueError("recovery source/provenance changed")
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    extension, validation = recovery._cohorts(config, old_jobs)
    if report.get("cohort_reservation") != {
            "training": recovery._reservation(extension),
            "validation": recovery._reservation(validation)}:
        raise ValueError("cohort reservation changed")
    for name, count in (("training_extension", 64), ("fresh_validation", 64),
                        ("pvt_smoke", 16)):
        group = report["groups"][name]
        if (group.get("completed_sims") != count or
                group.get("planned_sims") != count or len(group.get("jobs", [])) != count):
            raise ValueError(f"incomplete recovery group {name}")
        stage6._verified_jobs(root, report, name)
    added = report["groups"]["training_extension"]["jobs"]
    holdout = report["groups"]["fresh_validation"]["jobs"]
    pvt_jobs = report["groups"]["pvt_smoke"]["jobs"]
    _verify_vectors(added, recovery._phases(extension))
    _verify_vectors(holdout, recovery._phases(validation))
    training = old_jobs + added
    if any(job.get("turnoff_start_ns") != 2.100
           for job in training + holdout + pvt_jobs):
        raise ValueError("sampling time changed in measured jobs")
    decoder = campaign._train(training, recovery.BUDGET_V)
    if (not decoder["training_margin_candidate"] or
            decoder != report["groups"]["training_extension"]["analysis"] or
            decoder["frozen_decoder_sha256"] != report["frozen_decoder_sha256"]):
        raise ValueError("frozen decoder cannot be reproduced")
    checked = campaign._decode_holdout(holdout, validation, decoder, recovery.BUDGET_V)
    requirements = campaign._read(root / "configs/sky130_post49_requirements.json")
    sensitivity = campaign._sensitivity(holdout, decoder, requirements)
    if (not checked["tt_holdout_candidate"] or
            checked != report["groups"]["fresh_validation"]["analysis"] or
            sensitivity != report["offline_sensitivity"] or
            sensitivity["conclusion"] != "NO_ERRORS_AT_INJECTED_BUDGET_EXTREMES"):
        raise ValueError("fresh validation or injected-budget gate failed")
    selected = {case.name for case in campaign._pvt_cases(training, decoder)}
    reused_tt = [job for job in training if job["case"] in selected]
    if (len(reused_tt) != 8 or len(pvt_jobs) != 16 or
            {job["case"] for job in pvt_jobs} != selected or
            campaign._pvt_result(reused_tt + pvt_jobs, decoder, recovery.BUDGET_V) !=
            report["groups"]["pvt_smoke"]["analysis"] or
            report["groups"]["pvt_smoke"]["analysis"]["conclusion"] !=
            "THREE_POINT_DIAGNOSTIC_CANDIDATE"):
        raise ValueError("three-point PVT gate failed")
    base = build_characterization(root, config)
    source_recovery_sha = campaign._sha(path)
    folder = root / OUTPUT / f"recovery_{source_recovery_sha[:12]}"
    vectors = [{"case": job["case"], "phase": job["phase"],
                "activation_x2": job["activation_x2"],
                "ternary_weights": job["ternary_weights"],
                "held_differential_v": [campaign._held(job, lane)[0]
                                        for lane in range(4)]}
               for job in training]
    characterization = {
        "format": "automx-cim-stage6-held-node-characterization-v2",
        "status": "TT_HELD_NODE_DIAGNOSTIC_V2",
        "source_campaign_sha256": source_recovery_sha,
        "source_original_campaign_sha256": source_sha,
        "source_stage6_v1_physical_sha256": campaign._canonical_sha(base["physical"]),
        "config_sha256": campaign._sha(root / "configs/sky130_mha_tiny.json"),
        "pex_sha256": report["pex_sha256"],
        "model_sha256": report["model_sha256"],
        "operating_point": {"corner": "tt", "vdd_v": config.vdd,
                            "temperature_c": config.temperature_c,
                            "load_ff": 820, "sampling_turnoff_start_ns": 2.100,
                            "switch_width_um": campaign.WIDTH_UM,
                            "turnoff_fall_ps": campaign.FALL_PS,
                            "held_measure_time_ns": 2.4},
        "decoder": decoder, "training_vectors": vectors,
        "physical": base["physical"],
        "energy_delay_proxy_origin": "Stage-6 v1 passive-core proxy; readout energy/latency unmeasured",
        "limitations": "training held-voltage replay plus nominal per-level estimates; independent MHA validation gates creation but is never fitted; schematic TG/ideal control, three-point PVT smoke only; no physical ADC or wrapper",
    }
    model = HeldNodeMacroModel(characterization)
    comparison = evaluate_mha(run_stage1(config), model)
    comparison.update({
        "format": "automx-cim-stage6-mha-v2",
        "status": "DIAGNOSTIC_TT_HELD_NODE_LUT_V2",
        "source_campaign_sha256": source_recovery_sha,
        "frozen_decoder_sha256": decoder["frozen_decoder_sha256"],
        "training_pattern_invocations": model.measured_pattern_invocations,
        "nominal_level_estimate_invocations": model.estimated_pattern_invocations,
        "nominal_level_estimate_fraction": (
            model.estimated_pattern_invocations /
            max(1, model.measured_pattern_invocations + model.estimated_pattern_invocations)),
        "mha_coverage_status": ("NOMINAL_LEVEL_ESTIMATES_USED" if
                                model.estimated_pattern_invocations else
                                "ALL_PATTERNS_IN_TRAINING_SET"),
        "energy_delay_proxy_origin": characterization["energy_delay_proxy_origin"],
        "limitations": "tiny-MHA uses a TT training-only held-voltage LUT; unmeasured patterns use nominal sum-level estimates; no physical ADC, transistor noise, full PVT or wrapper sign-off",
    })
    stage6._write_once(folder / "characterization.json", characterization)
    stage6._write_once(folder / "tiny_mha_comparison.json", comparison)
    return {"status": comparison["status"],
            "characterization": str((folder / "characterization.json").relative_to(root)),
            "comparison": str((folder / "tiny_mha_comparison.json").relative_to(root)),
            "source_recovery_sha256": source_recovery_sha,
            "training_pattern_invocations": model.measured_pattern_invocations,
            "nominal_level_estimate_invocations": model.estimated_pattern_invocations}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--recovery-summary", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.recovery_summary), indent=2))
