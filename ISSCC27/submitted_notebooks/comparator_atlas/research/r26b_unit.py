"""r26b: unit-cell trim. r26 left +-1 mV limited by carry DNL; the single-bit weights of the width-scaled binary
trim (bit k: one W 0.42*2^k device + one W 2^k switch) are far from binary and change with PVT (cold: small
bits weak, w1/w0 ~ 3; hot: small bits ~ equal). Hypothesis: the narrow LSB devices sit in another model bin and
their perimeter junction terms do not scale with W. Unit-cell trim: bit k = 2^k identical unit devices
(W 0.42 trim, W 1 switch) via the instance multiplier m = 2^k (same total W and gate area). Mismatch per bit:
the unit sigma / sqrt(m) (Pelgrom, same area).

  python -B r26b_unit.py mcheck                    # m=2^k vs explicit parallel copies (TT, nominal)
  python -B r26b_unit.py weights <bits> <k> [k ...]  # single-bit weights, width vs unit cell, 5 conditions
  python -B r26b_unit.py screen|dnl|range <bits> <k>   # as r26_scale, unit-cell designs u<bits>_k<100k>
  python -B r26b_unit.py mc <bits> <k> [corner vdd temp [n_seeds]]   # seeds 0..n_seeds-1 (default 40), resumable
"""
import json
import math
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r26_scale as S  # noqa: E402
import comparator_atlas.designs as D  # noqa: E402
import comparator_atlas.spice as SP  # noqa: E402

T, R3, R22 = S.T, S.R3, S.R22
OUT = R3.HERE / "out" / "r26b"
HOT, DNL_CONDS = S.HOT, S.DNL_CONDS
UNIT_W, SWITCH_W = 0.42, 1.0
_orig = D.circuit_text
_BLOCK = re.compile(r"^(X[ts])([pn])(\d+) (.+)\n\+ w=\{([^}]*)\} l=(\S+)\n\+ ad=.*\n\+ pd=.*$", re.M)


def _unit(match, copies=False):
    kind, side, bit, rest, _, length = match.groups()
    m = 1 << int(bit)
    w = UNIT_W if kind == "Xt" else SWITCH_W
    geo = (f"+ w={{{w:.12g}}} l={length}\n+ ad={{0.29*({w:.12g})}} as={{0.29*({w:.12g})}}\n"
           f"+ pd={{2*(0.29+({w:.12g}))}} ps={{2*(0.29+({w:.12g}))}}")
    if copies:
        return "\n".join(f"{kind}{side}{bit}_{j} {rest}\n{geo}" for j in range(m))
    return f"{kind}{side}{bit} {rest}\n{geo}\n+ m={m}"


def circuit_text(design):
    text = _orig(design)
    if design.name.startswith(("u", "c")) and design.name[1:2].isdigit():
        text = _BLOCK.sub(lambda mt: _unit(mt, copies=design.name.startswith("c")), text)
    return text


D.circuit_text = SP.circuit_text = R3.circuit_text = circuit_text


def register(bits, k, prefix="u"):
    n = f"{prefix}{bits}_k{round(k * 100):03d}"
    D.DESIGNS[n] = D.Design(n, input_device="nfet_01v8_lvt", input_w=round(3 * k, 4), tail_w=round(7 * k, 4),
                            trim_l=1.0, trim_bits=bits)
    return n


def mult(name):
    m = re.fullmatch(r"X[ts][pn](\d+)", name)
    return 1 << int(m.group(1)) if m else 1


class Paired(T.Paired):
    """r25 pairing (core keeps the r22 draw); unit-cell bits scale their draw by 1/sqrt(m)."""

    def __init__(self, design, seed, sim, sig, cond):
        super().__init__(design, seed, sim, sig, cond)
        self.z = {n: z / math.sqrt(mult(n)) for n, z in self.z.items()}
        self.circuit = R3.mutated_circuit(design, self.z, sig)
        assert "+ m=16" in self.circuit or D.DESIGNS[design].trim_bits < 5


def _bounds(job):
    design, cond, codes = job
    return T._nominal(design, cond).boundaries(codes, lo=-R22.LIMIT_MV, hi=R22.LIMIT_MV)


