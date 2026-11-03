"""r26h: is the extra boundary loss of strong drivers (r26g: s5 loses 20 - 45 % more per mV of gate dip than the hold
capacitor) a property of the gate waveform or of the MOS driver? Design family h5_k<100k>: g5_k<100k> with each of
the 14 ideal segment sources moved behind a linear Thevenin driver, ideal source -> series R -> gate, plus an ideal
shunt C from gate to VSS (R26H_R in ohm, R26H_C in fF; LSB switches stay on ideal sources, as in d5). A linear RC
driver has no junction or Miller capacitance and no nonlinearity, so if (R, C) points with the dip of a MOS design
also have its loss, the loss is set by the gate waveform; if not, by the driver device.

  R26H_R=<ohm> R26H_C=<fF> python -B r26h_thev.py kick     # segment-gate dip + waveform, 5 DNL conditions
  R26H_R=<ohm> R26H_C=<fF> python -B r26h_thev.py probe    # fine boundaries at 0, +/-3, +/-28, +/-31
  R26H_OFF=<ohm>:<fF> ...                                 # state-aware: off (low) gates get R_off, C_off
  R26H_COND=<tt|ss|fs|sf|ff> ...                          # one condition only (files tagged _<cond>)
  python -B r26h_thev.py table                             # dip and loss of every h5 point vs d5 / s5 / hold caps
"""
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

import r26g_drv as B

F, G, U, R3 = B.F, B.G, B.U, B.R3
OUT_H = R3.HERE / "out" / "r26h"
OUT_H.mkdir(parents=True, exist_ok=True)
R_OHM = float(os.environ.get("R26H_R", "0"))
C_FF = float(os.environ.get("R26H_C", "0"))
COND = os.environ.get("R26H_COND", "")
OFF = os.environ.get("R26H_OFF", "")  # "<ohm>:<fF>": off (low) gates get their own R and C (state-aware driver)
R_OFF, C_OFF = (float(x) for x in OFF.split(":")) if OFF else (0.0, 0.0)
TAG = f"R{R_OHM:g}_C{C_FF:g}" + (f"_off{R_OFF:g}-{C_OFF:g}" if OFF else "") + (f"_{COND}" if COND else "")
CONDS = [c for c in G.S.DNL_CONDS if not COND or c[0] == COND]
_BDEC = re.compile(r"^Bdec([pn])(\d) g\1\2 vss ", re.M)
_is_g0, _ct_g, _check0 = G._is_g, G.circuit_text, G._check_circuit


def _is_h(name):
    return name.startswith("h") and name[1:2].isdigit()


def circuit_text(design):
    if not _is_h(design.name):
        return _ct_g(design)
    assert R_OHM > 0, "set R26H_R"

    def thev(mt):
        s, i = mt.group(1), mt.group(2)
        if not OFF:
            extra = f"Rth{s}{i} gi{s}{i} g{s}{i} {R_OHM:.12g}\n"
            if C_FF:
                extra += f"Cth{s}{i} g{s}{i} vss {C_FF * 1e-15:.12g}\n"
            return extra + f"Bdec{s}{i} gi{s}{i} vss "
        # state-aware: the ideal decoder output (vdd or 0) selects R; each C sits on a node that is grounded in its
        # own state and follows the gate otherwise, so it carries no current there
        on, g = f"(v(gi{s}{i}) > 0.5*v(vdd))", f"v(g{s}{i})"
        extra = f"Bth{s}{i} gi{s}{i} g{s}{i} I=v(gi{s}{i},g{s}{i})/({on} ? {R_OHM:.12g} : {R_OFF:.12g})\n"
        for st, c, v_on, v_off in (("on", C_FF, "0", g), ("off", C_OFF, g, "0")):
            if c:
                extra += (f"Cth{st}{s}{i} g{s}{i} c{st}{s}{i} {c * 1e-15:.12g}\n"
                          f"Bc{st}{s}{i} c{st}{s}{i} vss V={on} ? {v_on} : {v_off}\n")
        return extra + f"Bdec{s}{i} gi{s}{i} vss "

    text, n = _BDEC.subn(thev, _ct_g(design))
    assert n == 14, n
    return text


