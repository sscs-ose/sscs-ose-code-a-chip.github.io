"""r16: the r15b 6-bit design (unit-element 6-bit trim, input W 6) -- paired mismatch MC and energy.

mc: same seeds and protocol as r10. Every device shared with r3/r9/r10 keeps its z value; bit-4
unit copies take r10's values and the extra bit-5 copies continue the same [seed, 8] stream.
r3's calibration search has no code-range check, so the 6-bit range needs no deviation here; only
r3's ngspice wall-clock guard is scaled by 4 (no simulated result depends on it).
energy: r14's nominal deck (+3 mV, 5 fF, codes 0 and +full scale) at r14's three corners.
Local only.
  python -B r16_six_bit.py mc <start> <n> [corner vdd temp]
  python -B r16_six_bit.py energy        # writes out/r16/energy.json
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402  (puts the desktop root on sys.path)
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import HERE, Point, Sample, Simulator, circuit_text, get_design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402
from r8_unit_trim_mc import mutate, parse  # noqa: E402
from r9_combo_mc import combo_sigma, combo_text  # noqa: E402

NAME = "unit6_w6"
R10 = "r10_x2_unit5b"
OUT = HERE / "out" / "r16"
DESIGNS[NAME] = Design(NAME, input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=6)
DESIGNS[R10] = Design(R10, input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=5)
TEXT = unit_array(circuit_text(get_design(NAME)), 6)
PRIOR_NAMES = ([d["name"] for d in parse(combo_text(1.0))]
               + [d["name"] for d in parse(unit_array(circuit_text(get_design(R10)), 5))])


class _SlowerTimeout:
    """The 263-device netlists are larger; scale only r3's wall-clock guard (900 s per deck) by 4."""

    def __getattr__(self, name):
        return getattr(subprocess, name)

    @staticmethod
    def run(*args, timeout=None, **kwargs):
        return subprocess.run(*args, timeout=None if timeout is None else 4 * timeout, **kwargs)


R3.subprocess = _SlowerTimeout()


class C6(Sample):
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
    sig = combo_sigma(TEXT, "combo_t1")
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
    path = OUT / f"mc_unit6_{tag}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = C6(seed, sim, cond, sig).run()
            res["variant"] = "input_x2+unit_trim_x1+6b"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"6b seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


def energy() -> None:
    import r14_energy as R14
    R14.VARIANTS[NAME] = (6, 6, "unit")
    R14.STYLE[NAME] = "unit"
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(NAME, c, code) for c in R14.CONDS for code in (0, DESIGNS[NAME].max_code)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(R14.one, jobs))
    (OUT / "energy.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    if ARGS[0] == "mc":
        cond = (ARGS[3], float(ARGS[4]), float(ARGS[5])) if len(ARGS) > 3 else ("tt", 1.8, 27.0)
        mc(int(ARGS[1]), int(ARGS[2]), cond)
    else:
        energy()
