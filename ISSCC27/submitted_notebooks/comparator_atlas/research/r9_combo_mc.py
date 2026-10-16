"""r9: combined fix -- input pair x2 plus unit-element trim (x1 or x2 unit size), paired MC.

Same seeds and z values as r3/r8 (larger devices keep z, sigma follows geometry). Local only.
  python -B r9_combo_mc.py run <trim_scale> <start> <n> [corner vdd temp]
  python -B r9_combo_mc.py report
"""
import json
import re
import sys

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3
from r3_mismatch_mc import HERE, Sample, Simulator, circuit_text, get_design
from r7_trim_dnl import unit_array
from r8_unit_trim_mc import DESIGN, mutate, parse

R9 = HERE / "out" / "r9"
INPUTS = ("w={3*(1+pair_skew)}", "w={3*(1-pair_skew)}")


def combo_text(trim_scale: float) -> str:
    text = circuit_text(get_design(DESIGN))
    for s in INPUTS:
        assert text.count(s) == 1, s
        text = text.replace(s, s.replace("{3*", "{6*"))
    text = unit_array(text, get_design(DESIGN).trim_bits)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^X[ts][pn]\d", line):
            lines[i + 1] = re.sub(r"w=\{([0-9.]+)\}", lambda m: f"w={{{float(m.group(1)) * trim_scale:g}}}", lines[i + 1])
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def combo_sigma(text: str, tag: str) -> dict:
    devs = parse(text)
    orig = R3.devices
    R3.devices = lambda design: devs
    try:
        return R3.sigma(f"{DESIGN}_{tag}")
    finally:
        R3.devices = orig


class ComboSample(Sample):
    def __init__(self, seed, sim, cond, text, sig):
        super().__init__(DESIGN, seed, sim, R3.sigma(DESIGN), cond)
        names = [d["name"] for d in parse(text)]
        rng = np.random.default_rng([seed, 8])
        for n in names:
            if n not in self.z:
                self.z[n] = float(rng.standard_normal())
        self.z = {n: self.z[n] for n in names}
        self.circuit = mutate(text, self.z, sig)


def run(scale: float, start: int, n: int, cond) -> None:
    R9.mkdir(parents=True, exist_ok=True)
    text = combo_text(scale)
    sig = combo_sigma(text, f"combo_t{scale:g}")
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
    path = R9 / f"mc_combo_t{scale:g}_{tag}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = ComboSample(seed, sim, cond, text, sig).run()
            res["variant"] = f"input_x2+unit_trim_x{scale:g}"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"t{scale:g} seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


def report() -> None:
    groups = {}
    for f in sorted(R9.glob("mc_combo_*.jsonl")):
        for l in f.read_text().splitlines():
            x = json.loads(l)
            groups.setdefault(f"{x['variant']}@{'|'.join(map(str, x['cond']))}", []).append(x)
    out = {}
    for key, rows in sorted(groups.items()):
        m = np.abs([r["m_mv"] for r in rows])
        b0 = np.array([r["b0_mv"] for r in rows])
        cell = {"n": len(rows), "sigma_b0_mv": float(b0.std()), "max_abs_b0_mv": float(np.abs(b0).max()),
                "coverage": int(sum(r["covered"] for r in rows)), "abs_m_median": float(np.median(m)),
                "abs_m_max": float(m.max()), "abs_m_gt_3": int((m > 3).sum())}
        for v in (-3, 3, -1, 1):
            for dl in (0.75, 1.0, 2.0):
                o = [e["outcome"] for r in rows for e in r["evals"] if e["v_mv"] == v and e["deadline_ns"] == dl]
                cell[f"{v:+g}mV@{dl:g}ns"] = f"{o.count('correct')}/{len(o)} wrong={o.count('wrong')}"
        out[key] = cell
    (R9 / "r9_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if ARGS[0] == "run":
        cond = (ARGS[4], float(ARGS[5]), float(ARGS[6])) if len(ARGS) > 4 else ("tt", 1.8, 27.0)
        run(float(ARGS[1]), int(ARGS[2]), int(ARGS[3]), cond)
    else:
        report()
