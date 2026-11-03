"""R3: local-mismatch Monte Carlo of the calibrated comparators (TT, 1.8 V, 27 C, no width skew).

Per-device threshold mismatch follows the pinned SKY130 model's own Pelgrom term
(vth0 = vth0_nom + vth0_slope_spectre * slope_bin / sqrt(W L mult)). Because that parameter is
global per model in SPICE, each device's 1-sigma shift is first calibrated by simulation
(mismatch parameter = 1 vs. an equivalent series gate source) and then applied independently per
device and per sample through a series gate source. Only the vth0 component is modelled.

  python r3_mismatch_mc.py sigma <design>            # per-device 1-sigma calibration
  python r3_mismatch_mc.py run <design> <start> <n>  # samples seed=start..start+n-1
  python r3_mismatch_mc.py report
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np

DESKTOP = Path(__file__).resolve().parents[1]  # entry root (comparator_atlas, .deps, .tools, .cache)
sys.path.insert(0, str(DESKTOP))
from comparator_atlas.designs import circuit_text, get_design  # noqa: E402
from comparator_atlas.spice import (  # noqa: E402
    COLUMNS, SPICE_INIT, Point, Simulator, Trace, measure,
)

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "r3"
NG = Path(os.environ.get("NGSPICE_EXE")
          or next((str(p) for p in [DESKTOP / ".tools" / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"]
                   if p.is_file()), None)
          or shutil.which("ngspice") or "ngspice")
PDK = DESKTOP / ".deps" / "sky130_fd_pr"
CAL_DEADLINE = 3.5
TOL_MV = 0.2
EVAL_INPUTS_MV = (-3, -1, -0.5, 0.5, 1, 3)
DEADLINES = (0.5, 0.75, 1.0, 2.0, 3.5)
MOS = re.compile(r"^(X\w+) (\S+) (\S+) (\S+) (\S+) sky130_fd_pr__(\w+)$")


def devices(design: str):
    lines = circuit_text(get_design(design)).splitlines()
    found = []
    for i, line in enumerate(lines):
        m = MOS.match(line)
        if m:
            geo = re.match(r"\+ w=\{(.+)\} l=(\S+)", lines[i + 1])
            w = float(eval(geo.group(1), {}, {"pair_skew": 0.0}))
            found.append({"name": m.group(1), "nodes": m.group(2, 3, 4, 5), "device": m.group(6),
                          "w": w, "l": float(geo.group(2))})
    return found


def ngspice(deck: str) -> str:
    with tempfile.TemporaryDirectory(dir=HERE / "cache") as tmp:
        Path(tmp, ".spiceinit").write_text(SPICE_INIT, encoding="ascii")
        Path(tmp, "a.cir").write_text(deck, encoding="utf-8")
        r = subprocess.run([str(NG), "-b", "a.cir"], cwd=tmp, capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        if r.returncode != 0 or re.search(r"(?im)^\s*(error|fatal)\b|timestep too small", out):
            raise RuntimeError(out[-2000:])
        files = {p.name: p.read_text() for p in Path(tmp).glob("*.tsv")}
    return out, files


def sigma(design: str) -> dict:
    """Equivalent series-gate shift (V) of the PDK mismatch term at +1 sigma, per geometry."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"sigma_{design}.json"
    if path.exists():
        return json.loads(path.read_text())
    result = {}
    for d in devices(design):
        key = f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}"
        if key in result:
            continue
        p = d["device"].startswith("pfet")
        stem = f"sky130_fd_pr__{d['device']}"
        inc = "\n".join(f'.include "{f}"' for f in (
            PDK / "models" / "parameters" / "lod.spice",
            PDK / "cells" / d["device"] / f"{stem}__mismatch.corner.spice",
            PDK / "cells" / d["device"] / f"{stem}__tt.corner.spice"))
        vs = [0.9 - 0.004 * k for k in range(-10, 11)]
        body = "vdd" if p else "0"
        rows = []
        for mm in (0, 1):
            deck = (f"cal\n.option scale=1u\n{inc}\n.param {stem}__vth0_slope_spectre={mm}\n"
                    f"Vdd vdd 0 1.8\nVd d 0 {1.75 if p else 0.05}\nVg g 0 0\n"
                    f"X1 d g {'vdd' if p else '0'} {body} {stem} w={d['w']} l={d['l']}\n"
                    ".control\nset numdgt=12\n")
            for v in vs:
                deck += f"alter Vg {1.8 - v if p else v}\nop\nprint -i(Vd)\n"
            deck += "quit 0\n.endc\n.end\n"
            out, _ = ngspice(deck)
            rows.append([abs(float(x)) for x in re.findall(r"-i\(vd\) = (\S+)", out)])
        i0, i1 = np.array(rows[0]), np.array(rows[1])
        # i0 is decreasing in |vgs| order of vs (vs decreasing); find shift s with i0(v+s)=i1(v at 0.9)
        target = i1[10]
        order = np.argsort(vs)
        vg_eq = float(np.interp(target, i0[order], np.array(vs)[order]))
        # vg_eq: |Vgs| giving nominal current equal to the mismatched current at |Vgs|=0.9
        result[key] = 0.9 - vg_eq  # effective |Vth| increase (V) at +1 sigma
    path.write_text(json.dumps(result, indent=2))
    return result


