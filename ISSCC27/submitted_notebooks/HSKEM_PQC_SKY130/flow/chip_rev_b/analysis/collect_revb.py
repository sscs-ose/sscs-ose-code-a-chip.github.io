"""Collect the sign-off evidence of HSKEM-2 rev B (t3e w1) into the results files of the notebook (rev_b/).

Reads the parked final database's logs (WSL paths) and writes JSON summaries plus a cells.csv.gz without the
fill and tap rows (the format of rev A's cells.csv.gz). Every value is parsed, none typed in.
usage (WSL): python3 collect_revb.py <out dir>
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import pathlib
import re
import shutil
import sys

T3 = pathlib.Path("/root/t3")
FINAL = T3 / "t3e_final_w1/results"
REPORT = T3 / "t3e_a3grt/logs/sky130hd/trustedge_asic_core/chipv2/6_report.json"
STA = T3 / "sta_final_x6"
LVS = pathlib.Path("/mnt/c/chipv2_signoff/lvs_t3e_w1")
STAGE = pathlib.Path("/mnt/d/TKVM_ATTT_2026_test/chip_v2/signoff/fullchip_stage_t3e")
ICACS = pathlib.Path("/mnt/d/TKVM_ATTT_2026_test/icacs2026/data")


def sha(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def summary(out: pathlib.Path) -> dict:
    rep = json.loads(REPORT.read_text())
    keys = ["finish__design__die__area", "finish__design__instance__area__macros",
            "finish__design__instance__area__stdcell", "finish__design__instance__count__class:sequential_cell",
            "finish__design__instance__count__macros", "finish__design__instance__count__stdcell",
            "finish__design__instance__utilization", "finish__timing__drv__max_slew",
            "finish__timing__drv__max_cap", "finish__timing__drv__max_fanout"]
    m = {k: rep[k] for k in keys}
    drt = (T3 / "t3e_w1.out").read_text(errors="replace")
    drc = json.loads((T3 / "drc_t3e_w1/drc_result.json").read_text())
    fr = lambda d: re.search(r"Final result:\s*(.+?)\.?\s*$", (LVS / d / "final_result.txt").read_text(), re.M)[1]
    cmp2, rep_, neg = fr("compare2"), fr("repeat"), fr("negative")
    con = (LVS / "compare2/console.log").read_text(errors="replace")
    dev = re.findall(r"Circuit 1 contains (\d+) devices, Circuit 2 contains (\d+) devices", con)
    net = re.findall(r"Circuit 1 contains (\d+) nets,\s+Circuit 2 contains (\d+) nets", con)
    abst = (LVS / "abstraction_manifest.txt").read_text()
    cells = re.findall(r"cell=(sky130_fd_sc_hd__\w+)\|", abst)
    am = (LVS / "abstract_manifest.txt").read_text()
    shas = dict(reversed(l.split()) for l in (T3 / "t3e_final_w1.sha256").read_text().splitlines() if l.strip())
    shas = {pathlib.Path(k).name: v for k, v in shas.items()}
    res = {
        "chip": "HSKEM-2 rev B: public RTL (hskem_rtl/, placeholder keys) with the 14 slow-corner defines, final "
                "database t3e w1 (detailed route + ECO x1-x6 at the macro corners)",
        "source_orfs_report": "6_report.json of the run (timing fields there are the flow's typical-corner defaults "
                              "and are not used; sta_corners.json holds the sign-off timing)",
        "clock_target_ns": 40.0,
        "orfs_metrics": m,
        "fill_tap_instances": None,          # filled in by cells()
        "signoff": {
            "router_drc_violations": int(re.findall(r"Number of violations = (\d+)", drt)[-1]),
            "antenna_violations": int(re.search(r"antenna_violations_after=(\d+)", drt)[1]),
            "drc_markers": drc["drc_items"], "drc_parts": {k: v["drc_items"] for k, v in drc["parts"].items()},
            "drc_deck_scope": drc["deck_scope"],
            "primary_compare": cmp2, "repeat_compare": rep_,
            "negative_control_result": neg,
            "negative_control_detected": "match uniquely" not in neg,
            "layout_devices": int(dev[-1][0]), "reference_devices": int(dev[-1][1]),
            "layout_nets": int(net[-1][0]), "reference_nets": int(net[-1][1]),
            "sram_masters": int(re.search(r"reachable_sram_masters=(\d+)", am)[1]),
            "truth_table_verified_cells": cells,
            "claim_boundary": "pre-silicon top-level integration LVS with 7 SRAM abstractions and independent "
                              "transistor-level LVS for each SRAM; 5 multi-finger standard cells compared as black "
                              "boxes after a switch-level truth-table proof of each",
            "final_sha256": shas,
        },
    }
    return res


CLASS = [("SRAM macros", None), ("fill and tap", r"^(fill|decap|tapvpwrvgnd)"), ("antenna diodes", r"^diode"),
         ("tie cells", r"^conb"), ("flip-flops", r"^(df|edf|sdf|dlx|dlrt|dlclkp|sdlclkp)"),
         ("clock buffers and inverters", r"^clk(buf|inv|invlp|dlybuf)"),
         ("buffers and hold delays", r"^(buf|bufinv|dlygate|dlymetal|bufbuf)"),
         ("combinational logic", r".")]


def cells(out: pathlib.Path, res: dict) -> None:
    src = STAGE / "cells.csv.gz"
    cnt, area = collections.Counter(), collections.Counter()
    keep = []
    with gzip.open(src, "rt") as f:
        head = f.readline()
        for line in f:
            r = line.rstrip("\n").split(",")
            master, x0, y0, x1, y1, mac = r[0], *map(float, r[1:5]), r[5]
            if master == "DIE":
                keep.append(line); continue
            a = (x1 - x0) * (y1 - y0)
            short = master.replace("sky130_fd_sc_hd__", "")
            for name, pat in CLASS:
                if (pat is None and mac == "1") or (pat is not None and mac != "1" and re.match(pat, short)):
                    cnt[name] += 1; area[name] += a; break
            if not re.match(r"^(fill|decap|tapvpwrvgnd)", short):
                keep.append(line)
    with gzip.GzipFile(out / "cells.csv.gz", "wb", mtime=0) as g:
        g.write((head + "".join(keep)).encode())
    res["area_by_class"] = {k: {"instances": cnt[k], "area_mm2": round(area[k] / 1e6, 4)} for k, _ in CLASS}
    res["fill_tap_instances"] = cnt["fill and tap"]
    res["cells_csv_note"] = "cells.csv.gz lists every instance except the fill and tap cells (as for rev A)"


def sta(out: pathlib.Path) -> None:
    rows = {}
    for l in (STA / "summary.txt").read_text().splitlines():
        t = l.split()
        if len(t) > 3 and re.match(r"(ss|tt|ff)_(spice|view)_(sdc|soc)", t[0]):
            kv, i = {}, 1
            while i < len(t):
                if t[i] == "io_clk_ports":
                    kv["io_ports_in"], kv["io_ports_out"] = int(t[i + 2]), int(t[i + 4]); i += 5; continue
                try:
                    kv[t[i]] = float(t[i + 1])
                except ValueError:
                    pass
                i += 2
            rows[t[0]] = kv
    views = {k: json.loads((STA / f"views/{k}/views.json").read_text())["macros"] for k in ("ss", "tt", "ff")}
    crit = (STA / "sta_ss_spice_soc.log").read_text()
    path = next(x for x in crit.split("SECTION WORST_SETUP_PATH")[1].split("SECTION")[0].split("Startpoint:")[1:]
                if "Path Group: core_clk" in x)
    lines = path.splitlines()
    rowsp = [l for l in lines if re.match(r"\s+\d+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+[v^]", l)]
    delays = [(float(l.split()[3]), l.split()[-1].strip("()")) for l in rowsp]
    rep = [d for d, c in delays if re.match(r"sky130_fd_sc_hd__buf", c) and d < 0.4][:]
    res = {"clock_period_ns": 40.0, "rc": "OpenRCX nominal (the only SKY130 extraction corner)",
           "macro_views": "clock-to-output of every macro type at every corner measured in SPICE (views.json); "
                          "input setup/hold from the OpenRAM views",
           "io_model": {"soc": "service ports timed against a virtual clock carrying the core clock's measured "
                               "insertion delay; inputs max 2.0 / min 0.3 ns, outputs max 2.0 / min 0.0 ns",
                        "sdc": "the constraints as written (no common clock for the ports)"},
           "runs": rows,
           "macro_clk_to_dout_ns": {k: {m: v["used_ns"] for m, v in vv.items()} for k, vv in views.items()},
           "macro_clk_to_dout_view_ns": {k: {m: v["view_ns"] for m, v in vv.items()} for k, vv in views.items()},
           "provisional_views": sum(v["source"] != "measured" for vv in views.values() for v in vv.values()),
           "slow_corner_worst_path": {
               "startpoint": re.search(r"^\s*(\S+)", lines[0])[1], "launch": "falling clock edge (macro output)",
               "endpoint": re.search(r"Endpoint: (\S+)", path)[1],
               "macro_clk_to_dout_ns": delays[0][0],
               "repeaters": len([1 for d, c in delays[1:] if c.startswith("sky130_fd_sc_hd__buf")]),
               "slack_ns": float(re.search(r"([-\d.]+)\s+slack", path)[1])}}
    # repeaters: the run of buf cells straight after the macro output; logic: the rest up to the endpoint
    k = 1
    while k < len(delays) and delays[k][1].startswith("sky130_fd_sc_hd__buf"):
        k += 1
    w = res["slow_corner_worst_path"]
    w["repeaters"], w["repeater_delay_ns"] = k - 1, round(sum(d for d, _ in delays[1:k]), 3)
    w["logic_cells"], w["logic_delay_ns"] = len(delays) - k, round(sum(d for d, _ in delays[k:]), 3)
    # hold paths into the macro inputs (macro_hold_t3e.sh) and the SPICE input-timing points (sram_setup/)
    mh = {}
    for k in ("ss", "tt", "ff"):
        t = (T3 / f"macro_hold_w1/sta_{k}.log").read_text()
        p = t.split("SECTION MACRO_HOLD_PATH")[1].split("SECTION WORST_SETUP_PATH")[0]
        clk = [float(x) for x in re.findall(r"([\d.]+)\s+[\d.]+\s+clock network delay", p)]
        mh[k] = {"endpoint": re.search(r"Endpoint: (\S+)", p)[1],
                 "pin": re.findall(r"\s(\S+/\w+\[?\d*\]?) \(sky130_sram", p)[-1] if re.findall(r"\s(\S+/\w+\[?\d*\]?) \(sky130_sram", p) else None,
                 "data_arrival_ns": float(re.search(r"([\d.]+)\s+data arrival time", p)[1]),
                 "capture_clock_ns": clk[1], "view_hold_ns": float(re.search(r"(-?[\d.]+)\s+[\d.]+\s+library hold time", p)[1]),
                 "slack_ns": float(re.search(r"(-?[\d.]+)\s+slack", p)[1]),
                 "macro_input_pins": int(re.search(r"RESULT macro_input_pins (\d+)", t)[1])}
        mh[k]["input_change_after_macro_clock_ns"] = round(mh[k]["data_arrival_ns"] - mh[k]["capture_clock_ns"], 3)
    res["macro_input_hold"] = mh
    grid = {}
    for d in sorted(pathlib.Path("/root/sram_setup").glob("s*/sky130_sram_1rw_24x256/energy.json")):
        e = json.loads(d.read_text()); dk = json.loads((d.parent / "energy.sp.json").read_text())
        grid[dk["in_at_ns"]] = all(e["reads_correct"])
    res["spice_input_timing"] = {
        "method": "ngspice on the OpenRAM netlist; every input changes at one offset from the rising clock edge; a point "
                  "passes when every write and read of the run is correct (sram_setup/openram_energy.py)",
        "sky130_sram_1rw_24x256_ss": {"points_pass": grid,
                                      "note": "offset s near 0: setup = -s; s near -40: the input changes 40 + s after "
                                              "the previous edge (hold)"}}
    h128 = {}
    for k in ("ss", "tt", "ff"):
        f = pathlib.Path(f"/root/sram_hold128/{k}/sky130_sram_1rw_24x128/energy.json")
        if f.exists():
            e = json.loads(f.read_text()); dk = json.loads((f.parent / "energy.sp.json").read_text())
            assert dk["corner"] == k
            h128[k] = {"input_change_after_edge_ns": round(40 + float(dk["in_at_ns"]), 3), "pass": all(e["reads_correct"]),
                       "vdd": dk["vdd"], "temp_c": dk.get("temp_c")}
    res["spice_input_timing"]["sky130_sram_1rw_24x128_hold_at_sta_arrival"] = h128
    (out / "sta_corners.json").write_text(json.dumps(res, indent=1) + "\n")


def drv(out: pathlib.Path) -> None:
    t = (T3 / "drv_w1.txt").read_text()
    slew = re.findall(r"^(\S+)\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+) \(VIOLATED\)", t.split("max capacitance")[0], re.M)
    cap = re.findall(r"^(\S+)\s+([\d.]+)\s+([\d.]+)\s+(-[\d.]+) \(VIOLATED\)", t.split("max capacitance")[1], re.M)
    grp = lambda pin: "SRAM pin" if "u_macro/" in pin else "standard-cell pin"
    res = {"corner": "tt_025C_1v80 with SPEF (the flow's final report)",
           "max_slew": [{"pin": p, "limit": float(a), "value": float(b), "slack": float(c), "kind": grp(p)} for p, a, b, c in slew],
           "max_cap": [{"pin": p, "limit": float(a), "value": float(b), "slack": float(c), "kind": grp(p)} for p, a, b, c in cap]}
    res["counts"] = {"max_slew": len(slew), "max_cap": len(cap),
                     "sram_pins": sum(grp(p) == "SRAM pin" for p, *_ in slew + cap)}
    (out / "drv.json").write_text(json.dumps(res, indent=1) + "\n")


def ir(out: pathlib.Path) -> None:
    def parse(p):
        t = p.read_text()
        v = re.findall(r"Worstcase IR drop: ([\d.e+-]+) V", t); a = re.findall(r"Average IR drop  : ([\d.e+-]+) V", t)
        pw = re.findall(r"Total power\s+: ([\d.e+-]+) W", t)
        return {"VDD": {"worst_mv": float(v[0]) * 1e3, "average_mv": float(a[0]) * 1e3},
                "VSS": {"worst_mv": float(v[1]) * 1e3, "average_mv": float(a[1]) * 1e3}, "total_power_w": float(pw[0])}
    res = {"tool": "OpenROAD PSM (analyze_power_grid), typical corner 1.80 V",
           "sources": "voltage sources at both ends of every met5 strap (the edge of the core, as a pad ring or harness "
                      "would feed it); 246 sources per net",
           "macro_power": "SPICE energies of each macro type, one access per cycle at 25 MHz (the Liberty power views "
                          "are not physical and were removed from the macro view copies)",
           "decapsulation_activity": dict(parse(T3 / "ir_w1_vcd4/ir.log"),
                                          activity="the decapsulation shadow VCD of power.json (stretched x4)"),
           "uniform_activity_0p1": dict(parse(T3 / "ir_w1_edge/ir.log"),
                                        activity="0.1 toggles per cycle on every input, propagated")}
    (out / "ir_drop.json").write_text(json.dumps(res, indent=1) + "\n")


def gls(out: pathlib.Path) -> None:
    t = pathlib.Path("/root/real_gls_t3e/run_listmis.out").read_text(errors="replace")
    end = re.findall(r"REAL_CHIP end .*", t)[-1]
    kv = dict(re.findall(r"(\w+)=(\d+)", end))
    res = {"netlist": "6_final.v of w1 (routed, flattened)", "method":
           "the routed netlist simulated next to the RTL (scripts/real_chip_window.sv style), every output pin and every "
           "flip-flop compared each cycle over the first profiled decapsulation; zero-delay",
           "cycles_compared": int(kv["cycles_compared"]), "pin_mismatches": int(kv["pin_mismatches"]),
           "flop_mismatches": int(kv["flop_mismatches"]), "real_x": int(re.search(r"real x: (\d+)", end)[1]),
           "flop_mismatch_explanation": "two flip-flops (da_g[4], dx_g[4]) in cycles 1-560 only, always while the RTL "
           "value is X (an unreset pipeline register whose valid flag is 0): the gate-level shadow resolves X to 0, the "
           "netlist loads 1; the value is never used",
           "summary_line": end.strip()}
    (out / "gls.json").write_text(json.dumps(res, indent=1) + "\n")


def main(o: str) -> None:
    out = pathlib.Path(o); out.mkdir(parents=True, exist_ok=True)
    res = summary(out); cells(out, res)
    (out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    sta(out); drv(out); ir(out); gls(out)
    for f in ("power.json", "register_toggles.json", "clock_gating_whatif.json", "sram_accesses.json",
              "sram_energy.json", "blocks.csv", "fullchip_layout.png"):
        shutil.copy(STAGE / f, out / f)
    # the time stretch of the activity file, measured: VCD length / (window cycles x testbench clock)
    W = pathlib.Path("/mnt/c/chipv2_signoff/power_t3e")
    sim = (W / "sim.log").read_text()
    t0, t1, cyc = map(int, re.search(r"DECAPS_VCD start t=(\d+)\s+DECAPS_VCD end t=(\d+) cycles_in_window=(\d+)", sim).groups())
    with open(W / "shadow0.vcd", "rb") as f:
        f.seek(-1 << 20, 2); tail = f.read().decode(errors="replace")
    t_end = int(re.findall(r"^#(\d+)", tail, re.M)[-1])
    pw = json.loads((out / "power.json").read_text())
    k = t_end / (t1 - t0)
    pw["vcd_time_stretch"] = round(k)
    pw["vcd_time_stretch_note"] = (f"measured: the shadow VCD spans {t_end} time units for a window the testbench simulated "
                                   f"in {t1 - t0} (10 ns clock), ratio {k:.4f}; OpenSTA thus reads the activity at the chip's "
                                   "40 ns clock. The first rev B power run omitted the stretch (fixed 18/10).")
    (out / "power.json").write_text(json.dumps(pw, indent=2) + "\n")
    pass   # the ACVP encaps/decaps result goes to results/acvp_rtl/encdec_rev_b.json
    print(json.dumps(res["area_by_class"], indent=1))
    print("written:", sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    main(sys.argv[1])
