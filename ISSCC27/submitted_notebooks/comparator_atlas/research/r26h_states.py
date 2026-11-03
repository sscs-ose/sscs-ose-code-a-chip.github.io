"""r26h diagnostic: kick response of all 14 segment gates (on and off) at the boundary codes +/-28 and +/-31.

The r26h matched linear drivers reproduce the code -31 on-gate waveform of d5 / d5 H1 to 0.3 % rms and still miss
their segment loss, so the loss must come from a gate state the code -31 kick does not see. This saves every
segment gate g<side><2..8> at the clock edge for one design and reports, per state (on = gate high, off = gate low),
the largest excursion below and above the static level.

  [R26F_HOLD=1] python -B r26h_states.py                    # CMOS decoder d5 (d5 H1 with the 1 um hold caps)
  R26H_R=.. R26H_C=.. [R26H_COND=..] [R26H_OFF=..] python -B r26h_states.py   # linear Thevenin driver h5
  python -B r26h_states.py fit     # re-derive every fitted driver and write out/r26h/thevenin_state_k175.json

State-aware fit (`fit` recomputes each step from the saved runs and checks it against the run tags):
  1. R_on per condition: a linear driver's on-gate dip area is (injected charge) x R (r26h: R 7 kohm with and without
     C have one area), so R_on = 7 kohm x area(MOS) / area(R 7 kohm), mean of d5 and d5 H1.
  2. C_on per design: 1 / dip is linear in C at fixed R; two kicks at R_on (C = 0, 10 fF) give the C whose on-gate
     dip equals the MOS one (d5, d5 H1).
  3. R_off, C_off: the same two steps on the off (low) gates, from these all-gate runs (code -31).
  4. Segment loss of the symmetric (R_on, C_on) and state-aware (R_on, C_on | R_off, C_off) drivers, of the
     H1 controls with only R_off or only C_off changed, and of d5 with a linear hold capacitor (r26h_lincap.py,
     C = mean C_on(H1) - C_on(d5)), next to the MOS designs (dip_law_k175.json).
"""
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

FAM = "h5" if os.environ.get("R26H_R") else "d5"
if FAM == "h5":
    import r26h_thev as H
    B, OUT_H, TAG, CONDS = H.B, H.OUT_H, H.TAG, H.CONDS
else:  # r26h_thev replaces the decoder netlist, so the CMOS designs come from r26g_drv alone
    import r26g_drv as B
    OUT_H, CONDS = B.R3.HERE / "out" / "r26h", B.G.S.DNL_CONDS
    TAG = "d5_H%g" % B.F.HOLD if B.F.HOLD else "d5"
F, G, R3 = B.F, B.G, B.R3
GATES = [f"g{s}{i}" for s in "pn" for i in range(2, 9)]
CODES = tuple(int(c) for c in os.environ.get("R26H_CODES", "-31,-28,28,31").split(","))


def _job(job):
    cond, design, code = job
    s = G._nominal(design, cond)
    p = F.replace(s.base, differential_v=0.0, trim_code=code)
    vecs = [f"v(xdut.{g})" for g in GATES]
    header = s.sim._header(p).replace(R3.circuit_text(R3.get_design(s.design)), s.circuit)
    header = header.replace(".save v(clk)", ".save " + " ".join(vecs) + " v(clk)")
    lines = [header, ".control", "set wr_singlescale", "set wr_vecnames", "set numdgt=15"]
    lines += [f"alter Vt{side}{b} {cond[1] if side == 'n' else 0:.12g}" for side in "pn" for b in range(5)]
    lines += ["tran 1p 26n 21n 1p", "wrdata w.tsv " + " ".join(vecs), "quit 0", ".endc", ".end"]
    _, files = R3.ngspice("\n".join(lines) + "\n")
    v = np.loadtxt(files["w.tsv"].splitlines(), skiprows=1)
    t = v[:, 0]
    pre, edge = (t > 21.5e-9) & (t < 21.9e-9), (t > 21.9e-9) & (t < 25e-9)
    out = {}
    for i, g in enumerate(GATES):
        x = v[:, i + 1]
        v0 = float(np.mean(x[pre]))
        out[g] = {"v0": v0, "down_mv": float((v0 - x[edge].min()) * 1e3), "up_mv": float((x[edge].max() - v0) * 1e3),
                  "area_mv_ns": float(np.trapezoid(v0 - x[edge], t[edge]) * 1e12)}
    return {"design": design, "cond": list(cond), "code": code, "gates": out}


def main():
    design = H.DESIGN if FAM == "h5" else B.U.register(5, F.K, prefix="d")
    with ProcessPoolExecutor(10) as ex:
        rows = list(ex.map(_job, [(c, design, k) for c in CONDS for k in CODES]))
    tag = TAG
    (OUT_H / f"states_{tag}.json").write_text(json.dumps(rows, indent=1))
    for r in rows:
        on = [g for g, x in r["gates"].items() if x["v0"] > 0.9]
        off = [g for g in GATES if g not in on]
        f = lambda gs, k: max((r["gates"][g][k] for g in gs), default=0.0)  # noqa: E731
        print(tag, r["cond"][0], r["code"], f"on {len(on)} down {f(on, 'down_mv'):6.1f} up {f(on, 'up_mv'):5.1f} | "
              f"off {len(off)} down {f(off, 'down_mv'):6.1f} up {f(off, 'up_mv'):6.1f}", flush=True)


