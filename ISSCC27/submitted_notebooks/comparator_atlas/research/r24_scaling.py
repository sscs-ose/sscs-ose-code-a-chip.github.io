"""r24 scaling: why the comparator's input-referred noise moves across PVT, in closed form.

Along the noiseless switching-input trajectory (same deck as r24_isf.traj) ngspice reports the BSIM4
small-signal state of the input pair (gm, Id) and the latch NMOS. With the r23 noise PSD S_id(t) of the
same devices this gives gamma(t) = S_id / (4 kT gm), and the integration-phase charge law

    sigma_in^2 = 4 kT gamma / (gm t_int) = 4 kT gamma (Id/gm) / Q_int,     Q_int = Id t_int

is tested against the exact ISF result of every atlas condition.
  python -B r24_scaling.py op <design> <corner> <vdd> <temp>
  python -B r24_scaling.py feat <design> <corner> <vdd> <temp>        # closed-form ingredients + exact ISF
  python -B r24_scaling.py isf <design> <corner> <vdd> <temp> <workers> # fast ISF, then feat
  python -B r24_scaling.py fit <design>                               # closed form vs the atlas
  python -B r24_scaling.py pairs <design> <corner> <vdd> <temp> [prune]  # MC vs ISF per realization
  python -B r24_scaling.py report                                     # r24 archive files (after fit)
With R24_PRIOR_MV / R24_CM_V set (see r24_isf) every result goes to the matching out/r24 subfolder.
"""
import json
import sys

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r24_isf as R  # noqa: E402
from r24_isf import N, R3  # noqa: E402

K_B = 1.380649e-23
INST = {"nfet_01v8_lvt": "msky130_fd_pr__nfet_01v8_lvt", "nfet_01v8": "msky130_fd_pr__nfet_01v8",
        "pfet_01v8": "msky130_fd_pr__pfet_01v8"}
OP_DEVICES = ("Xinp", "Xinn", "Xln", "Xlp", "Xtail")
PARAMS = ("gm", "id", "gds")


def _vec(d, p):
    return f"@m.xdut.{d['name'].lower()}.{INST[d['device']]}[{p}]"


def op(design, corner, vdd, temp):
    """gm, Id, gds of the input pair, latch NMOS and tail along the noiseless trajectory (0.5 ps grid)."""
    path = R.OUT / f"op_{R.tag(design, corner, vdd, temp)}.npz"
    if path.exists():
        return path
    R.OUT.mkdir(parents=True, exist_ok=True)
    b0 = R.b0_of(design, corner, vdd, temp)
    devs = {d["name"]: d for d in N.devices(design) if d["name"] in OP_DEVICES}
    vecs = [_vec(devs[n], p) for n in OP_DEVICES for p in PARAMS]
    nodes = ["v(xdut.xp)", "v(xdut.xn)", "v(qp)", "v(qn)", "v(xdut.tail)"]
    header = R._header(design, corner, vdd, temp) + ".save " + " ".join(vecs + nodes) + "\n"
    cm, b = 0.5 * vdd, b0 * 1e-3
    lines = [header, ".control", "set numdgt=12", f"alter Vinp {cm + b / 2:.12g}", f"alter Vinn {cm - b / 2:.12g}",
             f"tran {R.TRAJ_DT:.3e} {N.DEADLINE_S:.6e} 19n {R.TRAJ_DT:.3e}", "linearize " + " ".join(vecs + nodes),
             "set wr_singlescale", "wrdata op.tsv " + " ".join(vecs + nodes), "quit 0", ".endc", ".end"]
    _, files = R3.ngspice("\n".join(lines) + "\n")
    arr = np.array([[float(v) for v in ln.split()] for ln in files["op.tsv"].splitlines() if ln.strip()])
    np.savez_compressed(path, t=arr[:, 0], data=arr[:, 1:].T,
                        names=np.array([f"{n}.{p}" for n in OP_DEVICES for p in PARAMS] + nodes))
    return path


def load_op(design, corner, vdd, temp):
    z = np.load(op(design, corner, vdd, temp))
    return z["t"], dict(zip([str(n) for n in z["names"]], z["data"]))


