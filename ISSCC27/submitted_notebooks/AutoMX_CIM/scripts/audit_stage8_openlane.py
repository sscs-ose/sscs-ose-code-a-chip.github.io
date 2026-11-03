"""Fail-closed audit of an OpenLane-1 macro-bound run after physical sign-off."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_stage8_prototype_gds import _gds_hierarchy, _gds_reaches

TOP = "automx_cim_tile_controller"
RUNS = Path("openlane") / TOP / "runs"
METRIC_CHECKS = ("Magic_violations", "klayout_violations", "lvs_total_errors",
                 "tritonRoute_violations")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _metrics(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError("OpenLane metrics.csv must contain exactly one data row")
    return {str(key).strip(): str(value).strip() for key, value in rows[0].items() if key}


def audit(root: Path, tag: str) -> dict[str, object]:
    root = root.resolve()
    if not tag or Path(tag).name != tag or tag in (".", ".."):
        raise ValueError("tag must be a single OpenLane run-directory name")
    run_dir = (root / RUNS / tag).resolve()
    if not run_dir.is_relative_to(root / RUNS):
        raise ValueError("OpenLane run path escapes the project")
    reasons: list[str] = []
    preflight_path = root / "results/receipts/stage8_preflight.json"
    try:
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        preflight = {}
    if preflight.get("status") != "PASS":
        reasons.append("Stage-8 preflight is not PASS")
    config = root / "openlane" / TOP / "config.json"
    if not config.is_file() or preflight.get("openlane_config_sha256") != _digest(config):
        reasons.append("OpenLane config differs from preflight")
    for field, relative in (("core_stage5_summary_sha256", "results/receipts/physical/stage5_summary.json"),
                            ("stage7_receipt_sha256", "results/receipts/stage7_regression.json"),
                            ("stage7_stress_sha256", "results/receipts/stage7_stress.json"),
                            ("stage7_2p2_sha256", "results/receipts/stage7_2p2_regression.json"),
                            ("wrapper_signoff_sha256", "results/receipts/wrapper_signoff.json")):
        source = root / relative
        if not source.is_file() or preflight.get(field) != _digest(source):
            reasons.append(f"{relative} differs from preflight")
    if set(preflight.get("view_sha256", {})) != {"gds", "lef", "lib", "spef"}:
        reasons.append("preflight does not bind all four wrapper views")
    for name, digest in preflight.get("view_sha256", {}).items():
        view = root / f"physical/sky130/wrapper/automx_ternary_cim_4x4.{name}"
        if not view.is_file() or _digest(view) != digest:
            reasons.append(f"wrapper {name} view differs from preflight")
    files = {"gds": run_dir / f"results/final/gds/{TOP}.gds",
             "def": run_dir / f"results/final/def/{TOP}.def",
             "netlist": run_dir / f"results/final/verilog/{TOP}.v",
             "metrics": run_dir / "reports/metrics.csv",
             "manufacturability": run_dir / "reports/manufacturability.rpt"}
    for name, path in files.items():
        if not path.is_file() or not path.stat().st_size:
            reasons.append(f"OpenLane {name} artifact missing or empty: {path.relative_to(root)}")
    if files["gds"].is_file() and files["gds"].stat().st_size:
        try:
            hierarchy = _gds_hierarchy(files["gds"])
        except (OSError, UnicodeError, ValueError) as error:
            reasons.append(f"OpenLane final GDS invalid: {error}")
        else:
            for name in (TOP, "automx_ternary_cim_4x4", "automx_ternary_cim_4x4_core"):
                if name not in hierarchy:
                    reasons.append(f"OpenLane final GDS lacks {name} structure")
            if not _gds_reaches(hierarchy, TOP, "automx_ternary_cim_4x4"):
                reasons.append("OpenLane final GDS top does not reference wrapper macro")
            if not _gds_reaches(hierarchy, TOP, "automx_ternary_cim_4x4_core"):
                reasons.append("OpenLane final GDS top does not reach passive core")
            if not _gds_reaches(hierarchy, "automx_ternary_cim_4x4",
                                "automx_ternary_cim_4x4_core"):
                reasons.append("OpenLane final GDS wrapper does not reference passive core")
    data: dict[str, str] = {}
    if files["metrics"].is_file() and files["metrics"].stat().st_size:
        try:
            data = _metrics(files["metrics"])
        except (OSError, ValueError) as error:
            reasons.append(f"OpenLane metrics invalid: {error}")
    if data:
        if data.get("flow_status", "").lower().replace(" ", "_") != "flow_completed":
            reasons.append("OpenLane flow_status is not flow_completed")
        for key in METRIC_CHECKS:
            try:
                value = float(data[key])
            except (KeyError, ValueError):
                reasons.append(f"OpenLane metric {key} missing or nonnumeric")
            else:
                if not math.isfinite(value) or value != 0:
                    reasons.append(f"OpenLane metric {key} is not zero: {value}")
        for key in ("spef_wns", "spef_tns"):
            try:
                value = float(data[key])
            except (KeyError, ValueError):
                reasons.append(f"OpenLane timing metric {key} missing or nonnumeric")
            else:
                if not math.isfinite(value) or value < 0:
                    reasons.append(f"OpenLane timing metric {key} is negative or nonfinite: {value}")
        try:
            area = float(data["CoreArea_um^2"])
        except (KeyError, ValueError):
            reasons.append("OpenLane CoreArea_um^2 missing or nonnumeric")
        else:
            if not math.isfinite(area) or area <= 0:
                reasons.append("OpenLane CoreArea_um^2 must be positive")
        for key in ("power_typical_internal_uW", "power_typical_switching_uW",
                    "power_typical_leakage_uW"):
            try:
                power = float(data[key])
            except (KeyError, ValueError):
                reasons.append(f"OpenLane power metric {key} missing or nonnumeric")
            else:
                if not math.isfinite(power) or power < 0:
                    reasons.append(f"OpenLane power metric {key} invalid: {power}")
        try:
            critical_path = float(data["critical_path_ns"])
        except (KeyError, ValueError):
            reasons.append("OpenLane critical_path_ns missing or nonnumeric")
        else:
            if not math.isfinite(critical_path) or critical_path <= 0:
                reasons.append("OpenLane critical_path_ns must be positive")
    receipt = {"format": "automx-cim-stage8-openlane-audit-v1",
               "status": "PASS_IMPLEMENTATION_ESTIMATE" if not reasons else "BLOCKED",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "scope": "SKY130 implementation estimate, not measured silicon",
               "tag": tag, "run_dir": str(run_dir), "reasons": reasons,
               "preflight_sha256": _digest(preflight_path) if preflight_path.is_file() else None,
               "artifacts": {name: {"path": str(path.relative_to(root)), "sha256": _digest(path)}
                             for name, path in files.items() if path.is_file() and path.stat().st_size},
               "metrics": {key: data.get(key) for key in
                           ("flow_status", *METRIC_CHECKS, "spef_wns", "spef_tns",
                            "CoreArea_um^2", "critical_path_ns", "power_typical_internal_uW",
                            "power_typical_switching_uW", "power_typical_leakage_uW")}}
    target = root / "results/receipts/stage8_final_audit.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    result = audit(args.root, args.tag)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "PASS_IMPLEMENTATION_ESTIMATE":
        raise SystemExit(1)
