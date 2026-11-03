"""R6: post-layout attribution and resizing on the adopted b1 extraction (C mode).

Re-simulates the archived b1 `atlas.c.spice` with the atlas testbench (5 fF loads, code 0,
pair_skew 0) and decomposes the post-layout slowdown with the R4 model
t_d = t0 + tau * ln(1 mV / |v|) fitted from +3 and +10 mV.

Variants either zero a group of extracted wiring capacitors (attribution) or rescale device
widths while keeping every extracted wiring capacitor (what-if resizing: wiring growth of a real
re-layout is NOT modelled, so resizing gains are optimistic upper bounds).

  python r6_layout_budget.py run
  python r6_layout_budget.py report
"""
import json
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import r3_mismatch_mc as r3
from r3_mismatch_mc import COLUMNS, Point, Simulator, Trace, circuit_text, get_design, measure

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "r6"
LAYOUT = (HERE.parent / "layout_single_row"
          / "v2" / "native" / "candidate")
NETLISTS = {"c": LAYOUT / "atlas.c.spice", "rc": LAYOUT / "atlas.rc.spice"}
ARCHIVE = LAYOUT.parent.parent / "analysis" / "finest-point-measurements.csv"
DESIGN = "lvt_balanced_4b"
CONDS = [("tt", 1.8, 27.0), ("fs", 1.62, -40.0), ("ss", 1.62, -40.0), ("ss", 1.62, 27.0)]
PVT45 = [(c, v, t) for c in ("tt", "ss", "ff", "sf", "fs") for v in (1.62, 1.8, 1.95) for t in (-40.0, 27.0, 125.0)]
INPUTS_MV = (3.0, 10.0)
CAP = re.compile(r"^(C\d+) (\S+) (\S+) ([\d.eE+-]+)f(?:\s*;.*)?\s*$")
DEV = re.compile(r"^(X\d+) (\S+) (\S+) (\S+) (\S+) (\S+) ad=\S+ pd=\S+ as=\S+ ps=\S+ w=(\S+) l=(\S+)$")
X, Q, TAIL = {"xp", "xn"}, {"qp", "qn"}, {"tail"}
S = {f"{s}{i}" for s in ("sp", "sn") for i in range(4)}


def touches(group):
    return lambda a, b: bool({a, b} & group)


# cap rules: (predicate on base node names, factor); first matching rule wins
VARIANTS = {
    "c_full": {},
    "no_wiring": {"caps": [(lambda a, b: True, 0.0)]},
    "no_x_wiring": {"caps": [(touches(X), 0.0)]},
    "no_q_wiring": {"caps": [(touches(Q), 0.0)]},
    "no_tail_wiring": {"caps": [(touches(X), 1.0), (touches(TAIL), 0.0)]},
    "no_s_wiring": {"caps": [(touches(X), 1.0), (touches(S), 0.0)]},
    "half_x_wiring": {"caps": [(touches(X), 0.5)]},
    "latch_p_x2": {"resize": {"latch_p": 2.0}},
    "latch_n_x2": {"resize": {"latch_n": 2.0}},
    "latch_pn_x2": {"resize": {"latch_p": 2.0, "latch_n": 2.0}},
    "input_x2": {"resize": {"input": 2.0}},
    "tail_x2": {"resize": {"tail": 2.0}},
    "no_q_to_vss": {"caps": [(lambda a, b: bool({a, b} & Q) and "vss" in (a, b), 0.0)]},
    "no_q_coupling": {"caps": [(lambda a, b: bool({a, b} & Q) and "vss" not in (a, b), 0.0)]},
    "half_q_wiring": {"caps": [(touches(Q), 0.5)]},
    "input_x1p5": {"resize": {"input": 1.5}},
    "input_x2_half_q": {"resize": {"input": 2.0}, "caps": [(touches(Q), 0.5)]},
    "rc_full": {"mode": "rc"},
    "rc_input_x1p5": {"mode": "rc", "resize": {"input": 1.5}},
    "rc_input_x2": {"mode": "rc", "resize": {"input": 2.0}},
    "rc_input_x2_half_q": {"mode": "rc", "resize": {"input": 2.0}, "caps": [(touches(Q), 0.5)]},
}
ATTRIB = [n for n, s in VARIANTS.items() if s.get("mode", "c") == "c"]
PVT_VARIANTS = ["rc_full", "rc_input_x2", "rc_input_x1p5", "rc_input_x2_half_q"]