def mcheck(workers=3):
    names = [register(5, 1.25, p) for p in ("u", "c")] + [S.register(5, 1.25)]
    codes = [0, 1, 16, 31]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_bounds_any, [(n, ("tt", 1.8, 27.0), codes) for n in names]))
    for n, b in zip(names, rows):
        print(n, {c: round(v, 3) for c, v in b.items()}, flush=True)


def _register_all(name):
    p, rest = name[0], name[1:]
    bits, k = rest.split("_k")
    return register(int(bits), int(k) / 100, p) if p in "uc" else S.register(int(bits), int(k) / 100)


def _bounds_any(job):
    name, cond, codes = job
    _register_all(name)
    return _bounds((name, cond, codes))


def weights(bits, ks, workers=10):
    OUT.mkdir(parents=True, exist_ok=True)
    mx = (1 << bits) - 1
    codes = sorted({0, mx, -mx} | {s * (1 << b) for b in range(bits) for s in (1, -1)})
    jobs = [(f"{p}{bits}_k{round(k * 100):03d}", c, codes) for k in ks for p in ("s", "u") for c in DNL_CONDS]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_bounds_any, jobs))
    rows = []
    for (n, c, _), b in zip(jobs, res):
        w = [b[1 << i] - b[0] for i in range(bits)]
        rows.append({"design": n, "cond": list(c), "b_mv": {str(k): v for k, v in b.items()},
                     "w_pos_mv": w, "w_neg_mv": [b[-(1 << i)] - b[0] for i in range(bits)]})
        print(n, c[0], "w/w0", [round(x / w[0], 2) for x in w], "full", round(b[mx] - b[0], 1),
              "sum", round(sum(w), 1), flush=True)
    with (OUT / "weights.jsonl").open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _transfer(job):
    bits, k, cond = job
    design = register(bits, k)
    mx = D.DESIGNS[design].max_code
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


def _range(job):
    bits, k, cond = job
    design = register(bits, k)
    mx = D.DESIGNS[design].max_code
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


def run_range(bits, k, workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, [(bits, k, c) for c in R22.conditions()]))
    (OUT / f"range_{register(bits, k)}.json").write_text(json.dumps(rows, indent=1))
    hr = sorted(r["half_range_mv"] for r in rows)
    print("half range min/median/max", hr[0], hr[len(hr) // 2], hr[-1], flush=True)


def _sig(design):
    # unit-cell geometry sigma: r3.sigma keys by device|w|l, all bits share the unit key
    return R3.sigma(design)


def _seed(job):
    bits, k, seed, cond = job
    design = register(bits, k)
    s = Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), _sig(design), cond)
    res = s.run()
    res["fix"] = "equalize"
    return res


def mc(bits, k, cond=HOT[0], seeds=range(40), workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    design = register(bits, k)
    _sig(design)
    path = OUT / f"mc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}.jsonl"
    done = {json.loads(ln)["seed"] for ln in path.read_text().splitlines()} if path.exists() else set()
    with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
        for res in ex.map(_seed, [(bits, k, s, cond) for s in seeds if s not in done]):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


if __name__ == "__main__":
    os.environ.pop("R24_PRIOR_MV", None)
    cmd = ARGS[0] if ARGS else ""
    if cmd == "mcheck":
        mcheck()
    elif cmd == "weights":
        weights(int(ARGS[1]), [float(x) for x in ARGS[2:]])
    elif cmd == "screen":
        screen(int(ARGS[1]), [float(x) for x in ARGS[2:]])
    elif cmd == "dnl":
        dnl(int(ARGS[1]), float(ARGS[2]))
    elif cmd == "range":
        run_range(int(ARGS[1]), float(ARGS[2]))
    elif cmd == "mc":
        mc(int(ARGS[1]), float(ARGS[2]), (ARGS[3], float(ARGS[4]), float(ARGS[5])) if len(ARGS) > 5 else HOT[0],
           range(int(ARGS[6]) if len(ARGS) > 6 else 40))
    else:
        raise SystemExit(__doc__)