def features(design, corner, vdd, temp, exact=True):
    """Closed-form ingredients of one condition, all from noiseless quantities; with exact=True also the
    ISF result (needs the fast ISF file)."""
    t, o = load_op(design, corner, vdd, temp)
    tt, lns, _ = R.load_traj(design, corner, vdd, temp)
    kt = K_B * (temp + 273.15)
    edge = R.EDGE_S
    after = t > edge
    xcm = 0.5 * (o["v(xdut.xp)"] + o["v(xdut.xn)"])
    t_int = float(t[after][np.argmax(xcm[after] < vdd / 2)] - edge)
    win = (t > edge) & (t <= edge + t_int)
    gm = 0.5 * (np.abs(o["Xinp.gm"]) + np.abs(o["Xinn.gm"]))
    idd = 0.5 * (np.abs(o["Xinp.id"]) + np.abs(o["Xinn.id"]))
    s_in = 0.5 * (np.exp(np.interp(t, tt, lns["Xinp"])) + np.exp(np.interp(t, tt, lns["Xinn"])))
    gm_bar = float(np.mean(gm[win]))
    id_bar = float(np.mean(idd[win]))
    q_int = float(np.trapezoid(idd[win], t[win]))
    gamma = float(np.mean(s_in[win]) / (4 * kt * gm_bar))
    cf_in = 4 * kt * gamma * (id_bar / gm_bar) / q_int
    res = {"condition": [corner, vdd, temp], "kT_zJ": kt * 1e21, "gamma": gamma, "gm_mS": gm_bar * 1e3,
           "id_uA": id_bar * 1e6, "id_over_gm_mV": id_bar / gm_bar * 1e3, "t_int_ps": t_int * 1e12,
           "q_int_fC": q_int * 1e15, "sigma_cf_in_mv": float(np.sqrt(cf_in) * 1e3)}
    if exact:
        pred = R.predict(design, corner, vdd, temp, fast=True)
        var_in = sum(pred["var_v2"][n] for n in N.GROUPS["input"])
        res.update({"sigma_mv": pred["sigma_mv"], "sigma_in_mv": float(np.sqrt(var_in) * 1e3),
                    "input_share": var_in / sum(pred["var_v2"].values()),
                    "group_sigma_mv": pred["group_sigma_mv"]})
    return res


def fit(design):
    rows = []
    for line in open(R.OUT / f"atlas_{design}.jsonl"):
        c = json.loads(line)["condition"]
        rows.append(features(design, *c))
        r = rows[-1]
        print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
    ratio = np.array([r["sigma_in_mv"] / r["sigma_cf_in_mv"] for r in rows])
    print(f"exact/closed-form (input pair): mean {ratio.mean():.3f} sd {ratio.std():.3f} "
          f"min {ratio.min():.3f} max {ratio.max():.3f} n {len(rows)}")
    (R.OUT / f"scaling_{design}.json").write_text(json.dumps(rows, indent=1))
    return rows


def pairs(design, corner, vdd, temp, prune):
    """Per-realization MC shift (archived r23 run files under N.OUT) next to the ISF prediction of the same
    noise sequence, plus the ISF sigma, its group split and the timing of this bench."""
    pattern = f"run_{N.tag(design, corner, vdd, temp, 2e-12, prune)}_s*.jsonl"
    rows = [json.loads(ln) for p in sorted(N.OUT.glob(pattern)) for ln in p.read_text().splitlines() if ln.strip()]
    rows.sort(key=lambda r: r["realization"])
    assert rows, pattern
    pred = R.predict(design, corner, vdd, temp, fast=True)
    return {"design": design, "condition": [corner, vdd, temp], "noise": prune or "all",
            "realization": [r["realization"] for r in rows], "mc_mv": [r["noise_mv"] for r in rows],
            "isf_mv": [R.realization_shift(design, corner, vdd, temp, r["realization"], fast=True) for r in rows],
            "edge": sum(bool(r["edge"]) for r in rows), "isf_sigma_mv": pred["sigma_mv"],
            "group_sigma_mv": pred["group_sigma_mv"], **R.timing(design, corner, vdd, temp, fast=True)}


BENCHES = (
    # bench, env, design, corner, vdd, temp, noisy devices (r23 run suffix)
    ("original", {}, "lvt_balanced_4b", "tt", 1.8, 27.0, "prune"),
    ("original", {}, "lvt_balanced_4b", "ss", 1.62, -40.0, "prune"),
    ("original", {}, "lvt_balanced_4b", "sf", 1.95, 125.0, "prune"),
    ("original", {}, "baseline", "tt", 1.8, 27.0, ""),
    ("original", {}, "lvt_base_3b", "tt", 1.8, 27.0, ""),
    ("original", {}, "unit6_w6", "tt", 1.8, 27.0, "prune"),
    ("pinned", {"R24_PRIOR_MV": "-5"}, "lvt_balanced_4b", "tt", 1.8, 27.0, "prune"),
    ("pinned", {"R24_PRIOR_MV": "-5"}, "unit6_w6", "tt", 1.8, 27.0, "prune"),
    ("pinned, CM 0.6 V", {"R24_PRIOR_MV": "-5", "R24_CM_V": "0.6"}, "lvt_balanced_4b", "tt", 1.8, 27.0, "prune"),
)
CM_SWEEP = ("0.6", "0.7", None, "1.1")


def _child(env, *args):
    import os
    import subprocess
    e = {k: v for k, v in os.environ.items() if k not in ("R24_PRIOR_MV", "R24_CM_V")}
    e.update(env, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-B", __file__, *map(str, args)], env=e, capture_output=True, text=True,
                         check=True, cwd=R.HERE).stdout
    return json.loads(out.strip().splitlines()[-1])


