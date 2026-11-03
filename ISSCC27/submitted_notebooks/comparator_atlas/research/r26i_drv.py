"""r26i: realisable fixes from the r26h state-aware fit. r26h traced the MOS designs' remaining segment loss to the
off (low) segment gates: the decoder's NMOS pull-down is ~3x stronger than its PMOS pull-up, and r26f's nfet hold
capacitor is depleted when its gate is low. Variants of d5_k175 (transistor-level CMOS decoder), each optionally
with r26f's square nfet hold capacitor (R26F_HOLD=<H um>):

  R26I_MN=<m>   multiplier (1, 2 or 4) on the NMOS (pull-down) of the 14 segment output inverters (nfet 0.65 / 0.5 um)
  R26I_MP=<m>   multiplier (1, 2 or 4) on the PMOS (pull-up) of the same inverters (pfet 1.0 / 0.5 um)
  R26I_PH=<P>   square pfet hold capacitor P x P um on every segment gate (gate on the segment gate, source, drain
                and body on VDD): full gate capacitance when the gate is low, depleted when high, so next to the
                nfet capacitor it gives a nearly state-independent capacitance from PDK devices (no MIM model)

  R26I_MN=.. R26I_MP=.. R26I_PH=.. [R26F_HOLD=H] python -B r26i_drv.py kick    # segment-gate dip, 5 DNL conditions
  ... python -B r26i_drv.py probe                                             # boundaries at 0, +/-3, +/-28, +/-31
  ... python -B r26i_drv.py run                                               # kick (if not saved), then probe
  python -B r26i_drv.py table      # writes out/r26i/fixes_k175.json from the runs, with the r26g / r26h references
"""
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor

import r26g_drv as B

F, G, U, R3 = B.F, B.G, B.U, B.R3
OUT_I = R3.HERE / "out" / "r26i"
OUT_I.mkdir(parents=True, exist_ok=True)
MN = int(os.environ.get("R26I_MN", "1"))
MP = int(os.environ.get("R26I_MP", "1"))
PH = float(os.environ.get("R26I_PH", "0"))
assert MN in (1, 2, 4) and MP in (1, 2, 4), "r26f's netlist check rejects m = 8 / 16"
TAG = f"d5_n{MN}_p{MP}_H{F.HOLD:g}_P{PH:g}"
AREA_N, AREA_P = 0.65 * 0.5, 1.0 * 0.5  # um2 per output-stage device
_ct_b = B.circuit_text


def _scale(mt):
    block = mt.group(1)
    src = block.split()[3]
    m = MN if src == "vss" else MP
    return block + (f"\n+ m={m}" if m > 1 else "")


def circuit_text(design):
    text = _ct_b(design)
    if not B._is_d0(design.name):
        return text
    text, n = B._OUT_INV.subn(_scale, text)
    assert n == 28, n
    if PH:
        caps = "\n".join(f"Xhq{s}{i} vdd g{s}{i} vdd vdd sky130_fd_pr__pfet_01v8\n+ w={{{PH:g}}} l={PH:g}\n"
                         f"+ ad={{0.29*({PH:g})}} as={{0.29*({PH:g})}}\n"
                         f"+ pd={{2*(0.29+({PH:g}))}} ps={{2*(0.29+({PH:g}))}}"
                         for s in "pn" for i in range(2, 9))
        text = text.replace(".ends atlas", caps + "\n.ends atlas")
    return text


F.circuit_text = G.D.circuit_text = G.SP.circuit_text = R3.circuit_text = circuit_text


def _check_circuit(text):
    B._check_d(text)
    assert not re.search(r"^Xlb", text, re.M)
    scaled = re.findall(r"^Xdc[pn]\d+ g[pn]\d \S+ (vdd|vss) [^\n]*\n(?:\+[^\n]*\n){3}\+ m=(\d+)", text, re.M)
    want = [("vss", MN)] * 14 * (MN > 1) + [("vdd", MP)] * 14 * (MP > 1)
    assert sorted((s, int(m)) for s, m in scaled) == sorted(want), scaled
    assert len(re.findall(r"^Xhq[pn][2-8] vdd \S+ vdd vdd sky130_fd_pr__pfet_01v8$", text, re.M)) == (14 if PH else 0)
    assert len(re.findall(r"^Xhc[pn][2-8] ", text, re.M)) == (14 if F.HOLD else 0)


G._check_circuit = _check_circuit
DESIGN = U.register(5, F.K, prefix="d")


def area_um2(mn=None, mp=None, hold=None, ph=None):
    """Added area per segment gate over d5 (um2): extra output-stage width plus hold-capacitor gate area."""
    mn, mp = MN if mn is None else mn, MP if mp is None else mp
    hold, ph = F.HOLD if hold is None else hold, PH if ph is None else ph
    return (mn - 1) * AREA_N + (mp - 1) * AREA_P + hold ** 2 + ph ** 2


def kick():
    conds = list(G.S.DNL_CONDS)
    with ProcessPoolExecutor(len(conds)) as ex:
        rows = list(ex.map(B._kick, [(c, DESIGN) for c in conds]))
    for r in rows:
        r.update(mn=MN, mp=MP, ph_um=PH)
        print(TAG, r["cond"], f"dip {r['dip_mv']['seg']:.1f} mV", flush=True)
    (OUT_I / f"kick_{TAG}.json").write_text(json.dumps(rows, indent=1))


def _span(x, c):
    return x[str(c)] - x[str(-c)]


