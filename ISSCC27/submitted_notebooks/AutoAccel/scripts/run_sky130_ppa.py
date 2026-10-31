#!/usr/bin/env python3
"""sky130_fd_sc_hd PPA flow for the AutoAccel multiplier architectures.

For each architecture (conventional, karatsuba_single, karatsuba_recursive)
and operand width (8, 16, 32, 64):
  1. Yosys generic synth (flattened),
  2. dfflibmap + ABC technology mapping against the sky130 liberty,
  3. ABC `stime` static timing,
  4. Yosys `stat -liberty` + `ltp` on the mapped netlist.

Extracts: mapped cell area (um^2), mapped cell count, critical-path delay
(ps), logic depth (levels), and static leakage (nW) summed from the liberty
`cell_leakage_power` of every mapped cell instance.

Outputs results/sky130_baseline.csv, results/sky130_comparison.csv and the
per-run logs under results/sky130_logs/.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
LOGDIR = RESULTS / "sky130_logs"
LIB = ROOT / "pdk" / "sky130hd_tt.lib"

CONFIGS = [
    {
        "architecture": "conventional",
        "top": "conventional_multiplier",
        "rtl": ["rtl/multiplier/conventional_multiplier.sv"],
    },
    {
        "architecture": "karatsuba_single",
        "top": "karatsuba_multiplier",
        "rtl": ["rtl/multiplier/PARAMETERIZED_MULTIPLIER.sv"],
    },
    {
        "architecture": "karatsuba_recursive",
        "top": "karatsuba_recursive_multiplier",
        "rtl": ["rtl/multiplier/conventional_multiplier.sv",
                "rtl/multiplier/karatsuba_recursive.sv"],
    },
]
WIDTHS = [8, 16, 32, 64]

YOSYS = "/home/z/.micromamba/eda/bin/yosys"


def load_leakage():
    """cell name -> cell_leakage_power (first occurrence per cell block)."""
    leakage = {}
    cur = None
    text = LIB.read_text(errors="replace").splitlines()
    for line in text:
        m = re.match(r"\s*cell \(\s*\"?([A-Za-z0-9_]+)\"?\s*\)", line)
        if m:
            cur = m.group(1)
            continue
        if cur is not None:
            m2 = re.match(r"\s*cell_leakage_power\s*:\s*([0-9eE.+-]+)\s*;", line)
            if m2:
                leakage.setdefault(cur, float(m2.group(1)))
            if re.match(r"\s*}\s*$", line) and leakage.get(cur) is not None:
                pass
    return leakage


def run_yosys(cfg, width, log_path):
    rel_lib = str(LIB.relative_to(ROOT))
    script = "; ".join([
        "read_liberty -lib " + rel_lib,
        "read_verilog -sv " + " ".join(cfg["rtl"]),
        f"hierarchy -top {cfg['top']} -chparam N {width}",
        "proc",
        "flatten",
        "opt_expr",
        "opt_clean",
        "check",
        "opt -nodffe -nosdff",
        "fsm",
        "opt",
        "memory",
        "opt_clean",
        "wreduce",
        "opt -purge",
        "alumacc",
        "share",
        "opt",
        "memory -nomap",
        "opt_clean",
        "techmap",
        "opt -fast",
        "dfflibmap -liberty " + rel_lib,
        "abc -liberty " + rel_lib + " -script scripts/abc_area.script",
        "setundef -zero",
        "clean -purge",
        "stat -liberty " + rel_lib,
        "ltp",
    ])
    proc = subprocess.run(
        [YOSYS, "-p", script],
        cwd=ROOT, capture_output=True, text=True, timeout=600)
    log_path.write_text(proc.stdout + "\n=== STDERR ===\n" + proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"yosys failed rc={proc.returncode} for "
            f"{cfg['architecture']} N={width}; see {log_path}")
    return proc.stdout


def parse_metrics(log_text, leakage):
    area = float(re.search(r"Chip area for module.*?:\s*([0-9.]+)", log_text).group(1))
    mcells = re.search(r"^\s*\d+\s+[0-9.E+]+\s+cells\s*$", log_text, re.M)
    if not mcells:
        mcells = re.search(r"Number of cells:\s*(\d+)", log_text)
    cells = int(re.search(r"\d+", mcells.group(0)).group(0))
    delay = float(re.search(r"Delay\s*=\s*([0-9.]+)", log_text).group(1))
    mltp = re.search(r"Longest topological path[^\n]*?length\s*=\s*(\d+)", log_text)
    depth = int(mltp.group(1)) if mltp else 0

    # per-cell instance counts from the stat -liberty cell table:
    # "       14  105.101   sky130_fd_sc_hd__a21boi_0"
    inst = {}
    for line in log_text.splitlines():
        m = re.match(r"\s+(\d+)\s+[0-9.E+]+\s+(sky130_fd_sc_hd__[A-Za-z0-9_]+)\s*$", line)
        if m:
            inst[m.group(2)] = inst.get(m.group(2), 0) + int(m.group(1))
    leak_nw = 0.0
    missing = set()
    for name, cnt in inst.items():
        val = leakage.get(name)
        if val is None:
            val = leakage.get(name.replace("sky130_fd_sc_hd__", ""))
        if val is None:
            missing.add(name)
            continue
        leak_nw += val * cnt
    if missing:
        print(f"  WARNING: no leakage data for {sorted(missing)}")
    return {
        "sky130_area_um2": round(area, 2),
        "mapped_cells": cells,
        "critical_path_delay_ps": round(delay, 2),
        "logic_depth_levels": depth,
        "static_leakage_nw": round(leak_nw, 4),
    }


def main():
    LOGDIR.mkdir(parents=True, exist_ok=True)
    leakage = load_leakage()
    print(f"Loaded leakage for {len(leakage)} cells from {LIB.name}")

    # --only ARCH WIDTH [ARCH WIDTH ...] : run only the selected points;
    # otherwise run every point whose log does not exist yet.
    args = sys.argv[1:]
    only = set()
    if args and args[0] == "--only":
        it = iter(args[1:])
        for a, w in zip(it, it):
            only.add((a, int(w)))

    rows = []
    for cfg in CONFIGS:
        for width in WIDTHS:
            log_path = LOGDIR / f"{cfg['architecture']}_N{width}_sky130.log"
            if only and (cfg["architecture"], width) not in only:
                continue
            if log_path.exists() and log_path.stat().st_size > 1000 \
                    and "Chip area" in log_path.read_text(errors="replace"):
                print(f"[{cfg['architecture']} N={width}] log exists, parsing", flush=True)
                log_text = log_path.read_text(errors="replace")
            else:
                print(f"[{cfg['architecture']} N={width}] running...", flush=True)
                log_text = run_yosys(cfg, width, log_path)
            met = parse_metrics(log_text, leakage)
            met.update(architecture=cfg["architecture"], width=width,
                       log=str(log_path.relative_to(ROOT)))
            rows.append(met)
            print(f"  area={met['sky130_area_um2']} um2  cells={met['mapped_cells']}"
                  f"  delay={met['critical_path_delay_ps']}ps"
                  f"  depth={met['logic_depth_levels']}"
                  f"  leak={met['static_leakage_nw']}nW")

    if not rows:
        print("nothing to do")
        return
    invalid = [r for r in rows if r["sky130_area_um2"] <= 0]
    if invalid or len(rows) < 12:
        print(f"parsed {len(rows)} runs ({len(invalid)} invalid) "
              f"- CSVs written only when all 12 runs are present")
        if invalid:
            raise RuntimeError("invalid runs; delete their logs and rerun")
        return
    base_cols = ["architecture", "width", "sky130_area_um2", "mapped_cells",
                 "critical_path_delay_ps", "logic_depth_levels",
                 "static_leakage_nw", "log"]
    with (RESULTS / "sky130_baseline.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=base_cols)
        w.writeheader()
        w.writerows(rows)

    by = {(r["architecture"], r["width"]): r for r in rows}
    comp = []
    for width in WIDTHS:
        c = by[("conventional", width)]
        for arch in ("karatsuba_single", "karatsuba_recursive"):
            a = by[(arch, width)]
            comp.append({
                "width": width,
                "architecture": arch,
                "conventional_area_um2": c["sky130_area_um2"],
                "arch_area_um2": a["sky130_area_um2"],
                "area_change_percent": round(
                    100.0 * (a["sky130_area_um2"] - c["sky130_area_um2"])
                    / c["sky130_area_um2"], 2),
                "conventional_delay_ps": c["critical_path_delay_ps"],
                "arch_delay_ps": a["critical_path_delay_ps"],
                "conventional_leakage_nw": c["static_leakage_nw"],
                "arch_leakage_nw": a["static_leakage_nw"],
            })
    comp_cols = ["width", "architecture", "conventional_area_um2",
                 "arch_area_um2", "area_change_percent",
                 "conventional_delay_ps", "arch_delay_ps",
                 "conventional_leakage_nw", "arch_leakage_nw"]
    with (RESULTS / "sky130_comparison.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=comp_cols)
        w.writeheader()
        w.writerows(comp)

    print("sky130 PPA flow completed successfully.")


if __name__ == "__main__":
    sys.exit(main())
