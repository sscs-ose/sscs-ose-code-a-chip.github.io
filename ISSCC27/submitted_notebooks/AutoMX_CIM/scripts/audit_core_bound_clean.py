"""Prepare and audit a separate antenna/fanout repair run on the Linux server.

This script does not run OpenLane. The original lvs09 config and frozen run are
kept intact; config_clean.json is selected with OpenLane's -config_file flag.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_stage8_core_bound_demo import (  # noqa: E402
    CORE, DESIGN, INPUTS, TOP, TOP_CHECK_METRICS, _gds_hierarchy,
    _gds_reaches, _pdn_ground_reasons, _sha, inspect,
)


VARIANT = DESIGN / "config_clean.json"
BASE = DESIGN / "config.json"
RECEIPT = Path("results/receipts/stage8_core_bound_clean.json")
OVERRIDES = {
    "CTS_SINK_CLUSTERING_SIZE": 8,
    "RUN_HEURISTIC_DIODE_INSERTION": 1,
    "HEURISTIC_ANTENNA_THRESHOLD": 20,
    "GPL_CELL_PADDING": 2,
    "DPL_CELL_PADDING": 2,
}
ZERO_METRICS = (*TOP_CHECK_METRICS, "pin_antenna_violations",
                "net_antenna_violations")
STA_COUNTS = ("max slew violation count", "max fanout violation count",
              "max cap violation count")
INPUT_FILES = tuple(dict.fromkeys((*INPUTS, VARIANT,
                                   Path("scripts/audit_core_bound_clean.py"))))
AUDIT_SCRIPT = "scripts/audit_core_bound_clean.py"
# clean01 was prepared with this parser. Its report numbers changed after
# heuristic diode insertion; the parser fix must not invalidate physical inputs.
CLEAN01_PREPARED_AUDIT_SHA256 = "38c75ab2e948cb293253d219ed9c1f0d7a0b4ac99016c4272645e785a3738e3d"


def _variant_reasons(root: Path) -> list[str]:
    """Keep the proven lvs09 setup except for five documented repair knobs."""
    try:
        base = json.loads((root / BASE).read_text(encoding="utf-8"))
        variant = json.loads((root / VARIANT).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"clean-run config missing or invalid: {error}"]
    expected = {**base, **OVERRIDES}
    return ([] if variant == expected else
            ["config_clean.json differs from baseline beyond the five repair knobs"])


def _snapshot(root: Path, tag: str, *, create: bool) -> list[str]:
    target = root / "build/stage8_core_bound_clean" / tag / "inputs.json"
    try:
        expected = {path.as_posix(): _sha(root / path) for path in INPUT_FILES}
    except OSError as error:
        return [f"clean-run input missing: {error}"]
    if target.is_file():
        try:
            recorded = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ["clean-run input snapshot invalid"]
        if recorded == expected:
            return []
        changed = {key for key in recorded.keys() | expected.keys()
                   if recorded.get(key) != expected.get(key)}
        if (not create and tag == "core_bound_20261008_clean01" and
                changed == {AUDIT_SCRIPT} and
                recorded.get(AUDIT_SCRIPT) == CLEAN01_PREPARED_AUDIT_SHA256):
            return []
        return ["clean-run inputs changed since the frozen snapshot"]
    if not create:
        return ["clean-run input snapshot missing; prepare before OpenLane"]
    if (root / DESIGN / "runs" / tag).exists():
        return ["OpenLane tag already exists without a frozen input snapshot"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return []


def _zero_metric_reasons(metrics: dict[str, str]) -> list[str]:
    reasons = []
    if metrics.get("flow_status", "").strip().lower() != "flow completed":
        reasons.append("OpenLane flow did not complete")
    for key in ZERO_METRICS:
        try:
            value = float(metrics[key])
        except (KeyError, ValueError):
            reasons.append(f"{key} missing or not numeric")
        else:
            if not math.isfinite(value) or value != 0:
                reasons.append(f"{key} = {metrics[key]}, expected 0")
    return reasons


def _report_counts(path: Path, labels: tuple[str, ...]) -> tuple[dict[str, int], list[str]]:
    try:
        body = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}, [f"missing report: {path.name}"]
    counts: dict[str, int] = {}
    reasons = []
    for label in labels:
        matches = re.findall(rf"(?im)^\s*{re.escape(label)}\s+(\d+)\s*$", body)
        if not matches:
            reasons.append(f"{label} missing in {path.name}")
        else:
            counts[label] = int(matches[-1])
            if counts[label] != 0:
                reasons.append(f"{label} = {counts[label]}, expected 0")
    return counts, reasons


def _unique_report(directory: Path, pattern: str) -> tuple[Path | None, list[str]]:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        return None, [f"expected exactly one {pattern} in {directory}, found {len(matches)}"]
    return matches[0], []


def _sta_reasons(run_dir: Path) -> tuple[dict[str, float | int], list[str]]:
    signoff = run_dir / "reports/signoff"
    checks, reasons = _unique_report(signoff, "*-rcx_sta.checks.rpt")
    if checks is None:
        counts = {}
    else:
        counts, count_reasons = _report_counts(checks, STA_COUNTS)
        reasons.extend(count_reasons)
    summary, summary_reasons = _unique_report(signoff, "*-rcx_sta.summary.rpt")
    reasons.extend(summary_reasons)
    if summary is None:
        return counts, reasons
    try:
        body = summary.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return counts, [*reasons, "post-route STA summary missing"]
    slacks = re.findall(r"(?im)^worst slack\s+(-?\d+(?:\.\d+)?)\s*$", body)
    if len(slacks) != 2:
        reasons.append("post-route setup/hold slack values missing")
    else:
        for label, value in zip(("setup_slack_ns", "hold_slack_ns"), slacks):
            counts[label] = float(value)
            if float(value) < 0:
                reasons.append(f"{label} is negative: {value}")
    return counts, reasons


def _arc_reasons(run_dir: Path) -> tuple[dict[str, int], list[str]]:
    log, reasons = _unique_report(run_dir / "logs/signoff", "*-arc.log")
    if log is None:
        return {}, reasons
    try:
        body = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}, ["final ARC antenna log missing"]
    counts: dict[str, int] = {}
    for label in ("net", "pin"):
        matches = re.findall(rf"Found\s+(\d+)\s+{label} violations\.", body)
        if not matches:
            reasons.append(f"ARC {label} violation count missing")
        else:
            counts[f"{label}_violations"] = int(matches[-1])
            if counts[f"{label}_violations"] != 0:
                reasons.append(f"ARC {label} violations = {matches[-1]}")
    return counts, reasons


def _run_config_reasons(run_dir: Path) -> list[str]:
    try:
        body = (run_dir / "config_in.tcl").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ["OpenLane effective input config missing"]
    reasons = []
    for key, value in OVERRIDES.items():
        if re.search(rf"(?m)^set ::env\({re.escape(key)}\) \"{value}\"$", body) is None:
            reasons.append(f"OpenLane did not load clean-run {key}={value}")
    try:
        resolved = (run_dir / "config.tcl").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [*reasons, "OpenLane resolved config missing"]
    for key, value in (("MAX_FANOUT_CONSTRAINT", 10),
                       ("GRT_REPAIR_ANTENNAS", 1),
                       ("USE_ARC_ANTENNA_CHECK", 1)):
        if re.search(rf"(?m)^set ::env\({key}\) \"{value}\"$", resolved) is None:
            reasons.append(f"OpenLane resolved {key} differs from lvs09")
    return reasons


def audit(root: Path, tag: str, reasons: list[str]) -> dict:
    run_dir = root / DESIGN / "runs" / tag
    result: dict = {"metrics": {}, "sta": {}, "antenna": {},
                    "final_gds": None, "final_gds_sha256": None}
    reasons.extend(_run_config_reasons(run_dir))
    reasons.extend(_pdn_ground_reasons(
        run_dir / "results/floorplan" / f"{TOP}.def",
        run_dir / "logs/floorplan/7-pdn.log",
        root / "physical/sky130/macro" / f"{CORE}.lef"))
    try:
        with (run_dir / "reports/metrics.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if len(rows) != 1:
            reasons.append("metrics.csv must contain exactly one result row")
        else:
            metrics = rows[0]
            result["metrics"] = {key: metrics.get(key) for key in
                                 ("flow_status", *ZERO_METRICS)}
            reasons.extend(_zero_metric_reasons(metrics))
    except (OSError, ValueError, csv.Error):
        reasons.append("OpenLane metrics missing or invalid")
    result["sta"], sta_reasons = _sta_reasons(run_dir)
    reasons.extend(sta_reasons)
    result["antenna"], arc_reasons = _arc_reasons(run_dir)
    reasons.extend(arc_reasons)
    lvs_report, lvs_reasons = _unique_report(
        run_dir / "reports/signoff", f"*-{TOP}.lvs.rpt")
    reasons.extend(lvs_reasons)
    if lvs_report is not None:
        try:
            lvs = lvs_report.read_text(encoding="utf-8", errors="replace")
            if re.search(r"(?m)^Total errors = 0\s*$", lvs) is None:
                reasons.append("detailed top LVS report does not say Total errors = 0")
        except OSError:
            reasons.append("detailed top LVS report unreadable")
    final = run_dir / "results/final/gds" / f"{TOP}.gds"
    if not final.is_file() or not final.stat().st_size:
        reasons.append("nonempty final GDS missing")
    else:
        result["final_gds"] = final.relative_to(root).as_posix()
        result["final_gds_sha256"] = _sha(final)
        try:
            if not _gds_reaches(_gds_hierarchy(final), TOP, CORE):
                reasons.append("final GDS does not contain reachable passive core")
        except (OSError, UnicodeError, ValueError) as error:
            reasons.append(f"final GDS invalid: {error}")
    return result


def run(root: str | Path, tag: str, *, audit_existing: bool = False) -> dict:
    root = Path(root).resolve()
    if re.fullmatch(r"[A-Za-z0-9_-]+", tag) is None:
        raise ValueError("unsafe OpenLane tag")
    reasons = list(inspect(root)["reasons"])
    reasons.extend(_variant_reasons(root))
    if audit_existing or not reasons:
        reasons.extend(_snapshot(root, tag, create=not audit_existing))
    report = {
        "format": "automx-cim-core-bound-clean-check-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "status": "READY_CLEAN_CORE_BOUND_EXPERIMENT" if not reasons else "BLOCKED",
        "reasons": reasons,
        "run_dir": (DESIGN / "runs" / tag).as_posix(),
        "config": VARIANT.as_posix(),
        "not_signoff": "external analog phase/sample-hold/ADC; LEF-macro top LVS only; no composite device LVS/PEX or mixed-signal wrapper views/PVT",
    }
    if audit_existing:
        try:
            frozen = json.loads((root / "build/stage8_core_bound_clean" / tag /
                                 "inputs.json").read_text(encoding="utf-8"))
            report["audit_parser_updated_after_prepare"] = (
                frozen.get(AUDIT_SCRIPT) != _sha(root / AUDIT_SCRIPT))
        except (OSError, ValueError):
            report["audit_parser_updated_after_prepare"] = None
    if audit_existing:
        report.update(audit(root, tag, reasons))
        report["status"] = "CLEAN_CORE_BOUND_EXTERNAL_ANALOG" if not reasons else "FAIL"
    receipt = root / RECEIPT
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--tag", default="core_bound_20261008_clean01")
    parser.add_argument("--audit-existing", action="store_true")
    args = parser.parse_args()
    result = run(args.root, args.tag, audit_existing=args.audit_existing)
    print(json.dumps(result, indent=2))
    if result["status"] not in ("READY_CLEAN_CORE_BOUND_EXPERIMENT",
                                "CLEAN_CORE_BOUND_EXTERNAL_ANALOG"):
        raise SystemExit(1)
