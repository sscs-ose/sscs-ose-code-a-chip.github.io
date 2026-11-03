"""r26: scale the input pair (and tail) of the 5b + equalize trim to buy a finer trim step.

r25: 5b + equalize (trim L 1) covers every r22 seed at the hot corners, but +-1 mV stays at 68-71/80 because
the hot-corner step is ~2 mV; a longer trim device cannot give a finer step (finding 10). The trim step is
set by the trim device's pull-down against the input pair's, so widening the input pair by k (tail too, at the
same current density) should shrink the step ~1/k while the offset sigma shrinks only ~1/sqrt(k).
Designs (registered in-process only): s<bits>_k<k*100>: lvt input W 3k, tail W 7k, trim L 1, equalizer.

  python -B r26_scale.py screen <bits> k [k ...]   # end-point half range / LSB at TT and the two hot corners
  python -B r26_scale.py dnl <bits> <k>            # full transfer at TT, SS/FS 1.62 V -40 C, SF/FF hot
  python -B r26_scale.py range <bits> <k>          # nominal half range at the 45 r22 conditions
  python -B r26_scale.py mc <bits> <k> [corner vdd temp]   # paired 40-seed MC (default sf 1.95 125)
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r25_trim5 as T  # noqa: E402  (imports r24_fixmc: equalizer patch)
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402

R3, R22 = T.R3, T.R22
OUT = R3.HERE / "out" / "r26"
HOT, DNL_CONDS = T.HOT, T.DNL_CONDS


def register(bits: int, k: float) -> str:
    n = f"s{bits}_k{round(k * 100):03d}"
    DESIGNS[n] = Design(n, input_device="nfet_01v8_lvt", input_w=round(3 * k, 4), tail_w=round(7 * k, 4),
                        trim_l=1.0, trim_bits=bits)
    return n


def _range(job):
    bits, k, cond = job
    design = register(bits, k)
    mx = DESIGNS[design].max_code
    b = T._nominal(design, cond).boundaries([-mx, 0, mx], lo=-R22.LIMIT_MV, hi=R22.LIMIT_MV)
    return {"design": design, "bits": bits, "k": k, "cond": list(cond), "b_neg_mv": b[-mx], "b0_mv": b[0],
            "b_pos_mv": b[mx], "half_range_mv": min(abs(b[-mx] - b[0]), abs(b[mx] - b[0])),
            "lsb_mv": (b[mx] - b[-mx]) / (2 * mx)}


def screen(bits, ks, workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, [(bits, k, c) for k in ks for c in (("tt", 1.8, 27.0),) + HOT]))
    with (OUT / "screen.jsonl").open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
            print(f"{r['design']} {r['cond']} half {r['half_range_mv']:.1f} lsb {r['lsb_mv']:+.3f}", flush=True)


def _transfer(job):
    bits, k, cond = job
    design = register(bits, k)
    mx = DESIGNS[design].max_code
    codes = list(range(-mx, mx + 1))
    b = T._nominal(design, cond).boundaries(codes, lo=-R22.LIMIT_MV, hi=R22.LIMIT_MV)
    v = np.array([b[c] for c in codes])
    steps = np.diff(v)
    lsb = (v[-1] - v[0]) / (2 * mx)
    return {"design": design, "cond": list(cond), "b_mv": {str(c): b[c] for c in codes}, "lsb_mv": lsb,
            "median_step_mv": float(np.median(np.abs(steps))), "max_abs_step_mv": float(np.max(np.abs(steps))),
            "dnl_max_lsb": float(np.max(np.abs(steps / lsb - 1))),
            "monotonic": bool(np.all(np.sign(steps) == np.sign(lsb)))}


def dnl(bits, k, workers=5):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_transfer, [(bits, k, c) for c in DNL_CONDS]))
    (OUT / f"dnl_{register(bits, k)}.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(r["cond"], f"lsb {r['lsb_mv']:+.3f} median step {r['median_step_mv']:.2f} "
              f"max step {r['max_abs_step_mv']:.2f} dnl {r['dnl_max_lsb']:.2f} monotonic {r['monotonic']}", flush=True)


def run_range(bits, k, workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, [(bits, k, c) for c in R22.conditions()]))
    (OUT / f"range_{register(bits, k)}.json").write_text(json.dumps(rows, indent=1))
    hr = sorted(r["half_range_mv"] for r in rows)
    print("half range min/median/max", hr[0], hr[len(hr) // 2], hr[-1], flush=True)


def _seed(job):
    bits, k, seed, cond = job
    design = register(bits, k)
    s = T.Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), R3.sigma(design), cond)
    res = s.run()
    res["fix"] = "equalize"
    return res


def mc(bits, k, cond=HOT[0], seeds=range(40), workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    design = register(bits, k)
    R3.sigma(design)  # calibrate once, before the workers read the cache
    path = OUT / f"mc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}.jsonl"
    done = {json.loads(ln)["seed"] for ln in path.read_text().splitlines()} if path.exists() else set()
    with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
        for res in ex.map(_seed, [(bits, k, s, cond) for s in seeds if s not in done]):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


if __name__ == "__main__":
    cmd = ARGS[0] if ARGS else ""
    if cmd == "screen":
        screen(int(ARGS[1]), [float(x) for x in ARGS[2:]])
    elif cmd == "dnl":
        dnl(int(ARGS[1]), float(ARGS[2]))
    elif cmd == "range":
        run_range(int(ARGS[1]), float(ARGS[2]))
    elif cmd == "mc":
        mc(int(ARGS[1]), float(ARGS[2]), (ARGS[3], float(ARGS[4]), float(ARGS[5])) if len(ARGS) > 5 else HOT[0])
    else:
        raise SystemExit(__doc__)
