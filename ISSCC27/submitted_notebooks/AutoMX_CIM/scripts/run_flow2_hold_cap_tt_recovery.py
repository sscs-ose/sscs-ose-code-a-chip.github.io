#!/usr/bin/env python3
"""Retry isolated hold-cap TT charge with an explicit substrate DC reference.

The original PEX remains immutable. A derived simulation-only copy adds a
1-Gohm VGND reference to the one floating substrate node reported by Magic.
This does not prove a substrate tie in the eventual composite layout.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automx_cim.physical import stage5  # noqa: E402
from automx_cim.spice import parse_measurements  # noqa: E402
from scripts import run_flow2_hold_cap_tt as charge  # noqa: E402
from scripts import run_flow2_hold_cap_leaf as leaf  # noqa: E402
from scripts import run_flow2_hold_cap_pex as pex  # noqa: E402
from scripts import run_flow2_precharge_leaf_layout as precharge  # noqa: E402
from scripts import run_flow2_remaining_measurements as campaign  # noqa: E402

FORMAT = "automx-cim-flow2-hold-cap-tt-substrate-recovery-v1"
DEFAULT_TAG = "hold_cap_charge_tt_20261017_02"
SOURCE_TAG = "hold_cap_charge_tt_20261017_01"
BIAS_OHMS = 1_000_000_000


def _item(root: Path, path: Path) -> dict[str, str]:
    return {"path": path.relative_to(root).as_posix(), "sha256": campaign._sha(path)}


def _previous(root: Path, view: Path, model: Path) -> tuple[Path, dict]:
    source = root / leaf.OUTPUT / SOURCE_TAG / "hold_cap_charge_tt.json"
    if not source.is_file():
        raise FileNotFoundError(f"failed isolated TT run is required: {source}")
    report = json.loads(source.read_text(encoding="utf-8"))
    jobs = report.get("jobs", {})
    schematic = jobs.get("schematic", {})
    failed = jobs.get("pex", {})
    if (report.get("format") != charge.FORMAT or
            report.get("status") != "BLOCKED_HOLD_CAP_TT_SIMULATION" or
            report.get("source_tag") != pex.DEFAULT_SOURCE_TAG or
            report.get("pex_tag") != pex.DEFAULT_TAG or
            report.get("pex_sha256") != campaign._sha(view) or
            report.get("model_sha256") != campaign._sha(model) or
            schematic.get("returncode") != 0 or
            failed.get("returncode") != 1 or
            set(schematic.get("measurements", {})) != set(charge.MEASURES) or
            not math.isfinite(schematic.get("effective_capacitance_ff", float("nan")))):
        raise ValueError("complete hash-linked failed TT run is required")
    for job in (schematic, failed):
        for key in ("deck", "log"):
            charge._verified_file(root, job.get(key), key)
    old_log = (root / failed["log"]["path"]).read_text(encoding="utf-8", errors="replace")
    if ("singular matrix" not in old_log.lower() or
            "w_n606_n460#" not in old_log.lower()):
        raise ValueError("previous PEX failure is not the expected substrate singularity")
    return source, schematic


def _substrate_referenced_view(source: Path, target: Path) -> str:
    """Add one simulation-only DC path to a singly floating substrate node."""
    original = source.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    name = f"{leaf.CELL}_pex_raw"
    start = next((i for i, line in enumerate(lines)
                  if re.match(rf"(?i)^\s*\.subckt\s+{re.escape(name)}\s+", line)), None)
    stop = next((i for i in range(start + 1, len(lines))
                 if re.match(r"(?i)^\s*\.ends(?:\s|$)", lines[i])), None) if start is not None else None
    if start is None or stop is None:
        raise ValueError("raw MIM3 PEX subcircuit is missing")
    candidates = []
    for line in lines[start + 1:stop]:
        fields = line.split()
        if (len(fields) == 4 and fields[0].upper().startswith("C") and
                "VGND" in (fields[1].upper(), fields[2].upper())):
            other = fields[2] if fields[1].upper() == "VGND" else fields[1]
            if re.fullmatch(r"w_[A-Za-z0-9_]+#", other):
                candidates.append(other)
    if len(candidates) != 1 or original.split().count(candidates[0]) != 1:
        raise ValueError("expected exactly one isolated substrate capacitor node")
    node = candidates[0]
    lines.insert(stop, f"RSUBREF {node} VGND {BIAS_OHMS}\n")
    target.write_text("".join(lines), encoding="utf-8")
    return node


def run(root: str | Path, *, pdk_root: str | Path | None = None,
        tag: str = DEFAULT_TAG, execute: bool = False,
        timeout_s: int = 900) -> dict:
    root = Path(root).resolve()
    if (not precharge.TAG_RE.fullmatch(tag) or tag in
            (SOURCE_TAG, pex.DEFAULT_TAG, pex.DEFAULT_SOURCE_TAG) or timeout_s <= 0):
        raise ValueError("invalid recovery tag or timeout")
    view, pex_receipt, leaf_receipt = charge._source(
        root, pex.DEFAULT_SOURCE_TAG, pex.DEFAULT_TAG)
    pdk = precharge._pdk(root, Path(pdk_root) if pdk_root is not None else None)
    model = pdk / "libs.tech/ngspice/sky130.lib.spice" if pdk else None
    ngspice = shutil.which("ngspice")
    reasons = []
    if not model or not model.is_file():
        reasons.append("SKY130 ngspice model library is missing")
    if not ngspice:
        reasons.append("ngspice is missing")
    prior_path, schematic = _previous(root, view, model) if not reasons else (None, None)
    folder = root / leaf.OUTPUT / tag
    receipt_path = folder / "hold_cap_charge_tt_recovery.json"
    report = {
        "format": FORMAT,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PREREQUISITES" if reasons else "READY_TO_RUN",
        "scope": "isolated MIM3 PEX, TT/25 C; one simulation-only substrate DC reference",
        "tag": tag,
        "source_failed_receipt_sha256": campaign._sha(prior_path) if prior_path else None,
        "leaf_receipt_sha256": campaign._sha(leaf_receipt),
        "pex_receipt_sha256": campaign._sha(pex_receipt),
        "original_pex_sha256": campaign._sha(view),
        "model_sha256": campaign._sha(model) if model and model.is_file() else None,
        "script_sha256": campaign._sha(Path(__file__)),
        "substrate_reference_ohms": BIAS_OHMS,
        "ngspice_executable": ngspice,
        "missing_prerequisites": reasons,
        "not_signoff": "simulation-only floating-substrate reference; physical substrate contact, sampler, retention, ADC and wrapper remain unverified",
    }
    if reasons or not execute:
        return report
    if receipt_path.is_file():
        saved = json.loads(receipt_path.read_text(encoding="utf-8"))
        for key in ("format", "tag", "source_failed_receipt_sha256",
                    "leaf_receipt_sha256", "pex_receipt_sha256",
                    "original_pex_sha256", "model_sha256", "script_sha256"):
            if saved.get(key) != report[key]:
                raise FileExistsError(f"recovery inputs changed: {receipt_path}")
        for key in ("derived_pex", "deck", "log"):
            if saved.get(key):
                charge._verified_file(root, saved[key], key)
        return saved
    build = root / "build/flow2_periphery_leaf" / tag / "charge_tt"
    if build.exists() and any(build.iterdir()):
        raise FileExistsError(f"interrupted recovery build needs inspection: {build}")
    build.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    derived = build / f"{leaf.CELL}.substrate_ref.pex.spice"
    node = _substrate_referenced_view(view, derived)
    report["substrate_node"] = node
    report["derived_pex"] = _item(root, derived)
    deck = build / "pex.spice"
    deck.write_text(charge._deck(model, derived, extracted=True), encoding="utf-8")
    report["deck"] = _item(root, deck)
    log = folder / "hold_cap_pex_tt_recovery.log"
    try:
        completed = stage5._run([ngspice, "-b", "-o", str(log), str(deck)],
                                build, timeout_s)
        report["returncode"] = completed.returncode
        output = (log.read_text(encoding="utf-8", errors="replace") if log.is_file()
                  else completed.stdout + completed.stderr)
    except subprocess.TimeoutExpired:
        report["returncode"] = None
        output = f"ngspice timed out after {timeout_s}s\n"
    if not log.is_file():
        log.write_text(output, encoding="utf-8")
    report["log"] = _item(root, log)
    values = parse_measurements(output, expected=charge.MEASURES)
    report["pex_measurements"] = values
    if (report["returncode"] != 0 or set(values) != set(charge.MEASURES) or
            not all(math.isfinite(value) for value in values.values())):
        report["status"] = "BLOCKED_HOLD_CAP_TT_RECOVERY_SIMULATION"
    else:
        delta_v = values["v_after"] - values["v_before"]
        if not 1.75 <= delta_v <= 1.85:
            report["status"] = "BLOCKED_HOLD_CAP_TT_RECOVERY_VOLTAGE_RAMP"
        else:
            report["schematic_effective_capacitance_ff"] = schematic["effective_capacitance_ff"]
            report["pex_effective_capacitance_ff"] = abs(values["charge_c"]) / delta_v * 1e15
            report["pex_minus_schematic_ff"] = (report["pex_effective_capacitance_ff"] -
                                                   report["schematic_effective_capacitance_ff"])
            report["status"] = "MEASURED_HOLD_CAP_TT_SUBSTRATE_REFERENCED_DIAGNOSTIC"
    campaign._save(receipt_path, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--timeout-s", type=int, default=900)
    args = parser.parse_args()
    print(json.dumps(run(args.root, pdk_root=args.pdk_root, tag=args.tag,
                         execute=args.run, timeout_s=args.timeout_s), indent=2))
