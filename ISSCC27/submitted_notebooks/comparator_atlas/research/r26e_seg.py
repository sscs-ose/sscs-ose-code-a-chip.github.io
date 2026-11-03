"""r26e: segmented unit-cell trim. r26d found that the local trim step spreads as sqrt(sigma0^2 + n sigma_u^2) with n
the unit cells that switch (binary: n = 2^j - 1, 15 at 7 -> 8, 31 at 15 -> 16) and predicted that coding the three
magnitude MSBs as a thermometer (7 cells of 4 units, n <= 7) cuts the e5_k175 static misses from 0.73 to 0.07 per
1000 seeds. Design family g5_k<100k>: the e-design (unit trim cells, unit-cell equalizer, clkb inverter m 4) with
bits 2-4 of each side replaced by seven 4-unit segments s<side>2..s<side>8, each with its own switch, node and 4-unit
equalizer; segment i is on when the 3-bit MSB value exceeds i - 2. Same unit-cell count (31 per side), same
equalizer count, same code. The decoder is an ideal behavioural source (no devices, no energy, no mismatch) driven
by the unchanged binary trim ports; it is static within a decision.

Pairing: the core and the r22-named devices keep their draws (as r25/r26b), so b0 is the e5 seed's b0; each trim
device's draw is scaled by 1/sqrt(unit cells) as in r26b.

  python -B r26e_seg.py check <k>                                # TT nominal: g vs e at a few codes
  python -B r26e_seg.py dnl <k>                                  # 63-code transfer at the 5 DNL conditions
  python -B r26e_seg.py mc <k> <corner> <vdd> <temp> [n_seeds]   # appends out/r26b/mc_<cond>_g5_k<100k>.jsonl
  python -B r26e_seg.py refine <k> <corner> <vdd> <temp> [n]     # as r26c_refine.py
"""
import json
import math
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r26c_eqscale as E  # noqa: E402

U, R3, T, D, SP, S = E.U, E.R3, E.T, E.D, E.SP, E.S
OUT = U.OUT
MSB_FROM, SEG_UNITS, SEGMENTS = 2, 4, 7
_BITBLOCK = re.compile(r"^X[ts][pn][234] .+\n\+ w=.*\n\+ ad=.*\n\+ pd=.*\n\+ m=\d+\n", re.M)
_EQ = re.compile(r"^(Xeq_(\d+) .+\n\+ w=.*\n\+ ad=.*\n\+ pd=.*)$", re.M)
_INV = re.compile(r"^(Xeqi_[pn] .+\n\+ w=.*\n\+ ad=.*\n\+ pd=.*)$", re.M)
_ct, _mut = E.circuit_text, E.mutated_circuit


def _is_g(name):
    return name.startswith("g") and name[1:2].isdigit()


def units(name):
    """Unit cells of a trim device (Xt/Xs) or equalizer index; 1 for anything else."""
    m = re.fullmatch(r"(?:X[ts][pn]|Xeq_)(\d+)", name)
    if not m:
        return 1
    i = int(m.group(1))
    return 1 << i if i < MSB_FROM else SEG_UNITS


def _geo(w, length):
    return (f"+ w={{{w:.12g}}} l={length}\n+ ad={{0.29*({w:.12g})}} as={{0.29*({w:.12g})}}\n"
            f"+ pd={{2*(0.29+({w:.12g}))}} ps={{2*(0.29+({w:.12g}))}}\n+ m={SEG_UNITS}")


def _segments(length):
    out = []
    for side in "pn":
        msb = f"(v(t{side}2)+2*v(t{side}3)+4*v(t{side}4))"
        for i in range(MSB_FROM, MSB_FROM + SEGMENTS):
            out.append(f"Xt{side}{i} x{side} vin{side} s{side}{i} vss sky130_fd_pr__nfet_01v8_lvt\n"
                       f"{_geo(U.UNIT_W, length)}")
            out.append(f"Xs{side}{i} s{side}{i} g{side}{i} tail vss sky130_fd_pr__nfet_01v8\n{_geo(U.SWITCH_W, 0.15)}")
            out.append(f"Bdec{side}{i} g{side}{i} vss V={msb} > {i - MSB_FROM + 0.5}*v(vdd) ? v(vdd) : 0")
    return "\n".join(out)


