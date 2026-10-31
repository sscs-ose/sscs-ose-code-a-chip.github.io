#!/usr/bin/env python3
"""N_IN scaling study (parameter overrides only, FF storage, N_OUT=8).
  scaling.py gen            write flow/scale/<design>_n<N>/config.json
  scaling.py run <stage> <designs-glob...>   (synth: --to Yosys.Synthesis ; layout: full flow)
  scaling.py csv            results/scaling.csv from the runs
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "flow" / "scale"
DES = {
    "dcim_core": ("dcim_core", ["dcim_core.v", "icg.v"], ["USE_LATCH=0"]),
    "sidecarcim_top": ("sidecarcim_top", ["sidecarcim_top.v", "dcim_core.v", "sidecar.v", "icg.v"],
                       ["USE_LATCH=0", "K=2", "PARALLEL=0"]),
    "dcim_8bit": ("dcim_8bit", ["dcim_core.v", "dcim_8bit.v", "icg.v"], ["USE_LATCH=0"]),
}
NS = [32, 64, 128, 256]
# second series: slots scale with rows (2 per 32 rows)
KSCALED = {64: 4, 128: 8, 256: 16}


def gen():
    for d, (top, files, par) in DES.items():
        for n in NS:
            p = S / ("%s_n%d" % (d, n))
            p.mkdir(parents=True, exist_ok=True)
            c = {"DESIGN_NAME": top, "VERILOG_FILES": ["dir::../../../rtl/" + f for f in files],
                 "SYNTH_PARAMETERS": par + ["N_IN=%d" % n], "CLOCK_PORT": "clk", "CLOCK_PERIOD": 30,
                 "FP_CORE_UTIL": 40, "FALLBACK_SDC": "dir::../../common.sdc"}
            (p / "config.json").write_text(json.dumps(c, indent=2) + "\n")


EXTRA = [(128, 4), (256, 4), (256, 8)]  # frontier points: (n_in, k)


def gen_k():
    top, files, par = DES["sidecarcim_top"]
    pts = [(n, k, "sidecarcim_topk_n%d" % n) for n, k in KSCALED.items()] +           [(n, k, "sidecarcim_topkk%d_n%d" % (k, n)) for n, k in EXTRA]
    for n, k, dn in pts:
        p = S / dn
        p.mkdir(parents=True, exist_ok=True)
        c = {"DESIGN_NAME": top, "VERILOG_FILES": ["dir::../../../rtl/" + f for f in files],
             "SYNTH_PARAMETERS": ["USE_LATCH=0", "K=%d" % k, "PARALLEL=0", "N_IN=%d" % n], "CLOCK_PORT": "clk",
             "CLOCK_PERIOD": 30, "FP_CORE_UTIL": 40, "FALLBACK_SDC": "dir::../../common.sdc"}
        (p / "config.json").write_text(json.dumps(c, indent=2) + chr(10))


def run(stage, names):
    subprocess.call(["python3", str(ROOT / "flow/sync_clock.py")])
    for nm in names:
        cfg = S / nm / "config.json"
        cmd = ["librelane", "--docker-no-tty", "--dockerized", "--run-tag", stage, str(cfg)]
        if stage.startswith("synth"):
            cmd[3:3] = ["--to", "Yosys.Synthesis"]
        log = ROOT / "flow" / "logs" / ("scale_%s_%s.log" % (nm, stage))
        with open(log, "w") as f:
            subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT)


def area(rpt):
    m = re.findall(r"Chip area for (?:top )?module '[^']+': ([\d.]+)", rpt.read_text())
    return float(m[-1])


def kof(p):
    c = json.loads((p / "config.json").read_text())
    for x in c["SYNTH_PARAMETERS"]:
        if x.startswith("K="):
            return int(x[2:])
    return ""


def csvout():
    rows = []
    for p in sorted(S.glob("*_n*")):
        d, n = p.name.rsplit("_n", 1)
        d = "sidecarcim_top" if d.startswith("sidecarcim_topk") else d
        k = kof(p) if d == "sidecarcim_top" else ""
        for tag, cg in (("synth", 0), ("synthcg", 1)):
            r = next((p / "runs" / tag).glob("*synthesis/reports/stat.rpt"), None)
            if r:
                rows.append((d, int(n), area(r), "synth", k, cg))
        for tag, cg in (("layout", 0), ("layoutcg", 1)):
            mj = p / "runs" / tag / "final" / "metrics.json"
            if mj.exists():
                rows.append((d, int(n), json.loads(mj.read_text())["design__instance__area__stdcell"], "layout", k, cg))
    rows.sort(key=lambda r: (r[5], r[3], r[0], r[1], str(r[4])))
    with open(ROOT / "results" / "scaling.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "n_in", "cell_area_um2", "stage", "k", "cg"])
        w.writerows(rows)
    print(open(ROOT / "results" / "scaling.csv").read())


if __name__ == "__main__":
    {"gen": lambda: (gen(), gen_k()), "csv": csvout}.get(sys.argv[1], lambda: run(sys.argv[2], sys.argv[3:]))()
