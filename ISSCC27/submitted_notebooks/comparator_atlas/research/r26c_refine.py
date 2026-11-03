"""r26c: refine the borderline MC seeds. r3 bisects the switching input to TOL 0.2 mV (bracket <= 0.4 mV), so the
reported residual m carries +-0.12 mV; seeds with 1 - BAND <= |m| <= 1 + BAND are re-bisected for every candidate
code to 0.01 mV inside +-WINDOW of the coarse value, and the best code is re-chosen.

  python -B r26c_refine.py <bits> <k> <corner> <vdd> <temp> [n_seeds] [prefix]   # appends out/r26b/refine_<cond>_<design>.jsonl
  prefix "u" (default, r26b unit cells) or "e" (r26c unit cells + unit-cell equalizer, r26c_eqscale.py)
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r26b_unit as U  # noqa: E402

R3 = U.R3
FINE_TOL_MV, WINDOW_MV, BAND_MV = 0.01, 0.4, 0.15


def _register(bits, k, prefix):
    if prefix == "e":
        import r26c_eqscale as E
        return E.register(bits, k)
    return U.register(bits, k)


def _refine(job):
    bits, k, seed, cond, cands, prefix = job
    R3.TOL_MV = FINE_TOL_MV
    design = _register(bits, k, prefix)
    s = U.Paired(design, seed, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), U._sig(design), cond)
    assert prefix != "e" or "+ m=16" in s.circuit, design
    fine = {}
    for code, coarse in cands.items():
        fine[code] = s.boundaries([code], lo=coarse - WINDOW_MV, hi=coarse + WINDOW_MV)[code]
    best = min(fine, key=lambda c: abs(fine[c]))
    edge = min(WINDOW_MV - abs(fine[c] - cands[c]) for c in fine)  # ~0 would mean the window clipped the boundary
    return {"design": design, "seed": seed, "cond": list(cond), "coarse": {str(c): v for c, v in cands.items()},
            "fine": {str(c): v for c, v in fine.items()}, "code": best, "m_mv": fine[best], "window_edge_mv": edge,
            "tol_mv": FINE_TOL_MV}


def main(bits, k, cond, n=200, prefix="u", workers=6):
    design = _register(bits, k, prefix)
    src = U.OUT / f"mc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}.jsonl"
    rows = [r for r in map(json.loads, src.read_text().splitlines()) if r["seed"] < n]
    pick = [r for r in rows if abs(abs(r["m_mv"]) - 1.0) <= BAND_MV]
    out = U.OUT / f"refine_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{design}.jsonl"
    done = {json.loads(ln)["seed"] for ln in out.read_text().splitlines()} if out.exists() else set()
    jobs = [(bits, k, r["seed"], cond, {int(c): v for c, v in r["candidates"].items()}, prefix) for r in pick
            if r["seed"] not in done]
    print(f"{design} {cond}: {len(pick)} borderline of {len(rows)}, {len(jobs)} to run", flush=True)
    with ProcessPoolExecutor(workers) as ex, out.open("a") as f:
        for res in ex.map(_refine, jobs):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} code={res['code']} m={res['m_mv']:+.3f} coarse={res['coarse']}", flush=True)


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    main(int(ARGS[0]), float(ARGS[1]), (ARGS[2], float(ARGS[3]), float(ARGS[4])), *[int(a) for a in ARGS[5:6]], *ARGS[6:7])
