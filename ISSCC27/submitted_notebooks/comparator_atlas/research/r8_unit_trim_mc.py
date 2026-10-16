"""r8: paired mismatch MC of lvt_balanced_4b with a unit-element trim array.

Same seeds as r3, so every device that exists in both circuits keeps its z value;
the extra unit copies draw independent z from a separate stream. Local only.
  python -B r8_unit_trim_mc.py run <start> <n> [corner vdd temp]
  python -B r8_unit_trim_mc.py report
"""
import json
import re
import sys

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
from r3_mismatch_mc import (HERE, MOS, OUT, Sample, Simulator, circuit_text, get_design, sigma, wilson)
from r7_trim_dnl import unit_array

DESIGN = "lvt_balanced_4b"
R8 = HERE / "out" / "r8"


def parse(text: str):
    lines = text.splitlines()
    found = []
    for i, line in enumerate(lines):
        m = MOS.match(line)
        if m:
            geo = re.match(r"\+ w=\{(.+)\} l=(\S+)", lines[i + 1])
            w = float(eval(geo.group(1), {}, {"pair_skew": 0.0}))
            found.append({"name": m.group(1), "nodes": m.group(2, 3, 4, 5), "device": m.group(6),
                          "w": w, "l": float(geo.group(2))})
    return found


def mutate(text: str, z: dict, sig: dict) -> str:
    extra = []
    for d in parse(text):
        shift = sig[f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}"] * z[d["name"]]
        value = shift if d["device"].startswith("pfet") else -shift
        old = f"{d['name']} {' '.join(d['nodes'])} sky130_fd_pr__{d['device']}"
        new = f"{d['name']} {d['nodes'][0]} mm_{d['name']} {d['nodes'][2]} {d['nodes'][3]} sky130_fd_pr__{d['device']}"
        assert text.count(old) == 1, old
        text = text.replace(old, new)
        extra.append(f"Vmm{d['name']} mm_{d['name']} {d['nodes'][1]} {value:.9g}")
    return text.replace(".ends atlas", "\n".join(extra) + "\n.ends atlas")


class UnitSample(Sample):
    def __init__(self, seed, sim, sig, cond):
        super().__init__(DESIGN, seed, sim, sig, cond)
        text = unit_array(circuit_text(get_design(DESIGN)), get_design(DESIGN).trim_bits)
        names = [d["name"] for d in parse(text)]
        rng = np.random.default_rng([seed, 8])
        for n in names:
            if n not in self.z:
                self.z[n] = float(rng.standard_normal())
        self.z = {n: self.z[n] for n in names}
        self.circuit = mutate(text, self.z, sig)


def run(start: int, n: int, cond) -> None:
    R8.mkdir(parents=True, exist_ok=True)
    (HERE / "cache").mkdir(exist_ok=True)
    sig = sigma(DESIGN)
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
    path = R8 / f"mc_unit_{tag}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = UnitSample(seed, sim, sig, cond).run()
            res["trim"] = "unit"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"unit seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


def report() -> None:
    def load(pattern):
        d = {}
        for f in pattern:
            for l in f.read_text().splitlines():
                x = json.loads(l)
                d[(tuple(x.get("cond", ["tt", 1.8, 27.0])), x["seed"])] = x
        return d
    unit = load(sorted(R8.glob("mc_unit_*.jsonl")))
    binary = load(sorted(OUT.glob("mc_*lvt_balanced_4b_*.jsonl")))
    out = {}
    for cond in sorted({k[0] for k in unit}):
        keys = sorted(k for k in unit if k[0] == cond)
        res = {}
        for name, src in (("unit", unit), ("binary", binary)):
            rows = [src[k] for k in keys if k in src]
            if len(rows) != len(keys):
                continue
            m = np.abs([r["m_mv"] for r in rows])
            cell = {"n": len(rows), "coverage": sum(r["covered"] for r in rows),
                    "abs_m_median": float(np.median(m)), "abs_m_max": float(m.max()),
                    "abs_m_gt_3": int((m > 3).sum())}
            for v in (-3, 3, -1, 1):
                for dl in (1.0, 2.0):
                    o = [e["outcome"] for r in rows for e in r["evals"] if e["v_mv"] == v and e["deadline_ns"] == dl]
                    k = o.count("correct")
                    cell[f"{v:+g}mV@{dl:g}ns"] = f"{k}/{len(o)} wrong={o.count('wrong')}"
            res[name] = cell
        out["|".join(map(str, cond))] = res
    (R8 / "r8_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if ARGS[0] == "run":
        cond = (ARGS[3], float(ARGS[4]), float(ARGS[5])) if len(ARGS) > 3 else ("tt", 1.8, 27.0)
        run(int(ARGS[1]), int(ARGS[2]), cond)
    else:
        report()
