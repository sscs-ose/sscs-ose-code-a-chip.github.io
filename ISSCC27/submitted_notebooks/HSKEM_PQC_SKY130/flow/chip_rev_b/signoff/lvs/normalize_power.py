#!/usr/bin/env python3
"""Normalize guarded top-level power connectivity for Run15 comparison.

This transformation is intentionally narrow:

* Layout: collapse the extracted standard-cell substrate net ``VNB`` onto
  ``VSS``.  The SKY130 tap-cell contract states that substrate is tied to
  ``VGND`` internally, while the hierarchical extracted tap abstraction has no
  explicit VNB pin.
* Reference: repair only buffer instances whose four standard-cell power pins
  were serialized as four distinct ``_unconnected_*`` nets.  Signal pins are
  never changed.

The source files are not modified.  Cardinalities are checked fail-closed and
recorded in a manifest beside the derived comparison inputs.
"""

from __future__ import annotations

import argparse
import os
import hashlib
import re
from collections import Counter
from pathlib import Path


TOP = "trustedge_asic_core"
# Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run15_normalize_power_connectivity.py. The old chip pinned 188942
# VNB pins and 310 buf_12 + 24 buf_4 reference instances with all-unconnected power; here every VNB pin must be
# replaced, any standard-cell master may carry the all-four-unconnected power pattern (ECO cells created by odb
# edits), the counts are recorded, and the top instance count comes from CHIPV2_LVS_TOP_INSTANCES.
TOP_INSTANCES = int(os.environ["CHIPV2_LVS_TOP_INSTANCES"])
POWER_EXPECTED = {
    "VGND": "VSS",
    "VNB": "VSS",
    "VPB": "VDD",
    "VPWR": "VDD",
}
UNCONNECTED = re.compile(r"^_unconnected_[0-9]+$", re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def logical_statements(path: Path):
    pending = None
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            stripped = raw.strip()
            if stripped.startswith("+"):
                if pending is None:
                    raise RuntimeError(f"orphan continuation in {path}")
                pending += " " + stripped[1:].strip()
                continue
            if pending is not None:
                yield pending
            pending = raw.rstrip("\r\n")
    if pending is not None:
        yield pending


def headers(path: Path):
    result = {}
    for statement in logical_statements(path):
        words = statement.split()
        if len(words) >= 2 and words[0].upper() == ".SUBCKT":
            name = words[1].lower()
            if name in result:
                raise RuntimeError(f"duplicate circuit {name} in {path}")
            result[name] = words[2:]
    return result


def rewrite_layout(source: Path, destination: Path):
    cell_headers = headers(source)
    in_top = False
    replacements = 0
    vnb_pin_count = 0
    supply_errors = []
    top_instances = 0
    with destination.open("w", encoding="utf-8", newline="\n") as out:
        for statement in logical_statements(source):
            words = statement.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT":
                in_top = words[1].lower() == TOP
            elif words and words[0].upper() == ".ENDS":
                in_top = False
            elif in_top and words and words[0].upper().startswith("X"):
                top_instances += 1
                model = words[-1].lower()
                pins = cell_headers.get(model)
                nodes = words[1:-1]
                if pins is None or len(pins) != len(nodes):
                    raise RuntimeError(f"layout pin cardinality failure: {words[0]}/{model}")
                for index, (pin, node) in enumerate(zip(pins, nodes), start=1):
                    upper = pin.upper()
                    if upper == "VNB":
                        vnb_pin_count += 1
                        if node.upper() == "VNB":
                            words[index] = "VSS"
                            replacements += 1
                        elif node.upper() != "VSS":
                            supply_errors.append(f"{words[0]}/{model}/{upper}={node}")
                    elif upper in POWER_EXPECTED and node.upper() != POWER_EXPECTED[upper]:
                        supply_errors.append(f"{words[0]}/{model}/{upper}={node}")
                statement = " ".join(words)
            out.write(statement + "\n")
    if top_instances != TOP_INSTANCES:
        raise RuntimeError(f"layout top instance count mismatch: {top_instances}")
    if supply_errors:
        raise RuntimeError("unexpected layout power connectivity: " + ";".join(supply_errors[:8]))
    if replacements == 0 or replacements != vnb_pin_count:
        raise RuntimeError(
            f"layout VNB normalization mismatch: replacements={replacements} pins={vnb_pin_count}"
        )
    return replacements, top_instances


def rewrite_reference(source: Path, destination: Path):
    cell_headers = headers(source)
    in_top = False
    repaired_instances = Counter()
    repaired_pins = Counter()
    top_instances = 0
    with destination.open("w", encoding="utf-8", newline="\n") as out:
        for statement in logical_statements(source):
            words = statement.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT":
                in_top = words[1].lower() == TOP
            elif words and words[0].upper() == ".ENDS":
                in_top = False
            elif in_top and words and words[0].upper().startswith("X"):
                top_instances += 1
                model = words[-1].lower()
                pins = cell_headers.get(model)
                nodes = words[1:-1]
                if pins is None or len(pins) != len(nodes):
                    raise RuntimeError(f"reference pin cardinality failure: {words[0]}/{model}")
                power_positions = [
                    (index, pin.upper())
                    for index, pin in enumerate(pins, start=1)
                    if pin.upper() in POWER_EXPECTED
                ]
                unconnected_power = [
                    (index, pin) for index, pin in power_positions if UNCONNECTED.fullmatch(words[index])
                ]
                if unconnected_power:
                    if not model.startswith("sky130_fd_sc_hd__"):
                        raise RuntimeError(f"unexpected model with unconnected power: {words[0]}/{model}")
                    if len(power_positions) != 4 or len(unconnected_power) != 4:
                        raise RuntimeError(f"partial unconnected power set: {words[0]}/{model}")
                    for index, pin in unconnected_power:
                        words[index] = POWER_EXPECTED[pin]
                        repaired_pins[pin] += 1
                    repaired_instances[model] += 1
                    statement = " ".join(words)
            out.write(statement + "\n")
    if top_instances != TOP_INSTANCES:
        raise RuntimeError(f"reference top instance count mismatch: {top_instances}")
    expected_pins = sum(repaired_instances.values())
    if expected_pins and repaired_pins != Counter({pin: expected_pins for pin in POWER_EXPECTED}):
        raise RuntimeError(f"reference repaired-pin mismatch: {dict(repaired_pins)}")
    return repaired_instances, repaired_pins, top_instances


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--layout-out", type=Path, required=True)
    parser.add_argument("--reference-out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    args.layout_out.parent.mkdir(parents=True, exist_ok=True)
    layout_vnb, layout_instances = rewrite_layout(args.layout, args.layout_out)
    reference_instances, reference_pins, reference_top = rewrite_reference(
        args.reference, args.reference_out
    )
    lines = [
        "A3_RUN15_POWER_CONNECTIVITY_NORMALIZATION=PASS",
        "source_files_modified=0",
        "signal_pins_modified=0",
        "tap_contract=substrate_to_VGND_and_well_to_VPWR",
        f"layout_top_instances={layout_instances}",
        f"layout_vnb_to_vss_pin_replacements={layout_vnb}",
        f"reference_top_instances={reference_top}",
        f"reference_repaired_instances={sum(reference_instances.values())}",
        f"reference_repaired_power_pins={sum(reference_pins.values())}",
        f"layout_input_sha256={sha256(args.layout)}",
        f"reference_input_sha256={sha256(args.reference)}",
        f"layout_output_sha256={sha256(args.layout_out)}",
        f"reference_output_sha256={sha256(args.reference_out)}",
    ]
    for model in sorted(reference_instances):
        lines.append(f"reference_model={model}|repaired_instances={reference_instances[model]}")
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
