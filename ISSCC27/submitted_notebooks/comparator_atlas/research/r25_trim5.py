"""r25: a 5-bit binary trim with the r24c equalizer, sized for range and step together.

r24c: equalizing the floating trim nodes removes the decision memory and widens the shipped 4b trim at the
hot corners (narrowest half range 18.5 -> 27.2 mV), but its hot-corner step grows (1.23 -> 1.95 mV), so the
two ~3 sigma r22 seeds stay uncovered and +-1 mV at 1 ns gets worse. r25 keeps the shipped core
(lvt input W 3, tail W 7, same latch) and the equalizer, adds one bit and lengthens the trim devices
(trim_l) so that 31 finer steps span a wider range. Designs are registered in-process only.

Pairing with r22: the core and every 4b-named trim device keep their r22 z draw; the added bit's devices
get their own stream (seed + 100000). Per-device sigma comes from the PDK mismatch model (r3.sigma).

  python -B r25_trim5.py screen [L ...]        # nominal half range / LSB at TT and the two hot corners
  python -B r25_trim5.py dnl <L>               # 63-code transfer at TT, SS 1.62 -40, FS 1.62 -40, SF/FF hot
  python -B r25_trim5.py range <L>             # nominal half range at the 45 PVT conditions
  python -B r25_trim5.py mc <L> [corner vdd temp]  # paired 40-seed mismatch MC (default sf 1.95 125)
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r24_fixmc as FX  # noqa: E402  (patches r3.mutated_circuit with the equalizer)
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402

R3, R22 = FX.R3, FX.R22
OUT = R3.HERE / "out" / "r25"
BASE = "lvt_balanced_4b"
HOT = (("sf", 1.95, 125.0), ("ff", 1.95, 125.0))
DNL_CONDS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("fs", 1.62, -40.0)) + HOT


def name(trim_l: float) -> str:
    return f"eq5_l{round(trim_l * 100):03d}"


def register(trim_l: float) -> str:
    n = name(trim_l)
    DESIGNS[n] = Design(n, input_device="nfet_01v8_lvt", input_w=3, tail_w=7, trim_l=trim_l, trim_bits=5)
    return n


for _arg in ARGS[1:]:
    try:
        register(float(_arg))
    except ValueError:
        pass


class Paired(R3.Sample):
    def __init__(self, design, seed, sim, sig, cond):
        super().__init__(design, seed, sim, sig, cond)
        rng4 = np.random.default_rng(seed)
        z4 = {d["name"]: float(rng4.standard_normal()) for d in R3.devices(BASE)}
        extra = np.random.default_rng(seed + 100000)
        self.z = {d["name"]: z4[d["name"]] if d["name"] in z4 else float(extra.standard_normal())
                  for d in R3.devices(design)}
        self.circuit = R3.mutated_circuit(design, self.z, sig)
        assert "Xeq_4" in self.circuit


def _nominal(design, cond):
    sig = {f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}": 0.0 for d in R3.devices(design)}
    s = R3.Sample(design, 0, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), sig, cond)
    assert "Xeq_4" in s.circuit
    return s


def _range(job):
    trim_l, cond = job
    design = register(trim_l)
    mx = DESIGNS[design].max_code
    b = _nominal(design, cond).boundaries([-mx, 0, mx], lo=-R22.LIMIT_MV, hi=R22.LIMIT_MV)
    return {"design": design, "trim_l": trim_l, "cond": list(cond), "b_neg_mv": b[-mx], "b0_mv": b[0],
            "b_pos_mv": b[mx], "half_range_mv": min(abs(b[-mx] - b[0]), abs(b[mx] - b[0])),
            "lsb_mv": (b[mx] - b[-mx]) / (2 * mx)}


def screen(lengths, workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(L, c) for L in lengths for c in (("tt", 1.8, 27.0),) + HOT]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, jobs))
    path = OUT / "screen.jsonl"
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
            print(f"{r['design']} {r['cond']} half {r['half_range_mv']:.1f} lsb {r['lsb_mv']:+.3f}", flush=True)


def _transfer(job):
    trim_l, cond = job
    design = register(trim_l)
    mx = DESIGNS[design].max_code
    b = _nominal(design, cond).boundaries(list(range(-mx, mx + 1)), lo=-R22.LIMIT_MV, hi=R22.LIMIT_MV)
    codes = list(range(-mx, mx + 1))
    v = np.array([b[c] for c in codes])
    steps = np.diff(v)
    lsb = (v[-1] - v[0]) / (2 * mx)
    return {"design": design, "cond": list(cond), "b_mv": {str(c): b[c] for c in codes}, "lsb_mv": lsb,
            "dnl_max_lsb": float(np.max(np.abs(steps / lsb - 1))), "max_step_mv": float(steps[np.argmax(abs(steps))]),
            "monotonic": bool(np.all(np.sign(steps) == np.sign(lsb)))}


def dnl(trim_l, workers=5):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_transfer, [(trim_l, c) for c in DNL_CONDS]))
    (OUT / f"dnl_{name(trim_l)}.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(r["cond"], f"lsb {r['lsb_mv']:+.3f} dnl {r['dnl_max_lsb']:.2f} max step {r['max_step_mv']:+.2f} "
              f"monotonic {r['monotonic']}", flush=True)


def run_range(trim_l, workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, [(trim_l, c) for c in R22.conditions()]))
    (OUT / f"range_{name(trim_l)}.json").write_text(json.dumps(rows, indent=1))
    hr = sorted(r["half_range_mv"] for r in rows)
    print("half range min/median/max", hr[0], hr[len(hr) // 2], hr[-1], flush=True)


def _seed(job):
    trim_l, seed, cond = job
    design = register(trim_l)
    sig = R3.sigma(design)
    s = Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), sig, cond)
    res = s.run()
    res["fix"] = "equalize"
    return res


def mc(trim_l, cond=HOT[0], seeds=range(40), workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    design = register(trim_l)
    R3.sigma(design)  # calibrate once, before the workers read the cache
    path = OUT / f"mc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}.jsonl"
    done = {json.loads(ln)["seed"] for ln in path.read_text().splitlines()} if path.exists() else set()
    jobs = [(trim_l, s, cond) for s in seeds if s not in done]
    with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
        for res in ex.map(_seed, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


if __name__ == "__main__":
    cmd = ARGS[0] if ARGS else ""
    if cmd == "screen":
        screen([float(x) for x in ARGS[1:]] or [1.25, 1.5, 2.0])
    elif cmd == "dnl":
        dnl(float(ARGS[1]))
    elif cmd == "range":
        run_range(float(ARGS[1]))
    elif cmd == "mc":
        mc(float(ARGS[1]), (ARGS[2], float(ARGS[3]), float(ARGS[4])) if len(ARGS) > 4 else HOT[0])
    else:
        raise SystemExit(__doc__)
