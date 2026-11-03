"""r26c: unit-cell equalizer. r26b made the trim devices unit cells (bit k = 2^k cells via m=2^k) but kept the
r24c equalizer as one minimum NMOS per bit (Xeq_k shorts sp<k>/sn<k> in reset). Bit k's floating node carries
2^k cells of capacitance while its equalizer resistance is fixed, so large bits settle less in reset and
the weights stay non-binary over PVT (0.01 mV nominal transfer: SS carry steps 1.8-2.0 mV vs 1.1 mV for the
bit-0 step; SF 3->4 step +0.33 mV, non-monotonic). Design family e<bits>_k<100k>: u-design plus Xeq_k with
m=2^k (each cell gets its own minimum equalizer) and the clkb inverter with m=INV_M.

  python -B r26c_eqscale.py fine [inv_m]             # codes 0..11 at 0.01 mV, SS/TT/SF (vs r26c_fine.py)
  python -B r26c_eqscale.py dnl <bits> <k> [inv_m]   # 63-code transfer at the 5 DNL conditions
  python -B r26c_eqscale.py range <bits> <k> [inv_m] # nominal half range at the 45 PVT conditions
  python -B r26c_eqscale.py mc <bits> <k> <corner> <vdd> <temp> [n_seeds] [inv_m]
"""
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r26b_unit as U  # noqa: E402

R3, T, D, SP, S = U.R3, U.T, U.D, U.SP, U.S
OUT = U.OUT
INV_M = 4
_EQ = re.compile(r"^(Xeq_(\d+) .+\n\+ w=.*\n\+ ad=.*\n\+ pd=.*)$", re.M)
_INV = re.compile(r"^(Xeqi_[pn] .+\n\+ w=.*\n\+ ad=.*\n\+ pd=.*)$", re.M)
_ct, _mut = U.circuit_text, R3.mutated_circuit


def _is_e(name):
    return name.startswith("e") and name[1:2].isdigit()


def circuit_text(design):
    if not _is_e(design.name):
        return _ct(design)
    return U._BLOCK.sub(lambda mt: U._unit(mt), U._orig(design))


def mutated_circuit(design, z, sig):
    text = _mut(design, z, sig)
    if not _is_e(design if isinstance(design, str) else design.name):
        return text
    text = _EQ.sub(lambda mt: f"{mt.group(1)}\n+ m={1 << int(mt.group(2))}", text)
    return _INV.sub(lambda mt: f"{mt.group(1)}\n+ m={INV_M}", text)


D.circuit_text = SP.circuit_text = R3.circuit_text = circuit_text
R3.mutated_circuit = mutated_circuit


def register(bits, k, inv_m=None):
    global INV_M
    if inv_m is not None:
        INV_M = inv_m
    n = U.register(bits, k, prefix="e")
    return n


def tag():
    return "" if INV_M == 4 else f"_i{INV_M}"


def _fine(args):
    cond, codes, inv_m = args
    R3.TOL_MV = 0.01
    design = register(5, 1.5, inv_m)
    s = T._nominal(design, cond)
    assert "+ m=16" in s.circuit and re.search(r"Xeq_4 [^\n]*\n(\+[^\n]*\n){3}\+ m=16", s.circuit), design
    coarse = s.boundaries(codes[:1], lo=-20.0, hi=20.0)[codes[0]]
    out = {}
    for c in codes:
        out[c] = s.boundaries([c], lo=coarse - 4.0, hi=coarse + 4.0)[c]
        coarse = out[c] - 1.4
    return cond[0], out


def fine(inv_m=4):
    register(5, 1.5, inv_m)
    conds = (("ss", 1.62, -40.0), ("tt", 1.8, 27.0), ("sf", 1.95, 125.0))
    jobs = [(c, list(range(i, i + 4)), inv_m) for c in conds for i in (0, 4, 8)]
    res = {}
    with ProcessPoolExecutor(9) as ex:
        for k, o in ex.map(_fine, jobs):
            res.setdefault(k, {}).update(o)
    (OUT / f"fine_transfer_e5_k150{tag()}.json").write_text(
        json.dumps({k: {str(c): v for c, v in sorted(o.items())} for k, o in res.items()}, indent=1))
    for k, o in res.items():
        print(k, "step", " ".join(f"{o[c + 1] - o[c]:+.3f}" for c in sorted(o)[:-1]), flush=True)