def base(node: str) -> str:
    return node.split(".")[0]


def role(nodes, dev):
    d, g, s = (base(n) for n in nodes[:3])
    ends = {d, s}
    if dev.endswith("pfet_01v8") and g in Q and "vdd" in ends and (ends - {"vdd"}) <= Q:
        return "latch_p"
    if dev.endswith("nfet_01v8") and g in Q and ends & Q and ends & X:
        return "latch_n"
    if dev.endswith("lvt") and g in {"vinp", "vinn"} and "tail" in ends:
        return "input"
    if g == "clk" and "tail" in ends:
        return "tail"
    return None


def variant_netlist(spec: dict) -> str:
    out = []
    counts = {}
    for line in NETLISTS[spec.get("mode", "c")].read_text().splitlines():
        m = CAP.match(line)
        if m:
            n1, n2, c = m.group(2), m.group(3), float(m.group(4))
            for pred, factor in spec.get("caps", []):
                if pred(base(n1), base(n2)):
                    c *= factor
                    break
            if c > 0:
                out.append(f"{m.group(1)} {n1} {n2} {c:.6g}f")
            continue
        m = DEV.match(line)
        if m and "resize" in spec:
            nodes = m.group(2, 3, 4, 5)
            dev = m.group(6)
            r = role(nodes, dev)
            k = spec["resize"].get(r)
            if k:
                w = float(m.group(7)) * k
                counts[r] = counts.get(r, 0) + 1
                line = (f"{m.group(1)} {' '.join(nodes)} {dev} ad={0.29 * w:.6g} pd={2 * (0.29 + w):.6g} "
                        f"as={0.29 * w:.6g} ps={2 * (0.29 + w):.6g} w={w:.6g} l={m.group(8)}")
        if line.startswith(".subckt atlas"):
            out += [line, "+ params: pair_skew=0"]
            continue
        out.append(line)
    if "resize" in spec:
        expect = {"latch_p": 2, "latch_n": 2, "input": 2, "tail": 1}
        for r in spec["resize"]:
            assert counts.get(r) == expect[r], (r, counts)
    return "\n".join(out) + "\n"


SIM = Simulator(HERE / "cache" / "r6_unused", workers=1)
SCHEM = circuit_text(get_design(DESIGN))


def simulate(name: str, cond, v_mv: float) -> dict:
    p = Point(design_name=DESIGN, corner=cond[0], vdd_v=cond[1], temperature_c=cond[2],
              differential_v=v_mv * 1e-3, pair_skew=0.0, trim_code=0, load_ff=5.0, max_step_ps=5.0)
    header = SIM._header(p)
    if name != "schematic":
        assert SCHEM in header
        header = header.replace(SCHEM, variant_netlist(VARIANTS[name]))
    deck = "\n".join([header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15",
                      SIM._analysis(p, "p0.tsv"), "quit 0", ".endc", ".end"]) + "\n"
    _, files = r3.ngspice(deck)
    values = np.loadtxt(files["p0.tsv"].splitlines(), skiprows=1, dtype=np.float64)
    assert values.shape[1] == len(COLUMNS)
    tr = Trace(p, values, f"r6_{name}", OUT)
    ms = measure(tr, 3.5)
    return {"variant": name, "cond": list(cond), "v_mv": v_mv, "outcome": ms.outcome,
            "t_ns": ms.decision_time_ns, "energy_fj": getattr(ms, "core_energy_fj", None),
            "at": {str(d): measure(tr, d).outcome for d in (1.0, 2.0)}}


def _execute(path: Path, jobs, threads: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / "cache").mkdir(exist_ok=True)
    with ThreadPoolExecutor(threads) as ex, path.open("a") as f:
        for res in ex.map(lambda j: simulate(*j), jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["variant"], res["cond"], res["v_mv"], res["at"], flush=True)


