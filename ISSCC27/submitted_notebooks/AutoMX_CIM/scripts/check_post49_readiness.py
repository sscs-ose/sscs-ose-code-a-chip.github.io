"""Read-only inventory of work packages after notebook cell 4.9.

This planner never grants analog, ADC, wrapper, or Stage-8 sign-off. The
individual measurement runners and Stage-8 preflight/audit remain the gates.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automx_cim.openlane import locate_openlane_flow


def _read(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _sha(path: Path) -> str | None:
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _spec_gaps(spec: dict[str, object] | None) -> list[str]:
    if not spec or spec.get("format") != "automx-cim-post49-requirements-v1":
        return ["requirements file missing or malformed"]
    gaps = []
    for section, fields in {
        "decoder": ("architecture", "uses_common_mode", "calibration_method"),
        "timing": ("sample_time_ns", "aperture_start_ns", "aperture_end_ns", "cycle_time_ns"),
        "acceptance": ("minimum_adjacent_code_margin_v",
                       "maximum_input_referred_offset_abs_v",
                       "maximum_input_referred_noise_rms_v",
                       "maximum_decode_error_rate", "minimum_holdout_patterns",
                       "maximum_reference_threshold_error_abs_v",
                       "maximum_aperture_induced_shift_abs_v"),
        "review": ("cell49_report", "heldout_report", "approved_by", "approval_date"),
    }.items():
        data = spec.get(section, {})
        for field in fields:
            if not isinstance(data, dict) or data.get(field) is None or data.get(field) == "":
                gaps.append(f"{section}.{field}")
    timing = spec.get("timing", {})
    timing_keys = ("sample_time_ns", "aperture_start_ns", "aperture_end_ns", "cycle_time_ns")
    if isinstance(timing, dict):
        for key in timing_keys:
            value = timing.get(key)
            if value is not None and (not isinstance(value, (int, float)) or
                                      not math.isfinite(value) or value <= 0):
                gaps.append(f"timing.{key} must be a finite positive number")
        if all(isinstance(timing.get(key), (int, float)) and math.isfinite(timing[key])
               for key in timing_keys) and not (
                0 < timing["aperture_start_ns"] <= timing["sample_time_ns"] <=
                timing["aperture_end_ns"] < timing["cycle_time_ns"]):
            gaps.append("timing aperture/sample/cycle order")
    acceptance = spec.get("acceptance", {})
    if isinstance(acceptance, dict):
        for key in ("minimum_adjacent_code_margin_v",
                    "maximum_input_referred_offset_abs_v",
                    "maximum_input_referred_noise_rms_v",
                    "maximum_decode_error_rate",
                    "maximum_reference_threshold_error_abs_v",
                    "maximum_aperture_induced_shift_abs_v"):
            value = acceptance.get(key)
            if value is not None and (not isinstance(value, (int, float)) or
                                      not math.isfinite(value) or value < 0):
                gaps.append(f"acceptance.{key} must be a finite nonnegative number")
        value = acceptance.get("minimum_holdout_patterns")
        if value is not None and (not isinstance(value, int) or value < 16):
            gaps.append("acceptance.minimum_holdout_patterns must be at least 16")
        rate = acceptance.get("maximum_decode_error_rate")
        if isinstance(rate, (int, float)) and math.isfinite(rate) and rate > 1:
            gaps.append("acceptance.maximum_decode_error_rate must not exceed 1")
        budget_keys = ("minimum_adjacent_code_margin_v",
                       "maximum_input_referred_offset_abs_v",
                       "maximum_input_referred_noise_rms_v",
                       "maximum_reference_threshold_error_abs_v",
                       "maximum_aperture_induced_shift_abs_v")
        if all(isinstance(acceptance.get(key), (int, float)) and
               math.isfinite(acceptance[key]) for key in budget_keys):
            total = (acceptance["maximum_input_referred_offset_abs_v"] +
                     5 * acceptance["maximum_input_referred_noise_rms_v"] +
                     acceptance["maximum_reference_threshold_error_abs_v"] +
                     acceptance["maximum_aperture_induced_shift_abs_v"])
            if 2 * total >= acceptance["minimum_adjacent_code_margin_v"]:
                gaps.append("acceptance five-sigma error budget exceeds half adjacent gap")
    pvt = spec.get("pvt_plan", {})
    if not isinstance(pvt, dict) or not pvt.get("pdk_model_support_verified"):
        gaps.append("pvt_plan.pdk_model_support_verified")
    if not isinstance(pvt, dict) or not isinstance(pvt.get("approved_matrix"), list) or not pvt["approved_matrix"]:
        gaps.append("pvt_plan.approved_matrix")
    if spec.get("status") != "APPROVED":
        gaps.append("status=APPROVED after review")
    return gaps


def _baseline_gaps(spec: dict[str, object] | None) -> list[str]:
    """Decisions needed to freeze a prototype, separate from sign-off evidence."""
    if not spec or spec.get("format") != "automx-cim-post49-requirements-v1":
        return ["requirements file missing or malformed"]
    fields = {
        "decoder": ("architecture", "uses_common_mode", "calibration_method"),
        "timing": ("sample_time_ns", "aperture_start_ns", "aperture_end_ns", "cycle_time_ns"),
        "acceptance": ("minimum_adjacent_code_margin_v",
                       "maximum_input_referred_offset_abs_v",
                       "maximum_input_referred_noise_rms_v",
                       "maximum_decode_error_rate", "minimum_holdout_patterns",
                       "maximum_reference_threshold_error_abs_v",
                       "maximum_aperture_induced_shift_abs_v"),
    }
    gaps = []
    for section, keys in fields.items():
        data = spec.get(section)
        for key in keys:
            if not isinstance(data, dict) or data.get(key) is None or data.get(key) == "":
                gaps.append(f"{section}.{key}")
    for gap in _spec_gaps(spec):
        if gap.startswith(("timing.", "acceptance.")) and gap not in gaps:
            gaps.append(gap)
    if spec.get("status") not in ("DESIGN_BASELINE_FROZEN_UNVERIFIED", "APPROVED"):
        gaps.append("status=DESIGN_BASELINE_FROZEN_UNVERIFIED")
    return gaps


def inspect(root: str | Path) -> dict[str, object]:
    root = Path(root).resolve()
    path49 = root / "results/sky130/core_candidate_full_tt/measured.json"
    stage49 = _read(path49)
    stage5_path = root / "results/receipts/physical/stage5_summary.json"
    stage5_summary = _read(stage5_path) or {}
    stage4_manifest = _read(root / "generated/sky130/spice/stage4_manifest.json") or {}
    stage49_inputs = {
        "stage4p5_sha256": root / "results/receipts/physical/core_pex_coverage.json",
        "stage4p8_sha256": root / "results/sky130/core_candidate_pex/measured.json",
        "stage5_summary_sha256": stage5_path,
    }
    stage5_views = stage5_summary.get("views")
    pex_view = ((stage5_views.get("extracted_spice") or {})
                if isinstance(stage5_views, dict) else {})
    if isinstance(pex_view.get("path"), str):
        stage49_inputs["pex_sha256"] = Path(pex_view["path"])
    if isinstance(stage4_manifest.get("model_library"), str):
        stage49_inputs["model_sha256"] = Path(stage4_manifest["model_library"])
    stale_stage49_inputs = [name for name, path in stage49_inputs.items()
                            if stage49 and stage49.get(name) != _sha(path)]
    stage49_jobs = stage49.get("jobs") if isinstance((stage49 or {}).get("jobs"), list) else []
    stage49_stale = bool(stage49 and
                          stage49.get("status") == "MEASURED_TT_CANDIDATE_SCREEN" and
                          stale_stage49_inputs)
    stage49_measured = bool(stage49 and
                            stage49.get("status") == "MEASURED_TT_CANDIDATE_SCREEN" and
                            stage49.get("completed_sims") == 101 and
                            stage49.get("planned_sims") == 101 and
                            len(stage49_jobs) == 101 and
                            stage49.get("load_ff") == 800 and
                            stage49.get("pwm_unit_ps") == 50 and
                            not stage49.get("failures") and
                            not stale_stage49_inputs)
    stage49_partial = bool(stage49 and stage49.get("status") == "FAIL" and
                           isinstance(stage49.get("completed_sims"), int) and
                           0 < stage49["completed_sims"] < 101)
    observation = ((stage49 or {}).get("analysis") or {}).get("transfer_observation")
    ordered = stage49_measured and observation == "ORDERED_IN_MEASURED_SET"
    holdout_path = root / "results/sky130/post49_holdout_tt/measured.json"
    holdout = _read(holdout_path)
    heldout_measured = bool(holdout and
                            holdout.get("status") == "MEASURED_HOLDOUT_TT" and
                            holdout.get("stage49_sha256") == _sha(path49) and
                            holdout.get("completed_sims") == 16 and
                            holdout.get("planned_sims") == 16 and
                            not holdout.get("failures"))
    combined_observation = (((holdout or {}).get("combined_117_case_analysis") or {})
                            .get("transfer_observation"))
    spec_path = root / "configs/sky130_post49_requirements.json"
    spec = _read(spec_path)
    spec_gaps = _spec_gaps(spec)
    baseline_gaps = _baseline_gaps(spec)
    wrapper_root = root / "physical/sky130/wrapper"
    stem = "automx_ternary_cim_4x4"
    views = {extension: (wrapper_root / f"{stem}.{extension}")
             for extension in ("gds", "lef", "lib", "spef")}
    missing_views = [str(path.relative_to(root)) for path in views.values()
                     if not path.is_file() or path.stat().st_size == 0]
    signoff = _read(root / "results/receipts/wrapper_signoff.json")
    config = _read(root / "openlane/automx_cim_tile_controller/config.json") or {}
    placement = config.get("MACRO_PLACEMENT_CFG")
    placement_ready = False
    if isinstance(placement, str) and placement.startswith("dir::"):
        target = (root / "openlane/automx_cim_tile_controller" /
                  placement.removeprefix("dir::")).resolve()
        placement_ready = target.is_relative_to(root) and target.is_file()
    die_ready = bool(config.get("DIE_AREA") and config["DIE_AREA"] != "0 0 1200 1200")
    flow_ready = locate_openlane_flow() is not None
    preflight = _read(root / "results/receipts/stage8_preflight.json")
    audit = _read(root / "results/receipts/stage8_final_audit.json")
    packages = {
        "A_tt_full_and_holdout": {
            "status": ("DEFERRED_PARTIAL_TT_SCREEN" if stage49_partial else
                       "STALE_CELL_4_9" if stage49_stale else
                       "PENDING_OPTIONAL_CELL_4_9" if not stage49_measured else
                       "REDESIGN_REQUIRED" if not ordered else
                       "READY_FOR_HOLDOUT" if not heldout_measured else
                       "MEASURED_DIAGNOSTIC"),
            "cell49_transfer_observation": observation,
            "cell49_completed_sims": (stage49 or {}).get("completed_sims"),
            "cell49_failures": (stage49 or {}).get("failures", []),
            "cell49_stale_inputs": stale_stage49_inputs,
            "holdout_transfer_observation": combined_observation,
            "next": ("Proceed with Stage 7 and Stage-8 preparation; keep ADC/wrapper sign-off pending" if stage49_partial else
                     "Rerun the measured cell 4.9 to refresh its source hashes, then cell 4.10" if stage49_stale else
                     "Cell 4.9 is optional for digital-flow progress; run it before analog sign-off" if not stage49_measured else
                     "Redesign core/stimulus; do not assert static ADC decoding" if not ordered else
                     "Run cell 4.10 with RUN_POST49_HOLDOUT_TT=True" if not heldout_measured else
                     "Review held-out overlaps, zero, common-mode and aperture; extend analog evidence"),
        },
        "B_adc_pvt_requirements": {
            "status": ("SPEC_DRAFT" if baseline_gaps else
                       "DESIGN_BASELINE_FROZEN_EVIDENCE_PENDING" if spec_gaps else
                       "SPEC_APPROVED_NOT_MEASURED"),
            "missing_decisions": baseline_gaps,
            "missing_evidence_or_review": [gap for gap in spec_gaps if gap not in baseline_gaps],
            "next": ("Resolve prototype decoder/timing/budget choices" if baseline_gaps else
                     "Build and measure sense/ADC; verify continuous aperture, noise/offset, full transfer and PVT; obtain human review before APPROVED" if spec_gaps else
                     "Build and measure sense/ADC; this inventory alone is not sign-off"),
        },
        "C_clocked_wrapper": {
            "status": "PENDING_PHYSICAL_EVIDENCE" if missing_views or not signoff or signoff.get("status") != "PASS" else "EVIDENCE_PRESENT_VERIFY_WITH_STAGE8_PREFLIGHT",
            "missing_views": missing_views,
            "signoff_receipt": (signoff or {}).get("status", "MISSING"),
            "next": "Implement physical sense/ADC wrapper; obtain DRC/LVS/PEX/post-layout/STA/ADC/PVT and genuine GDS/LEF/LIB/SPEF",
        },
        "D_openlane_setup": {
            "status": "PREPARATION_INCOMPLETE" if not (placement_ready and die_ready and flow_ready) else "READY_TO_CHECK_WITH_STAGE8_PREFLIGHT",
            "placement_file_present": placement_ready,
            "die_area_nonplaceholder": die_ready,
            "flow_tcl_found": flow_ready,
            "next": "Set placement and DIE_AREA from final wrapper LEF; expose executable flow.tcl on the server",
        },
        "E_stage8_top_level": {
            "status": ("AUDIT_RECORDED_VERIFY_WITH_AUDITOR" if audit and
                       audit.get("status") == "PASS_IMPLEMENTATION_ESTIMATE" else
                       "PREFLIGHT_RECORDED_RUN_OPENLANE" if preflight and
                       preflight.get("status") == "PASS" else
                       "WAITING_FOR_PREFLIGHT_AND_AUDIT"),
            "next": "Only after cell 5.2 PASS, run scripts/run_stage8_macro_bound.sh and inspect final audit",
        },
        "F_system_claims_beyond_base_only": {
            "status": "OUTSIDE_CURRENT_SIGNOFF_SCOPE",
            "next": "If claiming a physical full-MHA accelerator, implement/verify the 66-command Q/K/V/O RTL schedule, softmax/A@V path and any hybrid correction; rerun end-to-end accuracy and PPA",
        },
    }
    return {"format": "automx-cim-post49-readiness-v1",
            "scope": "Planning inventory only; none of these statuses is a sign-off PASS",
            "packages": packages}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(inspect(args.root), indent=2))
