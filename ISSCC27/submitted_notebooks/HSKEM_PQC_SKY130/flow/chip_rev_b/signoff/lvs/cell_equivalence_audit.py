#!/usr/bin/env python3
"""Audit the multi-finger standard-cell topology mismatches of a Netgen run by switch-level truth tables.

Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run11_cell_equivalence_audit.py. The old chip fixed seven cells
and their device deltas; here the cell set is every standard cell that the given Netgen log reports with a
device mismatch, the output pin is the cell's X or Y, and every cell must pass the full truth table
(layout transistors vs reference transistors). The top-level device-delta accounting of the old script was
specific to its Run11 log and is replaced by recording the per-cell instance counts.
"""

import argparse
import hashlib
import itertools
import re
from collections import Counter, defaultdict, deque
from pathlib import Path


CELLS = {}  # filled in main(): cell -> (output pin, unused)
POWER = {"VPWR": 1, "VDD": 1, "VGND": 0, "VSS": 0}
BULK = {"VPB", "VNB"}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(token):
    return token[1:] if token.startswith("\\$") else token


def read_cells(path):
    wanted = set(CELLS)
    found = {}
    current = None
    ports = []
    logical_lines = []
    pending = ""
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            words = raw.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT":
                name = words[1].lower()
                current = name if name in wanted else None
                ports = words[2:] if current else []
                logical_lines = []
                pending = ""
                continue
            if current is None:
                continue
            if words and words[0].upper() == ".ENDS":
                if pending:
                    logical_lines.append(pending)
                devices = []
                for line in logical_lines:
                    fields = line.split()
                    if not fields or not fields[0].upper().startswith("M") or len(fields) < 6:
                        continue
                    devices.append(tuple(canonical(value) for value in fields[1:6]))
                found[current] = ([canonical(port) for port in ports], devices)
                current = None
                pending = ""
                continue
            if raw.lstrip().startswith("*") or not words:
                continue
            if raw.startswith("+"):
                pending += " " + raw[1:].strip()
            else:
                if pending:
                    logical_lines.append(pending)
                pending = raw.strip()
    if set(found) != wanted:
        raise RuntimeError(f"missing cells in {path}: {sorted(wanted - set(found))}")
    return found


def evaluate(ports, devices, output, assignment):
    values = dict(POWER)
    values.update(assignment)
    graph = defaultdict(set)
    # Resolve cascaded static-CMOS internal gate nodes to a fixed point.  An
    # unknown-gate transistor is not assumed on; it becomes eligible only
    # after its gate is driven to a rail through an already-resolved stage.
    while True:
        graph = defaultdict(set)
        for drain, gate, source, _bulk, model in devices:
            if gate not in values:
                continue
            model_l = model.lower()
            on = values[gate] == (1 if "nfet" in model_l else 0 if "pfet" in model_l else -1)
            if on:
                graph[drain].add(source)
                graph[source].add(drain)
        changed = False
        seen = set()
        for seed in set(graph) | set(values):
            if seed in seen:
                continue
            component = {seed}
            queue = deque([seed])
            while queue:
                node = queue.popleft()
                for neighbor in graph[node]:
                    if neighbor not in component:
                        component.add(neighbor)
                        queue.append(neighbor)
            seen.update(component)
            driven = {values[node] for node in component if node in values}
            if len(driven) > 1:
                raise RuntimeError(f"rail short for {assignment}: {sorted(component)[:8]}")
            if len(driven) == 1:
                value = next(iter(driven))
                for node in component:
                    if node not in values:
                        values[node] = value
                        changed = True
        if not changed:
            break
    reachable = {output}
    queue = deque([output])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in reachable:
                reachable.add(neighbor)
                queue.append(neighbor)
    high = 1 in {values[node] for node in reachable if node in values}
    low = 0 in {values[node] for node in reachable if node in values}
    if high == low:
        raise RuntimeError(f"output {output} is {'shorted' if high else 'floating'} for {assignment}")
    return 1 if high else 0


