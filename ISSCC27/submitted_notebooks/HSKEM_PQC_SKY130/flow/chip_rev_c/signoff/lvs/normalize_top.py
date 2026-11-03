#!/usr/bin/env python3
"""Create guarded compare-only top-pin-normalized CDL inputs for A3 Run11.

Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run11_normalize_top.py: the pin counts come from the activity
audit (its PASS line) and the top instance count from CHIPV2_LVS_TOP_INSTANCES instead of 411 / 341 / 188960.
"""

import argparse
import hashlib
import os
import re
from pathlib import Path


TOP = "trustedge_asic_core"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_probe(path: Path):
    mappings = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("map="):
            continue
        fields = dict(field.split("=", 1) for field in line.split("|") if "=" in field)
        reference = fields["map"].upper()
        source = fields["l2n_net"]
        if reference in mappings or source in mappings.values():
            raise RuntimeError(f"non-unique probe mapping: {reference} -> {source}")
        mappings[reference] = source
    if len(mappings) == 0:
        raise RuntimeError("no probe mappings")
    if "A3_RUN10_GDS_LABEL_PROBE_L2N=PASS" not in path.read_text(encoding="utf-8"):
        raise RuntimeError("probe audit does not contain PASS marker")
    return mappings


def read_activity(path: Path):
    activity = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("pin="):
            continue
        fields = dict(field.split("=", 1) for field in line.split("|") if "=" in field)
        name = fields["pin"].upper()
        activity[name] = fields["active"] == "1"
        if not activity[name] and (fields["subcircuit_pin_count"] != "0" or fields["terminal_count"] != "0"):
            raise RuntimeError(f"inactive pin has connectivity: {name}")
    summary = [l for l in path.read_text(encoding="utf-8").splitlines() if "REFERENCE_TOP_PIN_ACTIVITY=PASS" in l]
    if len(summary) != 1:
        raise RuntimeError("activity audit PASS line missing")
    fields = dict(f.split("=", 1) for f in summary[0].split("|")[1:])
    if len(activity) != int(fields["total"]) or sum(activity.values()) != int(fields["active"]):
        raise RuntimeError(f"unexpected activity counts: total={len(activity)} active={sum(activity.values())}")
    return activity


def reference_header(path: Path):
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            words = line.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT" and words[1].upper() == TOP.upper():
                return words[2:]
    raise RuntimeError("reference top header not found")


def rewrite_reference(source: Path, destination: Path, active_ports):
    replaced = False
    with source.open("r", encoding="utf-8", errors="strict") as inp, destination.open("w", encoding="utf-8", newline="\n") as out:
        for line in inp:
            words = line.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT" and words[1].upper() == TOP.upper():
                if replaced:
                    raise RuntimeError("duplicate reference top header")
                out.write(f".SUBCKT {TOP} {' '.join(active_ports)}\n")
                replaced = True
            else:
                out.write(line)
    if not replaced:
        raise RuntimeError("reference top header not rewritten")


def rewrite_layout(source: Path, destination: Path, active_ports, mappings, reference_case):
    source_to_target = {value: reference_case[key] for key, value in mappings.items()}
    counts = {key: 0 for key in source_to_target}
    in_top = False
    saw_top = False
    saw_end = False
    instance_count = 0
    with source.open("r", encoding="utf-8", errors="strict") as inp, destination.open("w", encoding="utf-8", newline="\n") as out:
        for line in inp:
            words = line.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT" and words[1].upper() == TOP.upper():
                if saw_top:
                    raise RuntimeError("duplicate layout top header")
                saw_top = True
                in_top = True
                out.write(f".SUBCKT {TOP} {' '.join(active_ports)}\n")
                continue
            if in_top and words and words[0].upper() == ".ENDS":
                in_top = False
                saw_end = True
                out.write(line)
                continue
            if not in_top or not words or line.lstrip().startswith("*"):
                out.write(line)
                continue
            if words[0].startswith("X"):
                instance_count += 1
            changed = False
            for index, token in enumerate(words):
                canonical = token[1:] if token.startswith("\\$") else token
                if canonical in source_to_target:
                    words[index] = source_to_target[canonical]
                    counts[canonical] += 1
                    changed = True
            out.write((" ".join(words) + "\n") if changed else line)
    if not saw_top or not saw_end:
        raise RuntimeError("layout top circuit boundaries not found")
    missing = sorted(source for source, count in counts.items() if count == 0)
    if missing:
        raise RuntimeError(f"mapped source nets absent from layout top: {missing[:8]}")
    if instance_count != int(os.environ["CHIPV2_LVS_TOP_INSTANCES"]):
        raise RuntimeError(f"unexpected layout top instance count: {instance_count}")
    return counts, instance_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--activity", type=Path, required=True)
    parser.add_argument("--layout-out", type=Path, required=True)
    parser.add_argument("--reference-out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    mappings = read_probe(args.probe)
    activity = read_activity(args.activity)
    ports = reference_header(args.reference)
    if len(ports) != len(activity) or len({port.upper() for port in ports}) != len(ports):
        raise RuntimeError(f"reference header does not have {len(activity)} unique ports")
    reference_case = {port.upper(): port for port in ports}
    if set(reference_case) != set(activity):
        raise RuntimeError("activity/reference port sets differ")
    active_ports = [port for port in ports if activity[port.upper()]]
    inactive_ports = [port for port in ports if not activity[port.upper()]]
    if set(mappings) != {port.upper() for port in active_ports}:
        raise RuntimeError("probe mapping set is not exactly the active reference port set")

    args.layout_out.parent.mkdir(parents=True, exist_ok=True)
    rewrite_reference(args.reference, args.reference_out, active_ports)
    counts, instance_count = rewrite_layout(args.layout, args.layout_out, active_ports, mappings, reference_case)

    manifest_lines = [
        "A3_RUN11_TOP_NORMALIZATION=PASS",
        f"reference_port_count={len(ports)}",
        f"active_port_count={len(active_ports)}",
        f"inactive_disconnected_port_count={len(inactive_ports)}",
        f"mapped_unique_l2n_net_count={len(set(mappings.values()))}",
        f"layout_top_instance_count={instance_count}",
        f"layout_input_sha256={sha256(args.layout)}",
        f"reference_input_sha256={sha256(args.reference)}",
        f"probe_audit_sha256={sha256(args.probe)}",
        f"activity_audit_sha256={sha256(args.activity)}",
        f"layout_output_sha256={sha256(args.layout_out)}",
        f"reference_output_sha256={sha256(args.reference_out)}",
        "inactive_ports=" + ",".join(inactive_ports),
    ]
    args.manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print("\n".join(manifest_lines[:-1]))


if __name__ == "__main__":
    main()
