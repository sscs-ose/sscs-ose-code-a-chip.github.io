#!/usr/bin/env python3
"""Empty exactly the independently verified multi-finger cell bodies.

Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run13_prepare_verified_abstractions.py: the cell set is read from
the truth-table audit (every cell line with switch_truth_table=PASS) instead of the old fixed seven cells.
"""

import argparse
import hashlib
from pathlib import Path


CELLS = set()


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rewrite(source, destination):
    found = set()
    skipped_records = {}
    current = None
    skipped = 0
    with source.open("r", encoding="utf-8", errors="strict") as inp, destination.open("w", encoding="utf-8", newline="\n") as out:
        for line in inp:
            words = line.split()
            if current is None and len(words) >= 2 and words[0].upper() == ".SUBCKT" and words[1].lower() in CELLS:
                current = words[1].lower()
                if current in found:
                    raise RuntimeError(f"duplicate verified cell {current}")
                found.add(current)
                skipped = 0
                out.write(line)
                continue
            if current is not None:
                if words and words[0].upper() == ".ENDS":
                    if skipped == 0:
                        raise RuntimeError(f"verified cell already empty: {current}")
                    skipped_records[current] = skipped
                    out.write(f".ENDS {current}\n")
                    current = None
                elif words and not line.lstrip().startswith("*"):
                    skipped += 1
                continue
            out.write(line)
    if current is not None:
        raise RuntimeError(f"unterminated verified cell {current}")
    if found != CELLS:
        raise RuntimeError(f"verified abstraction set mismatch: {sorted(found)}")
    return skipped_records


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--layout", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--layout-out", type=Path, required=True)
    p.add_argument("--reference-out", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    args = p.parse_args()
    audit_text = args.audit.read_text(encoding="utf-8")
    if "A3_RUN11_MULTIFINGER_CELL_AUDIT=PASS" not in audit_text:
        raise RuntimeError("cell audit PASS marker absent")
    for line in audit_text.splitlines():
        if line.startswith("cell=") and line.endswith("switch_truth_table=PASS"):
            CELLS.add(line.split("|", 1)[0][len("cell="):])
    expected = int(next(l.split("=", 1)[1] for l in audit_text.splitlines() if l.startswith("mismatch_cell_count=")))
    if len(CELLS) != expected or expected == 0:
        raise RuntimeError(f"cell audit proves {len(CELLS)} of {expected} cells")
    args.layout_out.parent.mkdir(parents=True, exist_ok=True)
    layout_skipped = rewrite(args.layout, args.layout_out)
    reference_skipped = rewrite(args.reference, args.reference_out)
    lines = [
        "A3_RUN13_VERIFIED_CELL_ABSTRACTION=PASS",
        f"abstract_cell_count={len(CELLS)}",
        f"layout_input_sha256={sha256(args.layout)}",
        f"reference_input_sha256={sha256(args.reference)}",
        f"cell_audit_sha256={sha256(args.audit)}",
        f"layout_output_sha256={sha256(args.layout_out)}",
        f"reference_output_sha256={sha256(args.reference_out)}",
    ]
    for cell in sorted(CELLS):
        lines.append(f"cell={cell}|layout_removed_records={layout_skipped[cell]}|reference_removed_records={reference_skipped[cell]}|audit_guard=PASS")
    args.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