def audit_truth_tables(layout_cells, reference_cells):
    rows = []
    for cell, (output, _delta) in CELLS.items():
        lports, ldevices = layout_cells[cell]
        rports, rdevices = reference_cells[cell]
        if set(map(str.upper, lports)) != set(map(str.upper, rports)):
            raise RuntimeError(f"port-set mismatch in {cell}")
        output_name = next(port for port in rports if port.upper() == output)
        inputs = sorted(port for port in rports if port.upper() not in set(POWER) | BULK | {output})
        vectors = 0
        ones = 0
        for bits in itertools.product((0, 1), repeat=len(inputs)):
            assignment = dict(zip(inputs, bits))
            layout_assignment = {next(p for p in lports if p.upper() == key.upper()): value for key, value in assignment.items()}
            layout_output = next(p for p in lports if p.upper() == output)
            lv = evaluate(lports, ldevices, layout_output, layout_assignment)
            rv = evaluate(rports, rdevices, output_name, assignment)
            if lv != rv:
                raise RuntimeError(f"truth-table mismatch {cell} {assignment}: layout={lv} reference={rv}")
            vectors += 1
            ones += lv
        rows.append((cell, len(inputs), vectors, ones, len(ldevices), len(rdevices)))
    return rows


def top_instance_counts(path):
    counts = Counter()
    in_top = False
    pending = None
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            words = raw.split()
            if len(words) >= 2 and words[0].upper() == ".SUBCKT" and words[1].lower() == "trustedge_asic_core":
                in_top = True
                continue
            if in_top and words and words[0].upper() == ".ENDS":
                if pending:
                    counts[pending] += 1
                break
            if not in_top or not words or raw.lstrip().startswith("*"):
                continue
            if raw.startswith("X"):
                if pending:
                    counts[pending] += 1
                pending = words[-1].lower()
            elif raw.startswith("+") and pending:
                pending = words[-1].lower()
            elif pending:
                counts[pending] += 1
                pending = None
    return counts


def report_mismatch_cells(path):
    """Cells (other than the top) whose comparison ends in 'Netlists do not match.'.

    Two log formats: the old chip's Netgen wrote "Contents of circuit 1: Circuit: '<cell>'" and
    "*** MISMATCH ***"; Netgen 1.5.323 writes a side-by-side "Circuit 1: <cell> |Circuit 2: <cell>" header
    and "**Mismatch**" marks, and closes every cell comparison with "Netlists do not match." or
    "Netlists match uniquely.".
    """
    cells = set()
    last_cell = None
    old_re = re.compile(r"Contents of circuit 1:\s+Circuit: '([^']+)'", re.I)
    new_re = re.compile(r"^Circuit 1:\s+(\S+)\s+\|Circuit 2:\s+(\S+)")
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            match = old_re.search(line) or new_re.search(line)
            if match:
                last_cell = match.group(1).lower()
            if last_cell and last_cell != "trustedge_asic_core":
                if ("devices" in line and "*** MISMATCH ***" in line) or line.startswith("Netlists do not match"):
                    cells.add(last_cell)
    return cells


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--console", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    mismatch_cells = report_mismatch_cells(args.console)
    if not mismatch_cells or not all(cell and cell.startswith("sky130_fd_sc_hd__") for cell in mismatch_cells):
        raise RuntimeError(f"mismatch cell set is empty or not standard cells: {sorted(map(str, mismatch_cells))}")
    for cell in mismatch_cells:
        CELLS[cell] = (None, 0)
    layout_cells = read_cells(args.layout)
    reference_cells = read_cells(args.reference)
    for cell in mismatch_cells:
        ports = {port.upper() for port in reference_cells[cell][0]}
        outputs = [pin for pin in ("Y", "X") if pin in ports]
        if len(outputs) != 1:
            raise RuntimeError(f"cannot pick a single output pin for {cell}: {sorted(ports)}")
        CELLS[cell] = (outputs[0], 0)
    rows = audit_truth_tables(layout_cells, reference_cells)
    counts = top_instance_counts(args.layout)

    lines = [
        "A3_RUN11_MULTIFINGER_CELL_AUDIT=PASS",
        f"layout_sha256={sha256(args.layout)}",
        f"reference_sha256={sha256(args.reference)}",
        f"netgen_log_sha256={sha256(args.console)}",
        f"mismatch_cell_count={len(mismatch_cells)}",
    ]
    for cell, inputs, vectors, ones, layout_devices, reference_devices in rows:
        lines.append(
            f"cell={cell}|output={CELLS[cell][0]}|inputs={inputs}|vectors={vectors}|ones={ones}|"
            f"layout_mos={layout_devices}|reference_mos_records={reference_devices}|"
            f"top_instances={counts[cell]}|switch_truth_table=PASS"
        )
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