def circuit_text(design):
    if not _is_g(design.name):
        return _ct(design)
    text = U._BLOCK.sub(lambda mt: U._unit(mt), U._orig(design))
    length = re.search(r"^Xtp0 .+\n\+ w=\S+ l=(\S+)", text, re.M).group(1)
    text, n = _BITBLOCK.subn("", text)
    assert n == 12, n
    return text.replace(".ends atlas", _segments(length) + "\n.ends atlas")


def mutated_circuit(design, z, sig):
    text = _mut(design, z, sig)
    if not _is_g(design if isinstance(design, str) else design.name):
        return text
    text = _EQ.sub(lambda mt: f"{mt.group(1)}\n+ m={units('Xeq_' + mt.group(2))}", text)
    return _INV.sub(lambda mt: f"{mt.group(1)}\n+ m={E.INV_M}", text)


D.circuit_text = SP.circuit_text = R3.circuit_text = circuit_text
R3.mutated_circuit = mutated_circuit


def register(k):
    return U.register(5, k, prefix="g")


def _check_circuit(text):
    assert text.count("Bdec") == 2 * SEGMENTS and re.search(r"^Xtp8 xp \S+ sp8 vss", text, re.M)
    assert re.search(r"Xeq_8 [^\n]*\n(\+[^\n]*\n){3}\+ m=4", text)
    assert re.search(r"Xeq_1 [^\n]*\n(\+[^\n]*\n){3}\+ m=2", text)
    assert "+ m=16" not in text and "+ m=8" not in text


class Paired(T.Paired):
    def __init__(self, design, seed, sim, sig, cond):
        super().__init__(design, seed, sim, sig, cond)
        self.z = {n: z / math.sqrt(units(n)) for n, z in self.z.items()}
        self.circuit = R3.mutated_circuit(design, self.z, sig)
        _check_circuit(self.circuit)


def _nominal(design, cond):
    s = T._nominal(design, cond)
    _check_circuit(s.circuit)
    return s


def _bounds(job):
    name, k, cond, codes = job
    design = register(k) if name == "g" else E.register(5, k)
    s = _nominal(design, cond) if name == "g" else T._nominal(design, cond)
    return s.boundaries(codes, lo=-S.R22.LIMIT_MV, hi=S.R22.LIMIT_MV)


def check(k):
    design = register(k)
    text = R3.mutated_circuit(design, {d["name"]: 0.0 for d in R3.devices(design)},
                              {f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}": 0.0 for d in R3.devices(design)})
    _check_circuit(text)
    print(f"{design}: {len(R3.devices(design))} devices, trim units per side "
          f"{sum(units(d['name']) for d in R3.devices(design) if d['name'].startswith('Xtp'))}", flush=True)
    codes = [0, 3, 4, 7, 8, 15, 16, 31, -31]
    with ProcessPoolExecutor(2) as ex:
        g, e = ex.map(_bounds, [("g", k, ("tt", 1.8, 27.0), codes), ("e", k, ("tt", 1.8, 27.0), codes)])
    for c in codes:
        print(f"code {c:+d}: g {g[c]:+.3f}  e {e[c]:+.3f}  diff {g[c] - e[c]:+.3f}", flush=True)


def _transfer(job):
    k, cond = job
    design = register(k)
    codes = list(range(-31, 32))
    b = _nominal(design, cond).boundaries(codes, lo=-S.R22.LIMIT_MV, hi=S.R22.LIMIT_MV)
    v = np.array([b[c] for c in codes])
    steps = np.diff(v)
    lsb = (v[-1] - v[0]) / 62
    return {"design": design, "inv_m": E.INV_M, "cond": list(cond), "b_mv": {str(c): b[c] for c in codes},
            "lsb_mv": lsb, "median_step_mv": float(np.median(np.abs(steps))),
            "max_abs_step_mv": float(np.max(np.abs(steps))), "dnl_max_lsb": float(np.max(np.abs(steps / lsb - 1))),
            "monotonic": bool(np.all(np.sign(steps) == np.sign(lsb)))}


def dnl(k, workers=5):
    design = register(k)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_transfer, [(k, c) for c in S.DNL_CONDS]))
    (OUT / f"dnl_{design}.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        print(f"{r['cond']} lsb {r['lsb_mv']:+.3f} max step {r['max_abs_step_mv']:.2f} dnl {r['dnl_max_lsb']:.2f} "
              f"mono {r['monotonic']}", flush=True)


