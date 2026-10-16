"""r12: gate-switched trim -- r10 (input x2 + unit trim x1 + 5b) with the series switch removed.

Trim device: drain=x, source=tail, gate=g; g = vin (code bit on) via pass nfet, or vss via pull-down.
Off units have no channel, so they stop loading x every cycle (energy) and stop contributing
offset at code 0. Same seeds/z as r10 for every shared device; added digital devices get z=0.
Local only.
  python -B r12_gate_trim.py sigma
  python -B r12_gate_trim.py run <start> <n> [corner vdd temp]
  python -B r12_gate_trim.py energy
  python -B r12_gate_trim.py report
"""
import json
import re
import sys

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3
import r10_combo5b as R10
from r3_mismatch_mc import HERE, Point, Simulator
from r8_unit_trim_mc import mutate, parse
from r9_combo_mc import combo_sigma

R12 = HERE / "out" / "r12"
NAME, BITS = R10.NAME, 5


def gate_switched(text: str, bits: int) -> str:
    text, n1 = re.subn(r"^(Xt([pn])(\d)(u\d+)?) x\2 (\S+) s\2\3 vss", r"\1 x\2 g\2\3 tail vss", text, flags=re.M)
    text, n2 = re.subn(r"^Xs[pn]\d+(u\d+)? .+\n(\+ .+\n)+", "", text, flags=re.M)
    assert n1 == n2 == 2 * (2 ** bits - 1), (n1, n2)
    extra = ""
    for side, vin in (("p", "vinp"), ("n", "vinn")):
        for k in range(bits):
            extra += (f"Xi{side}{k}p tb{side}{k} t{side}{k} vdd vdd sky130_fd_pr__pfet_01v8\n+ w={{0.42}} l=0.15\n"
                      f"Xi{side}{k}n tb{side}{k} t{side}{k} vss vss sky130_fd_pr__nfet_01v8\n+ w={{0.42}} l=0.15\n"
                      f"Xg{side}{k}a g{side}{k} t{side}{k} {vin} vss sky130_fd_pr__nfet_01v8\n+ w={{0.42}} l=0.15\n"
                      f"Xg{side}{k}b g{side}{k} tb{side}{k} vss vss sky130_fd_pr__nfet_01v8\n+ w={{0.42}} l=0.15\n")
    i = text.rfind(".ends")
    return text[:i] + extra + text[i:]


TEXT = gate_switched(R10.TEXT, BITS)
DIGITAL = re.compile(r"^X[ig][pn]\d")


class G5(R10.C5):
    def __init__(self, seed, sim, cond, sig):
        super().__init__(seed, sim, cond, R10.combo_sigma(R10.TEXT, "combo_t1"))
        z = {d["name"]: (0.0 if DIGITAL.match(d["name"]) else self.z[d["name"]]) for d in parse(TEXT)}
        self.z = z
        self.circuit = mutate(TEXT, z, sig)


def sig():
    return combo_sigma(TEXT, "gate5b")


def run(start: int, n: int, cond) -> None:
    R12.mkdir(parents=True, exist_ok=True)
    s = sig()
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    tag = f"{cond[0]}{cond[1]:g}V{cond[2]:g}C"
    path = R12 / f"mc_gate5b_{tag}_{start}_{n}.jsonl"
    done = {json.loads(l)["seed"] for l in path.read_text().splitlines()} if path.exists() else set()
    with path.open("a") as f:
        for seed in range(start, start + n):
            if seed in done:
                continue
            res = G5(seed, sim, cond, s).run()
            res["variant"] = "input_x2+unit_trim_x1+5b+gate_switched"
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"g5 seed={seed} b0={res['b0_mv']:+.2f} code={res['code']} m={res['m_mv']:+.2f} "
                  f"covered={res['covered']}", flush=True)


def energy() -> None:
    """Nominal (no mismatch) energy and decision time at +3 mV, code 0 and full-scale codes."""
    import r6_layout_budget as r6
    from r3_mismatch_mc import Trace, circuit_text, get_design, measure
    out = []
    for cond in (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("ff", 1.98, 125.0)):
        for lab, text in (("r10_series_switch", R10.TEXT), ("r12_gate_switched", TEXT)):
            for code in (0, 31, -31):
                p = Point(design_name=NAME, corner=cond[0], vdd_v=cond[1], temperature_c=cond[2],
                          differential_v=3e-3, pair_skew=0.0, trim_code=code, load_ff=5.0, max_step_ps=5.0)
                h = r6.SIM._header(p).replace(circuit_text(get_design(NAME)), text)
                deck = "\n".join([h, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15",
                                  r6.SIM._analysis(p, "p0.tsv"), "quit 0", ".endc", ".end"]) + "\n"
                _, f = R3.ngspice(deck)
                m = R3.measure(Trace(p, np.loadtxt(f["p0.tsv"].splitlines(), skiprows=1), "e", r6.OUT), 3.5)
                row = {"cond": list(cond), "variant": lab, "code": code, "t_ns": m.decision_time_ns,
                       "energy_fj": m.core_energy_fj}
                out.append(row)
                print(json.dumps(row), flush=True)
    R12.mkdir(parents=True, exist_ok=True)
    (R12 / "energy.json").write_text(json.dumps(out, indent=1))


def report() -> None:
    out = {}
    for pat, lab in (("out/r9/mc_combo_5b_*.jsonl", "r10_series"), ("out/r12/mc_gate5b_*.jsonl", "r12_gate")):
        groups = {}
        for f in sorted(HERE.glob(pat)):
            for l in f.read_text().splitlines():
                x = json.loads(l)
                groups.setdefault(f"{lab}@{'|'.join(map(str, x['cond']))}", []).append(x)
        for key, rows in sorted(groups.items()):
            m = np.abs([r["m_mv"] for r in rows])
            b0 = np.array([r["b0_mv"] for r in rows])
            cell = {"n": len(rows), "sigma_b0_mv": float(b0.std()), "max_abs_b0_mv": float(np.abs(b0).max()),
                    "coverage": int(sum(r["covered"] for r in rows)), "abs_m_median": float(np.median(m)),
                    "abs_m_max": float(m.max())}
            for v in (3, 1, 0.5):
                for dl in (0.75, 1.0):
                    o = [e["outcome"] for r in rows for e in r["evals"] if abs(e["v_mv"]) == v and e["deadline_ns"] == dl]
                    cell[f"+-{v:g}mV@{dl:g}ns"] = f"{o.count('correct')}/{len(o)} wrong={o.count('wrong')}"
            t3 = [e["t_ns"] for r in rows for e in r["evals"] if abs(e["v_mv"]) == 3 and e["deadline_ns"] == 3.5]
            cell["worst_t_3mV_ns"] = None if None in t3 else float(max(t3))
            out[key] = cell
    (R12 / "r12_report.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = ARGS[0]
    if cmd == "sigma":
        print(json.dumps(sig(), indent=1))
    elif cmd == "run":
        cond = (ARGS[3], float(ARGS[4]), float(ARGS[5])) if len(ARGS) > 3 else ("tt", 1.8, 27.0)
        run(int(ARGS[1]), int(ARGS[2]), cond)
    elif cmd == "energy":
        energy()
    else:
        report()