def _done(path: Path) -> set:
    if not path.exists():
        return set()
    return {(r["variant"], tuple(r["cond"]), r["v_mv"]) for r in map(json.loads, path.read_text().splitlines())}


def run() -> None:
    path = OUT / "r6_runs.jsonl"
    done = _done(path)
    jobs = [(n, c, v) for c in CONDS for n in ["schematic", *ATTRIB] for v in INPUTS_MV
            if (n, tuple(c), v) not in done]
    _execute(path, jobs, 4)


def pvt45(threads: int = 4) -> None:
    path = OUT / "r6_pvt45.jsonl"
    done = _done(path)
    jobs = [(n, c, v) for n in PVT_VARIANTS for c in PVT45 for v in (-10.0, -3.0, 3.0, 10.0)
            if (n, tuple(c), v) not in done]
    _execute(path, jobs, threads)


def pvt45_report() -> None:
    import csv
    from collections import Counter
    rows = [json.loads(l) for l in (OUT / "r6_pvt45.jsonl").read_text().splitlines()]
    arch = {}
    for r in csv.DictReader(ARCHIVE.open()):
        if r["layout"] == "candidate" and r["mode"] == "rc":
            key = (r["corner"], float(r["vdd_v"]), float(r["temperature_c"]), float(r["signed_input_mv"]))
            arch.setdefault(key, {})[r["deadline_ns"]] = r["outcome"]
    rep = {}
    for n in PVT_VARIANTS:
        rs = [r for r in rows if r["variant"] == n]
        d = {"n": len(rs)}
        for dl in ("1.0", "2.0"):
            d[f"at_{dl}ns"] = dict(Counter(r["at"][dl] for r in rs))
            d[f"fail_{dl}ns"] = sorted({"/".join(map(str, r["cond"])) for r in rs if r["at"][dl] != "correct"})
        d["energy_mean_fj"] = float(np.mean([r["energy_fj"] for r in rs])) if rs else None
        d["worst_t_ns"] = max((r["t_ns"] for r in rs if r["t_ns"] is not None), default=None)
        if n == "rc_full":
            agree = sum(arch[(*r["cond"], r["v_mv"])][dl] == r["at"][dl] for r in rs for dl in ("1.0", "2.0"))
            d["archive_agreement"] = [agree, 2 * len(rs)]
        rep[n] = d
    (OUT / "r6_pvt45_report.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=1))


def report() -> None:
    rows = [json.loads(l) for l in (OUT / "r6_runs.jsonl").read_text().splitlines()]
    t = {(r["variant"], tuple(r["cond"]), r["v_mv"]): r for r in rows}
    rep = {}
    for c in CONDS:
        for n in ["schematic", *ATTRIB]:
            a, b = t.get((n, c, 3.0)), t.get((n, c, 10.0))
            if not a or not b or a["t_ns"] is None or b["t_ns"] is None:
                continue
            tau = (a["t_ns"] - b["t_ns"]) / math.log(10 / 3)
            t0 = a["t_ns"] + tau * math.log(3)
            vstar = math.exp((t0 - 1.0) / tau) if tau > 0 else None
            rep[f"{c[0]}|{c[1]:g}|{c[2]:g}|{n}"] = {
                "t3_ns": a["t_ns"], "t10_ns": b["t_ns"], "tau_ps": tau * 1e3, "t0_ns": t0,
                "vstar_1ns_mv": vstar, "energy3_fj": a["energy_fj"]}
    (OUT / "r6_report.json").write_text(json.dumps(rep, indent=2))
    for k, v in rep.items():
        e = f"{v['energy3_fj']:.0f}" if v["energy3_fj"] else "-"
        print(f"{k:34s} t3={v['t3_ns']:.3f} t10={v['t10_ns']:.3f} tau={v['tau_ps']:6.1f} "
              f"t0={v['t0_ns']:.3f} v*1ns={v['vstar_1ns_mv']:8.2f} E={e}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "pvt45":
        pvt45(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    else:
        {"run": run, "report": report, "pvt45_report": pvt45_report}[cmd]()
