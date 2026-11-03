"""r10: input pair x2 + unit-element trim x1 + 5 bits (fine LSB, full range), paired MC.

Registers an in-process design variant (no source file is modified). z values match r3/r9 for
all shared device names; the extra bit-4 unit copies continue the r9 [seed, 8] stream. Local only.
  python -B r10_combo5b.py run <start> <n> [corner vdd temp]
"""
import json
import sys

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3
from comparator_atlas.designs import DESIGNS, Design
from r3_mismatch_mc import HERE, Point, Sample, Simulator, circuit_text, get_design
from r7_trim_dnl import unit_array
from r8_unit_trim_mc import mutate, parse
from r9_combo_mc import R9, combo_sigma, combo_text

NAME = "r10_x2_unit5b"
DESIGNS[NAME] = Design(NAME, input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=5)
TEXT = unit_array(circuit_text(get_design(NAME)), 5)
R9_NAMES = [d["name"] for d in parse(combo_text(1.0))]


class C5(Sample):
    def __init__(self, seed, sim, cond, sig):
        self.design, self.seed, self.sim, self.cond, self.runs = NAME, seed, sim, cond, 0
        rng = np.random.default_rng(seed)
        z = {d["name"]: float(rng.standard_normal()) for d in R3.devices("lvt_balanced_4b")}
        rng2 = np.random.default_rng([seed, 8])
        names = [d["name"] for d in parse(TEXT)]
        for n in R9_NAMES + names:
            if n not in z:
                z[n] = float(rng2.standard_normal())
        self.z = {n: z[n] for n in names}
        self.circuit = mutate(TEXT, self.z, sig)
        self.base = Point(design_name=NAME, pair_skew=0.0, trim_code=0, differential_v=0.0,
                          corner=cond[0], vdd_v=cond[1], temperature_c=cond[2])


def run(start: int, n: int, cond) -> None:
    R9.mkdir(parents=True, exist_ok=True)
    sig = combo_sigma(TEXT, "combo_t1")
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
    path = R9 / f"mc_combo_5b_{tag}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = C5(seed, sim, cond, sig).run()
            res["variant"] = "input_x2+unit_trim_x1+5b"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"5b seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


if __name__ == "__main__":
    cond = (ARGS[3], float(ARGS[4]), float(ARGS[5])) if len(ARGS) > 3 else ("tt", 1.8, 27.0)
    run(int(ARGS[1]), int(ARGS[2]), cond)
