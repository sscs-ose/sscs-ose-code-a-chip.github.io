"""Summarize the logs of sta_macro_bound.sh: per macro-arc scale factor, the worst setup slack of the paths that
include the SRAM macros and of the flip-flop-to-flip-flop paths, and the worst overall setup slack.

    python3 sta_macro_bound_summary.py <log dir> <corner> <out.json>

The scale factor at which the two slacks separate is the point where a path through a macro becomes the chip's
critical path. Uses the same report parsing as sta_corners_fullchip.sh.
SPDX-License-Identifier: Apache-2.0
"""
import json
import pathlib
import re
import sys

logs, corner, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
SLACK = re.compile(r"^\S+\s+\(\S+\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+\((?:MET|VIOLATED)\)", re.M)


def section(text, name):
    return text.split(f"SECTION {name}\n", 1)[1].split("SECTION ", 1)[0]


def group_slack(text, check, group="core_clk"):
    parts = text.split(f"{check} group {group}", 1)
    if len(parts) < 2:
        return None
    body = re.split(r"\n(?:max_delay/setup|min_delay/hold) group ", parts[1], maxsplit=1)[0]
    m = SLACK.search(body)
    return float(m[3]) if m else None


res = {}
for f in sorted(logs.glob(f"bound_{corner}_x*.log"), key=lambda p: float(re.search(r"_x([\d.]+)\.log", p.name)[1])):
    k = float(re.search(r"_x([\d.]+)\.log", f.name)[1])
    t = f.read_text(errors="replace")
    if "SECTION END" not in t:
        continue
    r = {a: float(b) for a, b in re.findall(r"RESULT (\w+) (-?[\d.]+)", t)}
    r["reg2reg_incl_macros_setup_slack_ns"] = group_slack(section(t, "reg2reg_with_macros"), "max_delay/setup")
    r["ff2ff_setup_slack_ns"] = group_slack(section(t, "ff2ff_setup"), "max_delay/setup")
    r["reg2reg_incl_macros_hold_slack_ns"] = group_slack(section(t, "reg2reg_with_macros"), "min_delay/hold")
    r["ff2ff_hold_slack_ns"] = group_slack(section(t, "ff2ff_hold"), "min_delay/hold")
    r["worst_setup_paths_any"] = [l.split() for l in section(t, "worst_setup_paths_any").splitlines() if "VIOLATED" in l or "MET" in l][:5]
    res[f"x{k:g}"] = r
MP = re.compile(r"\((?:MET|VIOLATED)\)")
for f in logs.glob(f"macro_paths_{corner}_x*.log"):          # flow/sta_macro_paths.tcl, via sta_macro_paths.sh
    k = float(re.search(r"_x([\d.]+)\.log", f.name)[1])
    sec = None
    for line in f.read_text(errors="replace").splitlines():
        if line.startswith("SECTION "):
            sec = line.split()[1]
        elif sec and MP.search(line):
            res.setdefault(f"x{k:g}", {}).setdefault("macro_paths_slack_ns", {})[sec] = float(line.split()[-2])
out.write_text(json.dumps({"corner": corner, "macro_arc_scale": res}, indent=1) + "\n")
for k, r in res.items():
    if "setup_wns" not in r:
        continue
    print(k, r.get("macro_paths_slack_ns"), "reg2reg+macros", r["reg2reg_incl_macros_setup_slack_ns"], "ff2ff", r["ff2ff_setup_slack_ns"], "wns", r["setup_wns"])