def mutated_circuit(design: str, z: dict, sig: dict) -> str:
    text = circuit_text(get_design(design))
    extra = []
    for d in devices(design):
        key = f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}"
        g = d["nodes"][1]
        shift = sig[key] * z[d["name"]]  # |Vth| increase (V) for this device
        p = d["device"].startswith("pfet")
        # a weaker device equals the nominal device with |Vgs| reduced by shift
        value = shift if p else -shift
        old = f"{d['name']} {' '.join(d['nodes'])} sky130_fd_pr__{d['device']}"
        new = f"{d['name']} {d['nodes'][0]} mm_{d['name']} {d['nodes'][2]} {d['nodes'][3]} sky130_fd_pr__{d['device']}"
        text = text.replace(old, new)
        extra.append(f"Vmm{d['name']} mm_{d['name']} {g} {value:.9g}")
    return text.replace(".ends atlas", "\n".join(extra) + "\n.ends atlas")


class Sample:
    def __init__(self, design: str, seed: int, sim: Simulator, sig: dict, cond=("tt", 1.8, 27.0)):
        self.design, self.seed, self.sim = design, seed, sim
        rng = np.random.default_rng(seed)
        self.z = {d["name"]: float(rng.standard_normal()) for d in devices(design)}
        self.circuit = mutated_circuit(design, self.z, sig)
        self.base = Point(design_name=design, pair_skew=0.0, trim_code=0, differential_v=0.0,
                          corner=cond[0], vdd_v=cond[1], temperature_c=cond[2])
        self.cond = cond
        self.runs = 0

    def traces(self, points):
        header = self.sim._header(points[0]).replace(circuit_text(get_design(self.design)), self.circuit)
        assert "mm_Xinp" in header
        lines = [header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15"]
        bits = get_design(self.design).trim_bits
        for i, p in enumerate(points):
            cm = p.common_mode_ratio * p.vdd_v
            lines += [f"alter Vinp {cm + p.differential_v / 2:.12g}", f"alter Vinn {cm - p.differential_v / 2:.12g}"]
            for side, on in (("p", p.trim_code > 0), ("n", p.trim_code < 0)):
                for b in range(bits):
                    hi = on and bool(abs(p.trim_code) & (1 << b))
                    lines.append(f"alter Vt{side}{b} {p.vdd_v if hi else 0:.12g}")
            lines.append(self.sim._analysis(p, f"p{i}.tsv"))
        lines += ["quit 0", ".endc", ".end"]
        _, files = ngspice("\n".join(lines) + "\n")
        self.runs += len(points)
        out = []
        for i, p in enumerate(points):
            values = np.loadtxt(files[f"p{i}.tsv"].splitlines(), skiprows=1, dtype=np.float64)
            assert values.shape[1] == len(COLUMNS)
            out.append(Trace(p, values, f"mc{self.seed}_{i}", OUT))
        return out

    def decisions(self, requests):
        pts = [replace(self.base, differential_v=v * 1e-3, trim_code=c) for v, c in requests]
        return [measure(t, CAL_DEADLINE).decision for t in self.traces(pts)]

    def boundaries(self, codes, lo=-60.0, hi=60.0):
        """Bisect the switching input (mV) of several codes in parallel (decision at 3.5 ns)."""
        br = {c: [lo, hi] for c in codes}
        while any(b[1] - b[0] > 2 * TOL_MV for b in br.values()):
            act = [c for c in codes if br[c][1] - br[c][0] > 2 * TOL_MV]
            dec = self.decisions([((br[c][0] + br[c][1]) / 2, c) for c in act])
            for c, s in zip(act, dec):
                mid = (br[c][0] + br[c][1]) / 2
                if s > 0:
                    br[c][1] = mid
                elif s < 0:
                    br[c][0] = mid
                else:  # metastable at the calibration deadline: boundary is here
                    br[c] = [mid - TOL_MV / 2, mid + TOL_MV / 2]
        return {c: (b[0] + b[1]) / 2 for c, b in br.items()}

    def run(self) -> dict:
        mx = get_design(self.design).max_code
        b0 = self.boundaries([0])[0]
        ends = self.decisions([(0.0, -mx), (0.0, mx)])
        covered = ends[0] != ends[1] and 0 not in ends
        if covered:
            lo, hi = -mx, mx  # zero-probe decision flips between lo and hi
            dlo = ends[0]
            while hi - lo > 1:
                mid = (lo + hi) // 2
                d = self.decisions([(0.0, mid)])[0]
                if d == 0:
                    lo = hi = mid
                    break
                if d == dlo:
                    lo = mid
                else:
                    hi = mid
            cand = sorted({lo, hi})
        else:
            cand = [-mx, mx]
        bnd = self.boundaries(cand)
        code = min(bnd, key=lambda c: abs(bnd[c]))
        m = bnd[code]
        pts = [replace(self.base, differential_v=v * 1e-3, trim_code=code) for v in EVAL_INPUTS_MV]
        evals = []
        for tr in self.traces(pts):
            for dl in DEADLINES:
                ms = measure(tr, dl)
                evals.append({"v_mv": tr.point.differential_v * 1e3, "deadline_ns": dl,
                              "outcome": ms.outcome, "t_ns": ms.decision_time_ns})
        return {"design": self.design, "seed": self.seed, "cond": list(self.cond), "b0_mv": b0, "covered": covered,
                "candidates": {str(k): v for k, v in bnd.items()}, "code": code, "m_mv": m,
                "evals": evals, "transients": self.runs, "z": self.z}


def run(design: str, start: int, n: int, cond=("tt", 1.8, 27.0)) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / "cache").mkdir(exist_ok=True)
    sig = sigma(design)
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = "" if cond[0] == "tt" else f"{cond[0]}{cond[1]:g}V{cond[2]:g}C_"
    path = OUT / f"mc_{tag}{design}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = Sample(design, seed, sim, sig, cond).run()
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"{design} seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']} sims={res['transients']}", flush=True)


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def report() -> None:
    rows = [json.loads(l) for f in sorted(OUT.glob("mc_*.jsonl")) for l in f.read_text().splitlines()]
    rep = {}

    def key(r):
        c = r.get("cond", ["tt", 1.8, 27.0])
        return r["design"] if c[0] == "tt" else f"{r['design']}@{c[0]}|{c[1]:g}V|{c[2]:g}C"

    for design in sorted({key(r) for r in rows}):
        rs = [r for r in rows if key(r) == design]
        n = len(rs)
        b0 = np.array([r["b0_mv"] for r in rs])
        m = np.abs([r["m_mv"] for r in rs])
        d = {"n": n, "sigma_b0_mv": float(b0.std(ddof=1)) if n > 1 else None,
             "mean_b0_mv": float(b0.mean()), "max_abs_b0_mv": float(np.abs(b0).max()),
             "coverage": [sum(r["covered"] for r in rs), n, wilson(sum(r["covered"] for r in rs), n)],
             "residual_abs_mv": {"median": float(np.median(m)), "p90": float(np.percentile(m, 90)),
                                 "max": float(m.max())}}
        for thr in (0.5, 1.0, 3.0):
            k = int((m <= thr).sum())
            d[f"yield_abs_m_le_{thr}mV"] = [k, n, wilson(k, n)]
        outc = {}
        for v in EVAL_INPUTS_MV:
            for dl in DEADLINES:
                es = [e for r in rs for e in r["evals"] if e["v_mv"] == v and e["deadline_ns"] == dl]
                k = sum(e["outcome"] == "correct" for e in es)
                outc[f"{v:+g}mV@{dl}ns"] = {"correct": k, "wrong": sum(e["outcome"] == "wrong" for e in es),
                                            "unresolved": sum(e["outcome"] == "unresolved" for e in es),
                                            "n": len(es), "ci95": wilson(k, len(es))}
        # R1 law on random mismatch: wrong iff 0 < v/m < 1 (sign-aware)
        tp = fp = fn = tn = 0
        for r in rs:
            for e in r["evals"]:
                if e["deadline_ns"] != 3.5 or e["outcome"] == "unresolved":
                    continue
                pred = 0 < e["v_mv"] / r["m_mv"] < 1 if r["m_mv"] else False
                act = e["outcome"] == "wrong"
                tp += pred and act
                fp += pred and not act
                fn += act and not pred
                tn += not pred and not act
        d["outcomes"] = outc
        d["r1_law_at_3p5ns"] = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}
        rep[design] = d
    (OUT / "r3_report.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=1)[:6000])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sigma":
        print(json.dumps(sigma(sys.argv[2]), indent=1))
    elif cmd == "run":
        cond = (sys.argv[5], float(sys.argv[6]), float(sys.argv[7])) if len(sys.argv) > 5 else ("tt", 1.8, 27.0)
        run(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), cond)
    elif cmd == "report":
        report()