def _seed(job):
    k, seed, cond = job
    design = register(k)
    s = Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), U._sig(design), cond)
    res = s.run()
    res["fix"] = "equalize_unit_segmented"
    res["inv_m"] = E.INV_M
    return res


def mc(k, cond, seeds=range(200), workers=12):
    design = register(k)
    U._sig(design)
    path = OUT / f"mc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}.jsonl"
    done = {json.loads(ln)["seed"] for ln in path.read_text().splitlines()} if path.exists() else set()
    with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
        for res in ex.map(_seed, [(k, s, cond) for s in seeds if s not in done]):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


def _refine(job):
    import r26c_refine as RF
    k, seed, cond, cands = job
    R3.TOL_MV = RF.FINE_TOL_MV
    design = register(k)
    s = Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), U._sig(design), cond)
    fine = {c: s.boundaries([c], lo=v - RF.WINDOW_MV, hi=v + RF.WINDOW_MV)[c] for c, v in cands.items()}
    best = min(fine, key=lambda c: abs(fine[c]))
    edge = min(RF.WINDOW_MV - abs(fine[c] - cands[c]) for c in fine)
    return {"design": design, "seed": seed, "cond": list(cond), "coarse": {str(c): v for c, v in cands.items()},
            "fine": {str(c): v for c, v in fine.items()}, "code": best, "m_mv": fine[best], "window_edge_mv": edge,
            "tol_mv": RF.FINE_TOL_MV}


def refine(k, cond, n=200, workers=6):
    import r26c_refine as RF
    design = register(k)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}"
    rows = [r for r in map(json.loads, (OUT / f"mc_{tag}.jsonl").read_text().splitlines()) if r["seed"] < n]
    pick = [r for r in rows if abs(abs(r["m_mv"]) - 1.0) <= RF.BAND_MV]
    out = OUT / f"refine_{tag}.jsonl"
    done = {json.loads(ln)["seed"] for ln in out.read_text().splitlines()} if out.exists() else set()
    jobs = [(k, r["seed"], cond, {int(c): v for c, v in r["candidates"].items()})
            for r in pick if r["seed"] not in done]
    print(f"{design} {cond}: {len(pick)} borderline of {len(rows)}, {len(jobs)} to run", flush=True)
    with ProcessPoolExecutor(workers) as ex, out.open("a") as f:
        for res in ex.map(_refine, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} code={res['code']} m={res['m_mv']:+.3f}", flush=True)


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = ARGS[0] if ARGS else ""
    if cmd == "check":
        check(float(ARGS[1]))
    elif cmd == "dnl":
        dnl(float(ARGS[1]))
    elif cmd == "mc":
        mc(float(ARGS[1]), (ARGS[2], float(ARGS[3]), float(ARGS[4])), range(int(ARGS[5]) if len(ARGS) > 5 else 200))
    elif cmd == "refine":
        refine(float(ARGS[1]), (ARGS[2], float(ARGS[3]), float(ARGS[4])), *[int(a) for a in ARGS[5:6]])
    else:
        raise SystemExit(__doc__)