def _transfer(job):
    bits, k, cond, inv_m = job
    design = register(bits, k, inv_m)
    mx = D.DESIGNS[design].max_code
    s = T._nominal(design, cond)
    b = s.boundaries(list(range(-mx, mx + 1)), lo=-S.R22.LIMIT_MV, hi=S.R22.LIMIT_MV)
    v = np.array([b[c] for c in range(-mx, mx + 1)])
    steps = np.diff(v)
    lsb = (v[-1] - v[0]) / (2 * mx)
    return {"design": design, "inv_m": inv_m, "cond": list(cond), "b_mv": {str(c): b[c] for c in b}, "lsb_mv": lsb,
            "median_step_mv": float(np.median(np.abs(steps))), "max_abs_step_mv": float(np.max(np.abs(steps))),
            "dnl_max_lsb": float(np.max(np.abs(steps / lsb - 1))), "monotonic": bool(np.all(np.sign(steps) == np.sign(lsb)))}


def dnl(bits, k, inv_m=4, workers=5):
    design = register(bits, k, inv_m)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_transfer, [(bits, k, c, inv_m) for c in S.DNL_CONDS]))
    (OUT / f"dnl_{design}{tag()}.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['cond']} lsb {r['lsb_mv']:+.3f} max step {r['max_abs_step_mv']:.2f} dnl {r['dnl_max_lsb']:.2f} "
              f"mono {r['monotonic']}", flush=True)


def _range(job):
    bits, k, cond, inv_m = job
    design = register(bits, k, inv_m)
    mx = D.DESIGNS[design].max_code
    b = T._nominal(design, cond).boundaries([-mx, 0, mx], lo=-S.R22.LIMIT_MV, hi=S.R22.LIMIT_MV)
    return {"design": design, "cond": list(cond), "b_neg_mv": b[-mx], "b0_mv": b[0], "b_pos_mv": b[mx],
            "half_range_mv": min(abs(b[-mx] - b[0]), abs(b[mx] - b[0]))}


def run_range(bits, k, inv_m=4, workers=12):
    design = register(bits, k, inv_m)
    conds = [(c, v, t) for c in ("tt", "ss", "ff", "sf", "fs") for v in (1.62, 1.8, 1.95) for t in (-40.0, 27.0, 125.0)]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, [(bits, k, c, inv_m) for c in conds]))
    (OUT / f"range_{design}{tag()}.json").write_text(json.dumps(rows, indent=1))
    h = sorted(r["half_range_mv"] for r in rows)
    print(f"{design} half range min {h[0]:.1f} p10 {h[4]:.1f} median {h[22]:.1f}", flush=True)


def _seed(job):
    bits, k, seed, cond, inv_m = job
    design = register(bits, k, inv_m)
    s = U.Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), U._sig(design), cond)
    assert re.search(r"Xeq_4 [^\n]*\n(\+[^\n]*\n){3}\+ m=16", s.circuit)
    res = s.run()
    res["fix"] = "equalize_unit"
    res["inv_m"] = inv_m
    return res


def mc(bits, k, cond, seeds=range(200), inv_m=4, workers=12):
    design = register(bits, k, inv_m)
    U._sig(design)
    path = OUT / f"mc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}{tag()}.jsonl"
    done = {json.loads(ln)["seed"] for ln in path.read_text().splitlines()} if path.exists() else set()
    with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
        for res in ex.map(_seed, [(bits, k, s, cond, inv_m) for s in seeds if s not in done]):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = ARGS[0] if ARGS else ""
    if cmd == "fine":
        fine(*[int(a) for a in ARGS[1:2]])
    elif cmd == "dnl":
        dnl(int(ARGS[1]), float(ARGS[2]), *[int(a) for a in ARGS[3:4]])
    elif cmd == "range":
        run_range(int(ARGS[1]), float(ARGS[2]), *[int(a) for a in ARGS[3:4]])
    elif cmd == "mc":
        mc(int(ARGS[1]), float(ARGS[2]), (ARGS[3], float(ARGS[4]), float(ARGS[5])),
           range(int(ARGS[6]) if len(ARGS) > 6 else 200), *[int(a) for a in ARGS[7:8]])
    else:
        raise SystemExit(__doc__)