def report(design="lvt_balanced_4b"):
    """Archive files for r24 in out/r24: r24_report.json (validation pairs, CM sweep, closed-form fit) and the
    pinned-bench atlas. Each bench runs in a child process because the bench is chosen at import."""
    import shutil
    pinned = R.HERE / "out" / "r24" / "prior-5"
    validation = []
    for bench, env, d, c, v, t, prune in BENCHES:
        validation.append({"bench": bench, **_child(env, "pairs", d, c, v, t, prune)})
        print(bench, d, c, v, t, flush=True)
    sweep = []
    for cm in CM_SWEEP:
        env = {"R24_PRIOR_MV": "-5", **({"R24_CM_V": cm} if cm else {})}
        sweep.append({"cm_v": float(cm) if cm else 0.9, **_child(env, "sweep", design, "tt", 1.8, 27.0)})
    scaling = json.loads((pinned / f"scaling_{design}.json").read_text())
    out = R.HERE / "out" / "r24"
    (out / "r24_report.json").write_text(json.dumps({"validation": validation, "cm_sweep": sweep,
                                                     "scaling": scaling}, indent=1))
    shutil.copyfile(pinned / f"atlas_{design}.jsonl", out / f"atlas_pinned_{design}.jsonl")
    return out / "r24_report.json"


def _gain_rows(rows, a0, k=None):
    """Gain-suppression law sigma^2 = sigma_in^2 * (1 + (A0/A_int)^2), A_int = (gm/Id) * VDD/2; sigma_in is the
    exact ISF input-pair term, or k * the closed-form input law when k is given."""
    out = []
    for r in rows:
        a_int = r["condition"][1] / 2 / (r["id_over_gm_mV"] * 1e-3)
        s_in = r["sigma_in_mv"] if k is None else k * r["sigma_cf_in_mv"]
        pred = s_in * np.sqrt(1 + (a0 / a_int) ** 2)
        out.append({"condition": r["condition"], "a_int": a_int, "sigma_mv": r["sigma_mv"], "pred_mv": float(pred),
                    "err": float(pred / r["sigma_mv"] - 1)})
    return out


def _a0(rows):
    a = np.array([r["condition"][1] / 2 / (r["id_over_gm_mV"] * 1e-3) for r in rows])
    excess = np.array([(r["sigma_mv"] / r["sigma_in_mv"]) ** 2 - 1 for r in rows])
    return float(np.exp(np.mean(0.5 * np.log(excess) + np.log(a))))


def _stats(e):
    e = np.abs([r["err"] for r in e])
    return {"rms": float(np.sqrt(np.mean(e ** 2))), "max": float(e.max())}


def gainlaw(path=None):
    """r24c: fit A0 on the 45 pinned PVT conditions (leave-one-corner-out too) and test it on the CM sweep.
    Writes out/r24/gain_law.json."""
    path = path or (R.HERE / "out" / "r24" / "r24_report.json")
    rep = json.loads(path.read_text())
    rows, cm = rep["scaling"], rep["cm_sweep"]
    a0 = _a0(rows)
    k = float(np.exp(np.mean(np.log([r["sigma_in_mv"] / r["sigma_cf_in_mv"] for r in rows]))))
    share = []
    for b in rep["validation"] + cm:
        g = b["group_sigma_mv"]
        share.append(abs(g["reset"] ** 2 / sum(v ** 2 for v in g.values()) - b["pre_edge_share"]))
    loco = {}
    for corner in sorted({r["condition"][0] for r in rows}):
        train = [r for r in rows if r["condition"][0] != corner]
        test = [r for r in rows if r["condition"][0] == corner]
        a = _a0(train)
        loco[corner] = {"a0": a, **_stats(_gain_rows(test, a))}
    input_only = [{"err": k * r["sigma_cf_in_mv"] / r["sigma_mv"] - 1} for r in rows]
    res = {"a0": a0, "k_input": k, "pvt_exact_in": _stats(_gain_rows(rows, a0)),
           "pvt_closed_form": _stats(_gain_rows(rows, a0, k)), "pvt_input_only": _stats(input_only),
           "leave_one_corner_out": loco,
           "a_int_range_pvt": [min(r["a_int"] for r in _gain_rows(rows, a0)),
                               max(r["a_int"] for r in _gain_rows(rows, a0))],
           "cm_sweep": [{"cm_v": c["cm_v"], **e, "pred_closed_mv": f["pred_mv"], "err_closed": f["err"]}
                        for c, e, f in zip(cm, _gain_rows(cm, a0), _gain_rows(cm, a0, k))],
           "reset_vs_pre_edge_share_max_abs": max(share), "share_benches": len(share),
           "rows": _gain_rows(rows, a0)}
    (R.HERE / "out" / "r24" / "gain_law.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    cmd = ARGS[0]
    if cmd == "op":
        print(op(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4])))
    elif cmd == "feat":
        print(json.dumps(features(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4])), indent=1))
    elif cmd == "fit":
        fit(ARGS[1])
    elif cmd == "isf":
        R.isf(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4]), workers=int(ARGS[5]), fast=True)
        print(json.dumps(features(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4]))))
    elif cmd == "pairs":
        print(json.dumps(pairs(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4]), (ARGS[5:] or [""])[0])))
    elif cmd == "sweep":
        cond = (ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4]))
        print(json.dumps({**features(*cond), **R.timing(*cond, fast=True)}))
    elif cmd == "report":
        print(report())
    elif cmd == "gainlaw":
        r = gainlaw()
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=1))
    else:
        raise SystemExit(__doc__)
