"""r19 (MC part): the r19 candidate u6_w12_l05 (6-bit unit trim at L 0.5 um, input W 12 um) under
random mismatch, paired with r16. Same seeds and protocol as r10/r16: every device name shared with
r16 keeps its z value (the netlists differ only in W/L), so the two designs see the same draws.
Sigma per geometry comes from the PDK mismatch model (r3.sigma), cached under this design's own tag.
Only r3's ngspice wall-clock guard is scaled by 4 (no simulated result depends on it). Local only.
  python -B r19_mc_wide.py <start> <n> [corner vdd temp]
"""
import json
import subprocess
import sys

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402  (puts the desktop root on sys.path)
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import HERE, Point, Sample, Simulator, circuit_text, get_design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402
from r8_unit_trim_mc import mutate, parse  # noqa: E402
from r9_combo_mc import combo_sigma, combo_text  # noqa: E402

NAME = "u6_w12_l05"
R10 = "r10_x2_unit5b"
OUT = HERE / "out" / "r19"
DESIGNS[NAME] = Design(NAME, input_device="nfet_01v8_lvt", input_w=12, tail_w=7, trim_l=0.5, trim_bits=6)
DESIGNS[R10] = Design(R10, input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=5)
TEXT = unit_array(circuit_text(get_design(NAME)), 6)
PRIOR_NAMES = ([d["name"] for d in parse(combo_text(1.0))]
               + [d["name"] for d in parse(unit_array(circuit_text(get_design(R10)), 5))])


class _SlowerTimeout:
    def __getattr__(self, name):
        return getattr(subprocess, name)

    @staticmethod
    def run(*args, timeout=None, **kwargs):
        return subprocess.run(*args, timeout=None if timeout is None else 4 * timeout, **kwargs)


R3.subprocess = _SlowerTimeout()


class W12(R3.Sample):
    def __init__(self, seed, sim, cond, sig):
        self.design, self.seed, self.sim, self.cond, self.runs = NAME, seed, sim, cond, 0
        rng = np.random.default_rng(seed)
        z = {d["name"]: float(rng.standard_normal()) for d in R3.devices("lvt_balanced_4b")}
        rng2 = np.random.default_rng([seed, 8])
        names = [d["name"] for d in parse(TEXT)]
        for n in PRIOR_NAMES + names:
            if n not in z:
                z[n] = float(rng2.standard_normal())
        self.z = {n: z[n] for n in names}
        self.circuit = mutate(TEXT, self.z, sig)
        self.base = Point(design_name=NAME, pair_skew=0.0, trim_code=0, differential_v=0.0,
                          corner=cond[0], vdd_v=cond[1], temperature_c=cond[2])


def mc(start: int, n: int, cond) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / "cache").mkdir(exist_ok=True)
    sig = combo_sigma(TEXT, "w12_l05")
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
    path = OUT / f"mc_w12_{tag}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = W12(seed, sim, cond, sig).run()
            res["variant"] = "input_x4+unit_trim_l05+6b"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"w12 seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


if __name__ == "__main__":
    cond = (ARGS[2], float(ARGS[3]), float(ARGS[4])) if len(ARGS) > 2 else ("tt", 1.8, 27.0)
    mc(int(ARGS[0]), int(ARGS[1]), cond)