def probe(workers=5):
    part = OUT_I / f"_probe_{TAG}.jsonl"
    done = B._read_jsonl(part)
    have = {tuple(r["cond"]) for r in done}
    only = [c for c in os.environ.get("R26I_CONDS", "").split(",") if c]  # e.g. "tt,ss"; default all five
    todo = [c for c in G.S.DNL_CONDS if tuple(c) not in have and (not only or c[0] in only)]
    with ProcessPoolExecutor(workers) as ex, part.open("a") as fh:
        for r in ex.map(B._probe, [(DESIGN, c) for c in todo]):
            r.update(mn=MN, mp=MP, ph_um=PH, hold_um=F.HOLD)
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            done.append(r)
    if len(done) < len(G.S.DNL_CONDS):
        return
    ref = {tuple(r["cond"]): r["b_mv"] for r in B._read_jsonl(B.OUT_F / "_probe_k175.jsonl")
           if r["design"].startswith("g")}
    rows = sorted(done, key=lambda r: G.S.DNL_CONDS.index(tuple(r["cond"])))
    for r in rows:
        b, g = r["b_mv"], ref[tuple(r["cond"])]
        r["gain_vs_ideal"] = {n: _span(b, c) / _span(g, c) for n, c in (("lsb", 3), ("seg", 28), ("all", 31))}
        print(TAG, r["cond"], " ".join(f"{n} {v:.4f}" for n, v in r["gain_vs_ideal"].items()), flush=True)
    (OUT_I / f"probe_{TAG}.json").write_text(json.dumps(rows, indent=1))


def run():
    """kick (unless saved) then probe, 3 workers, so that several variants can run side by side"""
    if not (OUT_I / f"kick_{TAG}.json").exists():
        kick()
    probe(3)


def table():
    """Segment dip (mV) and segment loss (%) per condition for every r26i run, next to d5, d5 H1 / H2 (r26g) and d5
    with an ideal linear 8.3 fF capacitor (r26h); added area per segment gate over d5."""
    conds = [list(c) for c in G.S.DNL_CONDS]
    law = json.loads((B.OUT_F / "dip_law_k175.json").read_text())
    designs = {}
    for lab, h in (("d5", 0), ("d5 H1", 1), ("d5 H2", 2)):
        designs[lab] = {"mn": 1, "mp": 1, "hold_um": h, "ph_um": 0, "area_um2": area_um2(1, 1, h, 0),
                        "rows": [{"cond": r["cond"], "seg_dip_mv": r["designs"][lab]["seg_dip_mv"],
                                  "seg_loss_pct": r["designs"][lab]["seg_loss_pct"]} for r in law]}
    lin = {tuple(r["cond"]): r for r in json.loads((OUT_I.parent / "r26h" / "thevenin_state_k175.json").read_text())
           ["rows"]}
    designs["d5 + 8.3 fF linear (r26h)"] = {
        "mn": 1, "mp": 1, "hold_um": 0, "ph_um": 0, "area_um2": None,
        "rows": [{"cond": c, "seg_dip_mv": lin[tuple(c)]["lincap"]["seg_dip_mv"],
                  "seg_loss_pct": lin[tuple(c)]["lincap"]["loss_pct"]} for c in conds]}
    for p in sorted(OUT_I.glob("probe_d5_n*_p*_H*_P*.json")):
        tag = p.stem[len("probe_"):]
        mn, mp, h, ph = re.fullmatch(r"d5_n(\d+)_p(\d+)_H([\d.]+)_P([\d.]+)", tag).groups()
        kick_rows = {tuple(r["cond"]): r for r in json.loads((OUT_I / f"kick_{tag}.json").read_text())}
        prow = {tuple(r["cond"]): r for r in json.loads(p.read_text())}
        if (mn, mp, ph) == ("1", "1", "0") and h in ("0", "1", "2"):  # plain rerun: must reproduce r26g
            ref = designs["d5" + (f" H{h}" if h != "0" else "")]["rows"]
            err = max(abs(100 * (1 - prow[tuple(c)]["gain_vs_ideal"]["seg"]) - r["seg_loss_pct"])
                      for c, r in zip(conds, ref))
            assert err < 0.005, (tag, err)
            print(f"{tag} reproduces r26g within {err:.4f} pp")
            continue
        lab = " ".join(x for x in ("d5", f"N{mn}" * (mn != "1"), f"P{mp}" * (mp != "1"),
                                   f"H{h}" * (h != "0"), f"PH{ph}" * (ph != "0")) if x)
        designs[lab] = {"mn": int(mn), "mp": int(mp), "hold_um": float(h), "ph_um": float(ph),
                        "area_um2": round(area_um2(int(mn), int(mp), float(h), float(ph)), 3),
                        "rows": [{"cond": c, "seg_dip_mv": kick_rows[tuple(c)]["dip_mv"]["seg"],
                                  "seg_loss_pct": 100 * (1 - prow[tuple(c)]["gain_vs_ideal"]["seg"])}
                                 for c in conds]}
    for lab, d in designs.items():
        d["worst_loss_pct"] = max(r["seg_loss_pct"] for r in d["rows"])
        print(f"{lab:28s} area {d['area_um2']}  " + "  ".join(
            f"{r['cond'][0]} {r['seg_dip_mv']:.0f}/{r['seg_loss_pct']:.2f}" for r in d["rows"])
            + f"  worst {d['worst_loss_pct']:.2f}")
    (OUT_I / "fixes_k175.json").write_text(json.dumps({"conds": conds, "designs": designs}, indent=1))


if __name__ == "__main__":
    U.os.environ.pop("R24_PRIOR_MV", None)
    cmd = B.ARGS[0] if B.ARGS else ""
    if cmd not in ("kick", "probe", "run", "table"):
        raise SystemExit(__doc__)
    globals()[cmd]()
