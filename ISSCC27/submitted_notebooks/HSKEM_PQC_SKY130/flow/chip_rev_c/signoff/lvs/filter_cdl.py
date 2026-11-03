#!/usr/bin/env python3
"""Reference CDL for chip v2 LVS: drop the physical-only tap and antenna-diode instances of the top cell.

Derived from asic/run_a3_rcx0114_lvs_run8_filter_cdl.py (old chip). The old script pinned the counts of the
old netlist; here they are counted and recorded, and the accounting must close: every top instance is either
dropped (tap or diode master) or kept, and both dropped masters must be present.
usage: filter_cdl.py <6_final_concat.cdl> <filtered.cdl> <stats.txt>
"""
from pathlib import Path
import sys

source, target, stats_path = map(Path, sys.argv[1:4])
top_name = "trustedge_asic_core"
drop_masters = ("sky130_fd_sc_hd__tapvpwrvgnd_1", "sky130_fd_sc_hd__diode_2")

lines = source.read_text(encoding="utf-8", errors="strict").splitlines(keepends=True)
groups = []
for line in lines:
    if line.lstrip().startswith("+") and groups:
        groups[-1].append(line)
    else:
        groups.append([line])

current_subckt = None
dropped = {name: 0 for name in drop_masters}
kept_top_instances = 0
top_instances = 0
output = []
for group in groups:
    logical = " ".join(
        part.lstrip()[1:].strip() if part.lstrip().startswith("+") else part.strip() for part in group
    )
    tokens = logical.split()
    if tokens and tokens[0].lower() == ".subckt" and len(tokens) >= 2:
        current_subckt = tokens[1].lower()
    elif tokens and tokens[0].lower() == ".ends":
        current_subckt = None
    should_drop = False
    if current_subckt == top_name and tokens and tokens[0][:1].lower() == "x":
        top_instances += 1
        master = tokens[-1].lower()
        if master in dropped:
            dropped[master] += 1
            should_drop = True
        else:
            kept_top_instances += 1
    if not should_drop:
        output.extend(group)

if top_instances == 0:
    raise SystemExit("top cell not found or empty")
for name, count in dropped.items():
    if count == 0:
        raise SystemExit(f"no {name} instances: wrong input?")
if kept_top_instances + sum(dropped.values()) != top_instances:
    raise SystemExit("top instance accounting does not close")

target.write_text("".join(output), encoding="utf-8")
stats_path.write_text(
    "CHIPV2_LVS_FILTER=PASS\n"
    f"top={top_name}\n"
    f"top_instances={top_instances}\n"
    f"dropped_tapvpwrvgnd_1={dropped['sky130_fd_sc_hd__tapvpwrvgnd_1']}\n"
    f"dropped_diode_2={dropped['sky130_fd_sc_hd__diode_2']}\n"
    f"retained_top_instances={kept_top_instances}\n",
    encoding="utf-8",
)
print(f"CHIPV2_LVS_FILTER=PASS|top={top_instances}|retained={kept_top_instances}|"
      f"tap={dropped['sky130_fd_sc_hd__tapvpwrvgnd_1']}|diode={dropped['sky130_fd_sc_hd__diode_2']}")