def _check_circuit(text):
    if "Rth" not in text and "Bth" not in text:
        return _check0(text)
    assert text.count("Bdec") == 14 and len(re.findall(r"^[RB]th[pn]\d ", text, re.M)) == 14
    assert len(re.findall(r"^Cth(?:on|off)?[pn]\d ", text, re.M)) == 14 * ((C_FF > 0) + (C_OFF > 0))
    assert not re.search(r"^Xdc|^Xlb|^Xhc", text, re.M)
    assert re.search(r"Xeq_8 [^\n]*\n(\+[^\n]*\n){3}\+ m=4", text)


G._is_g = lambda name: _is_g0(name) or _is_h(name)
F.circuit_text = G.D.circuit_text = G.SP.circuit_text = R3.circuit_text = circuit_text
G._check_circuit = _check_circuit
DESIGN = U.register(5, F.K, prefix="h")
for _p in "gdbs":
    U.register(5, F.K, prefix=_p)


def kick():
    conds = list(CONDS)
    with ProcessPoolExecutor(len(conds)) as ex:
        rows = list(ex.map(B._kick, [(c, DESIGN) for c in conds]))
    for r in rows:
        r.update(r_ohm=R_OHM, c_ff=C_FF)
        print(TAG, r["cond"], f"dip {r['dip_mv']['seg']:.1f} mV", flush=True)
    (OUT_H / f"kick_{TAG}.json").write_text(json.dumps(rows, indent=1))


def probe(workers=5):
    part = OUT_H / f"_probe_{TAG}.jsonl"
    done = B._read_jsonl(part)
    have = {tuple(r["cond"]) for r in done}
    jobs = [(DESIGN, c) for c in CONDS if tuple(c) not in have]
    with ProcessPoolExecutor(workers) as ex, part.open("a") as fh:
        for r in ex.map(B._probe, jobs):
            r.update(r_ohm=R_OHM, c_ff=C_FF)
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


def table():
    """Segment dip and segment loss of every probed h5 point, next to the r26g MOS designs (dip_law_k175.json)."""
    law = {tuple(r["cond"]): r["designs"] for r in json.loads((B.OUT_F / "dip_law_k175.json").read_text())}
    rows = []
    for p in sorted(OUT_H.glob("probe_R*_C*.json")):
        tag = p.stem[len("probe_"):]
        if tag.count("_") > 1:
            continue
        kick_rows = {tuple(r["cond"]): r for r in json.loads((OUT_H / f"kick_{tag}.json").read_text())}
        for r in json.loads(p.read_text()):
            k = kick_rows[tuple(r["cond"])]
            dip = k["dip_mv"]["seg"]
            loss = 100 * (1 - r["gain_vs_ideal"]["seg"])
            rows.append({"r_ohm": r["r_ohm"], "c_ff": r["c_ff"], "cond": r["cond"], "seg_dip_mv": dip,
                         "seg_loss_pct": loss, "full_loss_pct": 100 * (1 - r["gain_vs_ideal"]["all"]),
                         "seg_loss_pct_per_mv": loss / dip if dip > 0 else None})
    rows.sort(key=lambda x: (G.S.DNL_CONDS.index(tuple(x["cond"])), x["r_ohm"], x["c_ff"]))
    for x in rows:
        mos = law[tuple(x["cond"])]
        print(f"{x['cond']} R {x['r_ohm']:>6g} C {x['c_ff']:>4g}  dip {x['seg_dip_mv']:6.1f}  loss "
              f"{x['seg_loss_pct']:.2f} %  {x['seg_loss_pct_per_mv'] or 0:.4f} %/mV   (d5 "
              f"{mos['d5']['seg_loss_pct_per_mv']:.4f}, s5 {mos['s5']['seg_loss_pct_per_mv']:.4f}, H1 "
              f"{mos['d5 H1']['seg_loss_pct_per_mv']:.4f})", flush=True)
    (OUT_H / "thevenin_k175.json").write_text(json.dumps({"points": rows, "mos": {
        "|".join(map(str, c)): v for c, v in law.items()}}, indent=1))


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = B.ARGS[0] if B.ARGS else ""
    if cmd not in ("kick", "probe", "table"):
        raise SystemExit(__doc__)
    globals()[cmd]()
