"""r24c: the r22 mismatch Monte Carlo (same r3 Sample logic, seeds 0-39, same per-device sigma) rerun with
the equalize memory fix (r24_probe.equalize: one minimum NMOS per trim bit shorting sp<k> to sn<k> in reset,
gate from one minimum inverter). The added devices are nominal (no mismatch); every original device keeps
its r22 draw, so each seed is paired with its r22 result.

  python -B r24_fixmc.py run [corner vdd temp]   # default sf 1.95 125; writes out/r24/fixmc_<tag>.jsonl
  python -B r24_fixmc.py range                    # nominal half-range at the 45 conditions, r3 bench
"""
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r22_range_mc as R22  # noqa: E402
import r24_probe as P  # noqa: E402

R3 = R22.R3
DESIGN = "lvt_balanced_4b"
OUT = R3.HERE / "out" / "r24"
_mutated = R3.mutated_circuit


def _nodes(design):
    return sorted(set(re.findall(r"^Xt[pn]\S* x[pn] vin[pn] (s[pn]\d+) vss",
                                 R3.circuit_text(R3.get_design(design)), re.M)))


def fixed_circuit(design, z, sig):
    text = _mutated(design, z, sig)
    nodes = _nodes(design)
    assert nodes, design
    eq = [P._mos("Xeqi_p", "clkb", "clk", "vdd", "vdd", "pfet"), P._mos("Xeqi_n", "clkb", "clk", "vss", "vss", "nfet")]
    eq += [P._mos(f"Xeq_{n[2:]}", n, "clkb", "sn" + n[2:], "vss", "nfet") for n in nodes if n.startswith("sp")]
    return text.replace(".ends atlas", "\n".join(eq) + "\n.ends atlas")


R3.mutated_circuit = fixed_circuit


def _seed(job):
    seed, cond = job
    sig = json.loads((R3.HERE / "out" / "r22" / f"sigma_{DESIGN}.json").read_text())
    sim = R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1)
    s = R3.Sample(DESIGN, seed, sim, sig, cond)
    assert "Xeq_0" in s.circuit
    return s.run()


def run(cond=("sf", 1.95, 125.0), seeds=range(40), workers=12):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"fixmc_{cond[0]}{cond[1]:g}V{cond[2]:g}C_{DESIGN}.jsonl"
    done = {json.loads(ln)["seed"] for ln in path.read_text().splitlines()} if path.exists() else set()
    jobs = [(s, cond) for s in seeds if s not in done]
    with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
        for res in ex.map(_seed, jobs):
            res["fix"] = "equalize"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"seed={res['seed']} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


def _range(cond):
    sig = {f"{d['device']}|{d['w']:.6g}|{d['l']:.6g}": 0.0 for d in R3.devices(DESIGN)}
    s = R3.Sample(DESIGN, 0, R3.Simulator(R3.HERE / "cache" / "r3_unused", workers=1), sig, cond)
    mx = R3.get_design(DESIGN).max_code
    b = s.boundaries([-mx, 0, mx], lo=-R22.LIMIT_MV, hi=R22.LIMIT_MV)
    return {"cond": list(cond), "b_neg_mv": b[-mx], "b0_mv": b[0], "b_pos_mv": b[mx],
            "half_range_mv": min(abs(b[-mx] - b[0]), abs(b[mx] - b[0]))}


def run_range(workers=12):
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_range, R22.conditions()))
    (OUT / f"fixrange_{DESIGN}.json").write_text(json.dumps(rows, indent=1))
    hr = sorted(r["half_range_mv"] for r in rows)
    print("half range min/median/max", hr[0], hr[len(hr) // 2], hr[-1], flush=True)


if __name__ == "__main__":
    if ARGS and ARGS[0] == "range":
        run_range()
    elif ARGS and ARGS[0] == "run":
        run((ARGS[1], float(ARGS[2]), float(ARGS[3])) if len(ARGS) > 3 else ("sf", 1.95, 125.0))
    else:
        raise SystemExit(__doc__)