def _rd(name):
    return json.loads((OUT_H / name).read_text())


def _seg_area(r):
    v = r["wave"]["seg_mv"]
    return sum(v[0] - x for x in v)


def _gates(r, on):
    g = [x for x in r["gates"].values() if (x["v0"] > 0.9) == on]
    return sum(x["area_mv_ns"] for x in g) / len(g), sum(x["down_mv"] for x in g) / len(g)


def _c_fit(d0, d10, target):
    return round(max(0.0, (1 / target - 1 / d0) / ((1 / d10 - 1 / d0) / 10)), 1)


def fit():
    by = lambda rows: {r["cond"][0]: r for r in rows}  # noqa: E731
    kick = {"d5": by(json.loads((B.OUT_F / "kick_d5_k175.json").read_text())),
            "H1": by(json.loads((B.OUT_F / "kick_d5_k175_H1.json").read_text()))}
    st = {n: {r["cond"][0]: r for r in _rd(f"states_{t}.json") if r["code"] == -31} for n, t in
          (("d5", "d5"), ("H1", "d5_H1"))}
    law = {r["cond"][0]: r["designs"] for r in json.loads((B.OUT_F / "dip_law_k175.json").read_text())}
    r7 = by(_rd("kick_R7000_C0.json"))
    lin = by(_rd("probe_d5_lin8.3.json"))
    lin_kick = by(_rd("kick_d5_lin8.3.json"))

    def loss(tag, c):
        return 100 * (1 - by(_rd(f"probe_{tag}_{c}.json"))[c]["gain_vs_ideal"]["seg"])

    rows, c_hold = [], []
    for cond in G.S.DNL_CONDS:
        c = cond[0]
        r_on = int(round(7000 * (_seg_area(kick["d5"][c]) + _seg_area(kick["H1"][c])) / 2 / _seg_area(r7[c]), -2))
        d0, d10 = (by(_rd(f"kick_R{r_on}_C{x}_{c}.json"))[c]["dip_mv"]["seg"] for x in (0, 10))
        row = {"cond": list(cond), "r_on_ohm": r_on}
        for n in ("d5", "H1"):
            c_on = _c_fit(d0, d10, kick[n][c]["dip_mv"]["seg"])
            sym = f"R{r_on}_C{c_on:g}"
            m = by(_rd(f"kick_{sym}_{c}.json"))[c]
            a, b = m["wave"]["seg_mv"], kick[n][c]["wave"]["seg_mv"]
            rms = (sum(((a[0] - x) - (b[0] - y)) ** 2 for x, y in zip(a, b)) / len(a)) ** 0.5
            r_off = int(round(r_on * _gates(st[n][c], False)[0] / _gates(by(_rd(f"states_{sym}_{c}.json"))[c],
                                                                         False)[0], -2))
            o0, o10 = (_gates(by(_rd(f"states_{sym}_off{r_off}-{x}_{c}.json"))[c], False)[1] for x in (0, 10))
            c_off = _c_fit(o0, o10, _gates(st[n][c], False)[1])
            mos = law[c]["d5" if n == "d5" else "d5 H1"]
            row[n] = {"c_on_ff": c_on, "r_off_ohm": r_off, "c_off_ff": c_off, "seg_dip_mv": mos["seg_dip_mv"],
                      "on_wave_rms_pct": 100 * rms / mos["seg_dip_mv"], "loss_sym_pct": loss(sym, c),
                      "loss_state_pct": loss(f"{sym}_off{r_off}-{c_off:g}", c), "loss_mos_pct": mos["seg_loss_pct"]}
            if n == "H1":
                row[n]["loss_r_off_only_pct"] = loss(f"{sym}_off{r_off}-{c_on:g}", c)
                row[n]["loss_c_off_only_pct"] = loss(f"{sym}_off{r_on}-{c_off:g}", c)
        c_hold.append(row["H1"]["c_on_ff"] - row["d5"]["c_on_ff"])
        row["lincap"] = {"seg_dip_mv": lin_kick[c]["dip_mv"]["seg"],
                         "loss_pct": 100 * (1 - lin[c]["gain_vs_ideal"]["seg"])}
        rows.append(row)
        print(c, r_on, {n: {k: round(v, 2) for k, v in row[n].items()} for n in ("d5", "H1")},
              {k: round(v, 2) for k, v in row["lincap"].items()}, flush=True)
    lin_ff = round(sum(c_hold) / len(c_hold), 1)
    assert lin_ff == 8.3, lin_ff
    (OUT_H / "thevenin_state_k175.json").write_text(json.dumps({"lincap_ff": lin_ff, "rows": rows}, indent=1))


if __name__ == "__main__":
    if getattr(B, "ARGS", [])[:1] == ["fit"]:
        fit()
    else:
        main()
