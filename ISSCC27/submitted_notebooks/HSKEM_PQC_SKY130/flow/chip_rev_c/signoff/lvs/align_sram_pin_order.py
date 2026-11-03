#!/usr/bin/env python3
"""Align repaired SRAM headers and instance arguments to the reference order."""

import argparse
import os
from pathlib import Path

# Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run15_align_sram_pin_order.py: the SRAM masters and the
# instance count come from CHIPV2_LVS_SRAMS (comma list) and CHIPV2_LVS_SRAM_INSTANCES instead of 8 / 18.
SRAMS = {name.lower() for name in os.environ["CHIPV2_LVS_SRAMS"].split(",") if name}
SRAM_INSTANCES = int(os.environ["CHIPV2_LVS_SRAM_INSTANCES"])


def statements(path):
    pending = None
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            if pending is not None and line.lstrip().startswith("+"):
                pending += " " + line.lstrip()[1:].strip()
                continue
            if pending is not None:
                yield pending
            pending = line.rstrip("\n")
        if pending is not None:
            yield pending


def headers(path):
    result = {}
    current = None
    raw_ports = None
    net_names = None
    for statement in statements(path):
        words = statement.split()
        if len(words) >= 2 and words[0].upper() == ".SUBCKT":
            name = words[1].lower()
            if name in SRAMS:
                if name in result:
                    raise RuntimeError(f"duplicate SRAM header: {name}")
                current = name
                raw_ports = words[2:]
                net_names = {}
            else:
                current = None
            continue
        if current is not None and len(words) >= 4 and words[0] == "*" and words[1].lower() == "net":
            net_names[words[2]] = words[3]
            continue
        if current is not None and words and words[0].upper() == ".ENDS":
            ports = [net_names.get(port, port) for port in raw_ports]
            ports = [port[len("__physical_"):] if port.lower().startswith("__physical_") else port
                     for port in ports]
            canonical = [port.upper() for port in ports]
            if len(canonical) != len(set(canonical)):
                raise RuntimeError(f"duplicate SRAM ports: {current}")
            result[current] = ports
            current = None
    if set(result) != SRAMS:
        raise RuntimeError(f"SRAM header set mismatch: {sorted(set(result) ^ SRAMS)}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_headers = headers(args.layout)
    target_headers = headers(args.reference)
    permutations = {}
    for name in sorted(SRAMS):
        source = source_headers[name]
        target = target_headers[name]
        source_index = {port.upper(): index for index, port in enumerate(source)}
        if set(source_index) != {port.upper() for port in target}:
            raise RuntimeError(f"SRAM pin set mismatch: {name}")
        permutations[name] = [source_index[port.upper()] for port in target]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    instance_count = 0
    header_count = 0
    with args.output.open("w", encoding="utf-8", newline="\n") as out:
        for statement in statements(args.layout):
            words = statement.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT" and words[1].lower() in SRAMS:
                name = words[1].lower()
                out.write(f".SUBCKT {words[1]} {' '.join(target_headers[name])}\n")
                header_count += 1
                continue
            if words and words[0].upper().startswith("X") and words[-1].lower() in SRAMS:
                name = words[-1].lower()
                nodes = words[1:-1]
                if len(nodes) != len(source_headers[name]):
                    raise RuntimeError(f"SRAM instance arity mismatch: {words[0]} {name}")
                reordered = [nodes[index] for index in permutations[name]]
                out.write(" ".join([words[0], *reordered, words[-1]]) + "\n")
                instance_count += 1
                continue
            out.write(statement + "\n")

    if header_count != len(SRAMS) or instance_count != SRAM_INSTANCES:
        raise RuntimeError(f"alignment count mismatch headers={header_count} instances={instance_count}")
    print("A3_RUN15_SRAM_PIN_ORDER_ALIGNMENT=PASS")
    print(f"aligned_sram_headers={header_count}")
    print(f"aligned_sram_instances={instance_count}")


if __name__ == "__main__":
    main()
