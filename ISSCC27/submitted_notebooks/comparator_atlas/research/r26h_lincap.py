"""r26h fix: d5 (transistor-level CMOS decoder) with a linear hold capacitor on every segment gate, instead of r26f's
nfet MOS capacitor (H1). The state-aware Thevenin fit (r26h_thev.py, R26H_OFF) shows the MOS capacitor keeps
~8 fF on a high (on) gate but only ~2.5 fF on a low (off) gate, and the off gates' fast low-impedance response
carries the rest of the MOS designs' segment loss; a linear capacitor keeps its value in both states. Modelled as an
ideal capacitor to VSS (R26H_LIN in fF; the sky130 MIM cell model is not in the pinned PDK checkout).

  R26H_LIN=<fF> python -B r26h_lincap.py kick     # segment-gate dip + waveform, 5 DNL conditions
  R26H_LIN=<fF> python -B r26h_lincap.py probe    # fine boundaries at 0, +/-3, +/-28, +/-31, gain vs ideal g5
"""
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

import r26g_drv as B

F, G, U, R3 = B.F, B.G, B.U, B.R3
OUT_H = R3.HERE / "out" / "r26h"
OUT_H.mkdir(parents=True, exist_ok=True)
LIN_FF = float(os.environ.get("R26H_LIN", "0"))
TAG = f"d5_lin{LIN_FF:g}"
_ct_b = B.circuit_text


def circuit_text(design):
    text = _ct_b(design)
    if not (B._is_d0(design.name) and LIN_FF):
        return text
    caps = "\n".join(f"Clin{s}{i} g{s}{i} vss {LIN_FF * 1e-15:.12g}" for s in "pn" for i in range(2, 9))
    return text.replace(".ends atlas", caps + "\n.ends atlas")


F.circuit_text = G.D.circuit_text = G.SP.circuit_text = R3.circuit_text = circuit_text
_check_b = G._check_circuit


def _check_circuit(text):
    _check_b(text)
    assert len(re.findall(r"^Clin[pn][2-8] ", text, re.M)) == (14 if LIN_FF else 0)
    assert not re.search(r"^Xhc", text, re.M)


G._check_circuit = _check_circuit
DESIGN = U.register(5, F.K, prefix="d")


def kick():
    assert LIN_FF > 0 and not F.HOLD
    conds = list(G.S.DNL_CONDS)
    with ProcessPoolExecutor(len(conds)) as ex:
        rows = list(ex.map(B._kick, [(c, DESIGN) for c in conds]))
    for r in rows:
        r["lin_ff"] = LIN_FF
        print(TAG, r["cond"], f"dip {r['dip_mv']['seg']:.1f} mV", flush=True)
    (OUT_H / f"kick_{TAG}.json").write_text(json.dumps(rows, indent=1))


def probe(workers=5):
    assert LIN_FF > 0 and not F.HOLD
    part = OUT_H / f"_probe_{TAG}.jsonl"
    done = B._read_jsonl(part)
    have = {tuple(r["cond"]) for r in done}
    jobs = [(DESIGN, c) for c in G.S.DNL_CONDS if tuple(c) not in have]
    with ProcessPoolExecutor(workers) as ex, part.open("a") as fh:
        for r in ex.map(B._probe, jobs):
            r["lin_ff"] = LIN_FF
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            done.append(r)
    ref = {tuple(r["cond"]): r["b_mv"] for r in B._read_jsonl(B.OUT_F / "_probe_k175.jsonl")
           if r["design"].startswith("g")}

    def span(x, c):
        return x[str(c)] - x[str(-c)]

    rows = sorted(done, key=lambda r: G.S.DNL_CONDS.index(tuple(r["cond"])))
    for r in rows:
        b, g = r["b_mv"], ref[tuple(r["cond"])]
        r["gain_vs_ideal"] = {n: span(b, c) / span(g, c) for n, c in (("lsb", 3), ("seg", 28), ("all", 31))}
        print(TAG, r["cond"], " ".join(f"{n} {v:.4f}" for n, v in r["gain_vs_ideal"].items()), flush=True)
    (OUT_H / f"probe_{TAG}.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = B.ARGS[0] if B.ARGS else ""
    if cmd not in ("kick", "probe"):
        raise SystemExit(__doc__)
    globals()[cmd]()
