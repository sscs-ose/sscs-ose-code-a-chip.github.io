#!/usr/bin/env python3
"""Build a gated TT 2+2 held-node LUT model and tiny-MHA diagnostic.

The model uses only held-node training voltages. Fresh MHA jobs gate its
creation but never enter its fitted LUT. Unmeasured patterns use per-level
training interval centers and are counted as estimates.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.attention import run_stage1  # noqa: E402
from automx_cim.characterization import build_characterization, evaluate_mha  # noqa: E402
from automx_cim.characterization_v2 import HeldNodeMacroModel  # noqa: E402
from automx_cim.config import Sky130MHAConfig  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

SUMMARY = campaign.SUMMARY
OUTPUT = Path("results/sky130/stage6_v2")
GROUP_COUNTS = {"broader_aperture": 40, "aperture_5ps_grid": 40,
                "held_node_training": 120, "fresh_mha_holdout": 64,
                "pvt_smoke": 16}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _require_campaign(root: Path, report: dict) -> None:
    if (report.get("format") != "automx-cim-flow2-remaining-measurements-v1" or
            report.get("status") != "MEASURED_READOUT_DIAGNOSTICS_NO_WRAPPER" or
            report.get("script_sha256") != _sha(Path(campaign.__file__))):
        raise ValueError("complete current Flow-2 readout campaign required")
    groups = report.get("groups", {})
    for name, count in GROUP_COUNTS.items():
        item = groups.get(name, {})
        if (item.get("status") != "MEASURED_TT_DIAGNOSTIC" or
                item.get("planned_sims") != count or
                item.get("completed_sims") != count or
                len(item.get("jobs", [])) != count):
            raise ValueError(f"incomplete campaign group: {name}")
    training = groups["held_node_training"]["analysis"]
    holdout = groups["fresh_mha_holdout"]["analysis"]
    pvt = groups["pvt_smoke"]["analysis"]
    if (not training.get("training_margin_candidate") or
            training.get("frozen_decoder_sha256") !=
            report.get("frozen_decoder_sha256") or
            not holdout.get("tt_holdout_candidate") or
            report.get("offline_sensitivity", {}).get("conclusion") !=
            "NO_ERRORS_AT_INJECTED_BUDGET_EXTREMES" or
            pvt.get("conclusion") != "THREE_POINT_DIAGNOSTIC_CANDIDATE" or
            report.get("selected_turnoff_start_ns") != groups[
                "aperture_5ps_grid"]["analysis"].get("selected_turnoff_start_ns")):
        raise ValueError("aperture, decoder, holdout, sensitivity or PVT gate failed")
    _, _, model, pex, _ = campaign._sources(root)
    if (report.get("model_sha256") != _sha(model) or
            report.get("pex_sha256") != _sha(pex) or
            report.get("source_refined_sha256") != _sha(
                root / campaign.REFINED /
                f"pex_{_sha(pex)[:12]}/measured.json")):
        raise ValueError("campaign PEX, model or aperture source changed")


def _verified_jobs(root: Path, report: dict, group: str) -> list[dict]:
    jobs = report["groups"][group]["jobs"]
    for item in jobs:
        deck, log, receipt = (root / item[key] for key in
                              ("deck", "log", "checkpoint"))
        if (not all(path.is_file() for path in (deck, log, receipt)) or
                _sha(deck) != item.get("deck_sha256") or
                _sha(log) != item.get("log_sha256")):
            raise ValueError(f"changed {group} deck/log: {item['case']}")
        saved = _read(receipt)
        parsed = parse_measurements(log.read_text(
            encoding="utf-8", errors="replace"), campaign._expected())
        if (saved.get("status") != "PASS" or
                saved.get("deck_sha256") != item["deck_sha256"] or
                saved.get("log_sha256") != item["log_sha256"] or
                saved.get("pex_sha256") != report["pex_sha256"] or
                saved.get("model_sha256") != report["model_sha256"] or
                saved.get("ngspice_version") != report["ngspice_version"] or
                set(parsed) != set(campaign._expected()) or
                parsed != saved.get("measurements_v") or
                parsed != item.get("measurements_v")):
            raise ValueError(f"changed {group} checkpoint: {item['case']}")
    return jobs


def _write_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if _read(path) != payload:
            raise FileExistsError(f"existing Stage-6 v2 evidence differs: {path}")
    else:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


def run(root: str | Path) -> dict:
    root = Path(root).resolve()
    summary_path = root / SUMMARY
    summary = _read(summary_path)
    _require_campaign(root, summary)
    training = _verified_jobs(root, summary, "held_node_training")
    holdout = _verified_jobs(root, summary, "fresh_mha_holdout")
    pvt = _verified_jobs(root, summary, "pvt_smoke")
    off_ns = summary["selected_turnoff_start_ns"]
    if any(job.get("turnoff_start_ns") != off_ns
           for job in training + holdout + pvt):
        raise ValueError("measured jobs do not share the frozen sampling time")
    decoder = campaign._train(training, 0.0008)
    if decoder != summary["groups"]["held_node_training"]["analysis"]:
        raise ValueError("frozen training decoder cannot be reproduced")
    config = Sky130MHAConfig.from_json(root / "configs/sky130_mha_tiny.json")
    parents = campaign._fresh_parents({"old": campaign.load_stimuli(
        root, model_sha256=summary["model_sha256"])[0]}, config,
        [campaign._case(job) for job in training])
    expected_holdout = {phase.name: campaign._vectors(phase)
                        for parent in parents for phase in campaign.split_case(
                            campaign._vectors(parent), "adjacent")}
    if ({job["case"] for job in holdout} != set(expected_holdout) or
            any({key: job[key] for key in (
                "case", "activation_x2", "ternary_weights", "integer_sums")}
                != expected_holdout[job["case"]] for job in holdout)):
        raise ValueError("fresh MHA vectors differ from reserved ranks 128..159")
    checked_holdout = campaign._decode_holdout(holdout, parents, decoder, 0.0008)
    if checked_holdout != summary["groups"]["fresh_mha_holdout"]["analysis"]:
        raise ValueError("fresh holdout analysis cannot be reproduced")
    requirements = _read(root / "configs/sky130_post49_requirements.json")
    if campaign._sensitivity(holdout, decoder, requirements) != summary[
            "offline_sensitivity"]:
        raise ValueError("sensitivity result cannot be reproduced")
    selected = {job["case"] for job in pvt}
    reused = [job for job in training if job["case"] in selected]
    if (len(reused) != 8 or campaign._pvt_result(
            reused + pvt, decoder, 0.0008) !=
            summary["groups"]["pvt_smoke"]["analysis"]):
        raise ValueError("three-corner PVT result cannot be reproduced")
    base = build_characterization(root, config)
    source_sha = _sha(summary_path)
    folder = root / OUTPUT / f"campaign_{source_sha[:12]}"
    vectors = [{"case": job["case"], "phase": job["phase"],
                "activation_x2": job["activation_x2"],
                "ternary_weights": job["ternary_weights"],
                "held_differential_v": [campaign._held(job, lane)[0]
                                        for lane in range(4)]}
               for job in training]
    characterization = {
        "format": "automx-cim-stage6-held-node-characterization-v2",
        "status": "TT_HELD_NODE_DIAGNOSTIC_V2",
        "source_campaign_sha256": source_sha,
        "source_stage6_v1_physical_sha256": campaign._canonical_sha(base["physical"]),
        "config_sha256": _sha(root / "configs/sky130_mha_tiny.json"),
        "pex_sha256": summary["pex_sha256"],
        "model_sha256": summary["model_sha256"],
        "operating_point": {"corner": "tt", "vdd_v": config.vdd,
                            "temperature_c": config.temperature_c,
                            "load_ff": 820, "sampling_turnoff_start_ns":
                                summary["selected_turnoff_start_ns"],
                            "switch_width_um": campaign.WIDTH_UM,
                            "turnoff_fall_ps": campaign.FALL_PS,
                            "held_measure_time_ns": 2.4},
        "decoder": decoder, "training_vectors": vectors,
        "physical": base["physical"],
        "energy_delay_proxy_origin": "Stage-6 v1 passive-core characterization; readout energy/latency unmeasured",
        "limitations": "training-voltage replay and per-level nominal estimates; unmeasured tiny-MHA patterns are not electrical simulations; schematic TG/ideal control, three-point PVT smoke only; no physical ADC or wrapper",
    }
    model = HeldNodeMacroModel(characterization)
    comparison = evaluate_mha(run_stage1(config), model)
    comparison.update({
        "format": "automx-cim-stage6-mha-v2",
        "status": "DIAGNOSTIC_TT_HELD_NODE_LUT_V2",
        "source_campaign_sha256": source_sha,
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
        "energy_delay_proxy_origin": characterization["energy_delay_proxy_origin"],
        "limitations": "tiny-MHA uses a training-only held-voltage LUT; unmeasured patterns use nominal sum-level voltages, so numerical agreement is not independent analog/ADC validation; physical noise, full PVT and wrapper remain unmeasured",
    })
    _write_once(folder / "characterization.json", characterization)
    _write_once(folder / "tiny_mha_comparison.json", comparison)
    return {"status": comparison["status"],
            "characterization": str((folder / "characterization.json").relative_to(root)),
            "comparison": str((folder / "tiny_mha_comparison.json").relative_to(root)),
            "source_campaign_sha256": source_sha,
            "training_pattern_invocations": model.measured_pattern_invocations,
            "nominal_level_estimate_invocations": model.estimated_pattern_invocations}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.root), indent=2))
