"""r23: transient thermal noise of the compared comparators (input-referred noise and +/-1 mV error rate).

ngspice has no device noise in transient analysis, so each MOSFET gets an explicit drain-source noise
current i_n(t) = sqrt(S_id(Vds, Vgs, Vbs)) * xi(t). S_id is the white (thermal) drain-current noise
of the pinned SKY130 BSIM4 model itself, tabulated per device geometry, corner and temperature by
ngspice .noise at 10 GHz (where flicker noise is negligible), stored as ln S_id and read back in
transient through the XSPICE table3D model. xi(t) is a seeded unit-PSD white sequence (Gaussian,
variance 1/(2 dt), piecewise linear) switched on from 20 ns, two nanoseconds before the evaluated
clock edge, so reset (kT/C) noise is included. Flicker noise and induced gate noise are not modelled.

For one noise realization the decision is a deterministic function of the input, so the switching
input is found by bisection inside one ngspice deck; across realizations the switching inputs give
the input-referred noise distribution directly (noiseless switching input subtracted).
  python -B r23_noise.py tables <design> <corner> <vdd> <temp>
  python -B r23_noise.py validate [dt_ps]               # on-switch kT/C check, NMOS and PMOS, against .noise
  python -B r23_noise.py run <design> <corner> <vdd> <temp> <start> <n> [dt_ps] [prune|only:<group>]
  python -B r23_noise.py report [dt_ps]                 # archived report: report 2
Archived runs use dt = 2 ps and realizations 0-39 (groups 0-23); "prune" leaves the off trim branches
(Xt*/Xs*) noiseless; "only:<group>" keeps one GROUPS entry noisy. Finer dt grids split each 2 ps value
into equal-mean, independent halves, so dt = 1 and 0.5 ps runs are paired with the 2 ps ones.
"""
import json
import math
import re
import sys
import zlib
from pathlib import Path

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r3_mismatch_mc as R3  # noqa: E402  (puts the desktop root on sys.path)
from comparator_atlas.designs import DESIGNS, Design  # noqa: E402
from r3_mismatch_mc import HERE, Point, Simulator, circuit_text, get_design  # noqa: E402
from r7_trim_dnl import unit_array  # noqa: E402

OUT = HERE / "out" / "r23"
TAB = HERE / "cache" / "r23"
K_B = 1.380649e-23
NOISE_ON_S = 20e-9
NOISE_OFF_S = 25.6e-9
DEADLINE_S = 22.025e-9 + 3.5e-9
BISECT = 10
SPAN_MV = 6.0
FULL_X = np.round(np.arange(-2.0, 2.0001, 0.05), 4)
FULL_Y = np.round(np.arange(-2.0, 2.0001, 0.05), 4)
FULL_Z = np.round(np.arange(-2.0, 0.0001, 0.2), 4)
FLOOR = 1e-36
BASELINE_PARAMS = {"pair_skew": 0.0, "input_w": 2.0, "input_l": 0.15, "trim_l": 1.0}
MOS = re.compile(r"^(X\w+) (\S+) (\S+) (\S+) (\S+) sky130_fd_pr__(\w+)$")

DESIGNS["unit6_w6"] = Design("unit6_w6", input_device="nfet_01v8_lvt", input_w=6, tail_w=7, trim_bits=6)
DESIGNS["u6_w12_l05"] = Design("u6_w12_l05", input_device="nfet_01v8_lvt", input_w=12, tail_w=7, trim_l=0.5,
                               trim_bits=6)
UNIT = {"unit6_w6", "u6_w12_l05"}


def ngspice_long(deck, timeout=7200):
    """R3.ngspice with a longer timeout (unpruned 6-bit bisection decks exceed R3's 900 s)."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory(dir=HERE / "cache") as tmp:
        Path(tmp, ".spiceinit").write_text(R3.SPICE_INIT, encoding="ascii")
        Path(tmp, "a.cir").write_text(deck, encoding="utf-8")
        r = subprocess.run([str(R3.NG), "-b", "a.cir"], cwd=tmp, capture_output=True, text=True, timeout=timeout)
        out = r.stdout + r.stderr
        if r.returncode != 0 or re.search(r"(?im)^\s*(error|fatal)\b|timestep too small", out):
            raise RuntimeError(out[-2000:])
    return out, {}


GROUPS = {"input": ("Xinp", "Xinn"), "tail": ("Xtail",), "latchn": ("Xln", "Xlp"), "latchp": ("Xpn", "Xpp"),
          "reset": ("Xrxp", "Xrxn", "Xrqp", "Xrqn")}


def netlist(design: str) -> str:
    text = circuit_text(get_design(design))
    return unit_array(text, 6) if design in UNIT else text


def devices(design: str):
    lines = netlist(design).splitlines()
    found = []
    for i, line in enumerate(lines):
        m = MOS.match(line)
        if m:
            geo = dict(tok.split("=", 1) for tok in lines[i + 1].split()[1:])
            w = float(eval(geo["w"].strip("{}"), {}, dict(BASELINE_PARAMS)))
            ln = float(eval(geo["l"].strip("{}"), {}, dict(BASELINE_PARAMS)))
            found.append({"name": m.group(1), "nodes": m.group(2, 3, 4, 5), "device": m.group(6), "w": w, "l": ln})
    return found


def key(d, corner, temp) -> str:
    return f"{d['device']}_w{d['w']:g}_l{d['l']:g}_{corner}_{temp:g}C".replace(".", "p").replace("-", "m")


def _includes(device: str, corner: str) -> str:
    stem = f"sky130_fd_pr__{device}"
    return "\n".join(f'.include "{f}"' for f in (
        R3.PDK / "models" / "parameters" / "lod.spice",
        R3.PDK / "cells" / device / f"{stem}__mismatch.corner.spice",
        R3.PDK / "cells" / device / f"{stem}__{corner}.corner.spice"))


def white_psd(d, corner, temp, pts):
    """One-sided white drain-current noise (A^2/Hz) at 10 GHz, source at 0, for (|Vds|, Vgs, Vbs) points."""
    s = -1.0 if d["device"].startswith("pfet") else 1.0
    w = d["w"]
    deck = (f"psd\n.option scale=1u\n{_includes(d['device'], corner)}\n.temp {temp:g}\n"
            f"Vd dd 0 0\nVg g 0 0 ac 1\nVb b 0 0\nVsense dd d 0\n"
            f"X1 d g 0 b sky130_fd_pr__{d['device']} w={w:g} l={d['l']:g}\nHout out 0 Vsense 1\nRout out 0 1\n"
            ".control\nset numdgt=8\nset sqrnoise\n")
    for x, y, z in pts:
        deck += (f"alter Vd {s * x:.6g}\nalter Vg {s * y:.6g}\nalter Vb {s * z:.6g}\n"
                 "noise v(out) Vg lin 1 1e10 1e10\nsetplot noise1\nprint onoise_spectrum\ndestroy all\n")
    deck += "quit 0\n.endc\n.end\n"
    out, _ = R3.ngspice(deck)
    vals = [float(v) for v in re.findall(r"^onoise_spectrum = (\S+)", out, re.M)]
    assert len(vals) == len(pts), (len(vals), len(pts))
    return np.array(vals)


def table(d, corner, temp) -> Path:
    """Write the XSPICE table3D file of ln S_id over signed source-referenced (Vds, Vgs, Vbs)."""
    TAB.mkdir(parents=True, exist_ok=True)
    path = TAB / f"{key(d, corner, temp)}.table"
    if path.exists():
        return path
    pts = [(x, y, z) for z in FULL_Z for y in FULL_Y for x in FULL_X]
    lns = np.log(np.maximum(white_psd(d, corner, temp, pts), FLOOR)).reshape(len(FULL_Z), len(FULL_Y), len(FULL_X))
    lines = ["* r23 ln S_id (A^2/Hz) " + key(d, corner, temp), "*x", str(len(FULL_X)), "*y", str(len(FULL_Y)),
             "*z", str(len(FULL_Z)), "*x row", " ".join(f"{v:g}" for v in FULL_X), "*y column",
             " ".join(f"{v:g}" for v in FULL_Y), "*z tables", " ".join(f"{v:g}" for v in FULL_Z)]
    for k in range(len(FULL_Z)):
        lines.append("*table")
        lines += [" ".join(f"{v:.6g}" for v in row) for row in lns[k]]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def tables(design, corner, vdd, temp):
    seen = {}
    for d in devices(design):
        k = key(d, corner, temp)
        if k not in seen:
            seen[k] = table(d, corner, temp)
    return seen


def pwl(values, dt):
    t0 = NOISE_ON_S
    pairs = ["0 0", f"{t0 - dt:.6e} 0"] + [f"{t0 + i * dt:.6e} {v:.5g}" for i, v in enumerate(values)]
    pairs.append(f"{t0 + len(values) * dt:.6e} 0")
    return "PWL(\n" + "\n".join("+ " + " ".join(pairs[i:i + 8]) for i in range(0, len(pairs), 8)) + ")"


def sequence(name, realization, dt, base_dt=2e-12):
    """Unit-PSD white sequence (variance 1/(2 dt)) for one device. Finer grids refine the base-grid sequence
    by halving: each value c splits into c + s(e1 - e2)/2 and c - s(e1 - e2)/2 with s the new sample std, which
    keeps the block mean and makes the fine samples i.i.d.; so results at different dt are paired."""
    n = int(round((NOISE_OFF_S - NOISE_ON_S) / base_dt))
    seed = zlib.crc32(name.encode())
    xi = np.random.default_rng([realization, seed]).standard_normal(n) / np.sqrt(2 * base_dt)
    step, level = base_dt, 0
    while step > dt * (1 + 1e-9):
        step, level = step / 2, level + 1
        e = np.random.default_rng([realization, seed, level]).standard_normal((len(xi), 2))
        half = (e[:, 0] - e[:, 1]) / 2 / np.sqrt(2 * step)
        xi = np.column_stack((xi + half, xi - half)).ravel()
    assert abs(step - dt) < 1e-18, (step, dt)
    return xi


def noise_text(devs, corner, temp, realization, dt, prune=()):
    """Noise elements inside the atlas subcircuit and table models at top level."""
    inner, models = [], {}
    for d in devs:
        if d["name"] in prune:
            continue
        k = key(d, corner, temp)
        models[k] = f'.model tab_{k} table3d (offset=0.0 gain=1.0 order=2 file="{(TAB / (k + ".table")).as_posix()}")'
        dn, gn, sn, bn = d["nodes"]
        nm = d["name"]
        terms = f"%vd({dn} {sn}) %vd({gn} {sn}) %vd({bn} {sn})"
        if d["device"].startswith("pfet"):
            terms = f"%vd({sn} {dn}) %vd({sn} {gn}) %vd({sn} {bn})"
        xi = sequence(nm, realization, dt)
        inner += [f"aT{nm} {terms} %id(0 ls{nm}) tab_{k}", f"Rls{nm} ls{nm} 0 1",
                  f"Vnz{nm} nz{nm} 0 {pwl(xi * 1e-6, dt)}",
                  f"Bn{nm} {dn} {sn} I = exp(0.5*v(ls{nm}))*v(nz{nm})*1e6"]
    return "\n".join(inner), "\n".join(models.values())


def deck(design, corner, vdd, temp, b0_mv, realization, dt, prune=(), noisy=True, span_mv=SPAN_MV, steps=BISECT,
         probe=False):
    sim = Simulator(HERE / "cache" / "r3_unused", workers=1)
    p = Point(design_name=design, pair_skew=0.0, trim_code=0, differential_v=0.0, corner=corner, vdd_v=vdd,
              temperature_c=temp)
    header = sim._header(p)
    if design in UNIT:
        header = header.replace(circuit_text(get_design(design)), netlist(design))
    if noisy:
        inner, models = noise_text(devices(design), corner, temp, realization, dt, prune)
        header = header.replace(".ends atlas", inner + "\n.ends atlas") + models + "\n"
    cm = 0.5 * vdd
    lo, hi = (b0_mv - span_mv) * 1e-3, (b0_mv + span_mv) * 1e-3
    lines = [header, ".control", "set numdgt=12", f"set lo = {lo:.9e}", f"set hi = {hi:.9e}", f"repeat {steps}",
             "  let mid = ($lo + $hi) / 2", f"  let vp = {cm:.12g} + mid / 2", f"  let vn = {cm:.12g} - mid / 2",
             "  set mids = \"$&mid\"", "  alter Vinp $&vp", "  alter Vinn $&vn",
             f"  tran 10p {NOISE_OFF_S:.4e} 19n 10p",
             f"  meas tran qa find v(qp) at={DEADLINE_S:.6e}", f"  meas tran qb find v(qn) at={DEADLINE_S:.6e}",
             "  let dq = qa - qb", "  echo BIS $mids $&dq"]
    if probe:
        lines.append(f"  print v(xdut.ls{probe}) v(xdut.nz{probe}) > probe.txt")
    lines += ["  if dq > 0", "    set hi = \"$mids\"", "  else", "    set lo = \"$mids\"", "  end",
              "  destroy all", "end", "quit 0", ".endc", ".end"]
    return "\n".join(lines) + "\n"


def bisect(design, corner, vdd, temp, b0_mv, realization, dt, prune=(), noisy=True, span_mv=SPAN_MV, steps=BISECT):
    out, _ = ngspice_long(deck(design, corner, vdd, temp, b0_mv, realization, dt, prune, noisy, span_mv, steps))
    rows = [(float(a), float(b)) for a, b in re.findall(r"^BIS (\S+) (\S+)", out, re.M)]
    assert len(rows) == steps, out[-3000:]
    lo, hi = (b0_mv - span_mv) * 1e-3, (b0_mv + span_mv) * 1e-3
    for mid, dq in rows:
        if dq > 0:
            hi = mid
        else:
            lo = mid
    edge = min(abs(hi * 1e3 - (b0_mv + span_mv)), abs(lo * 1e3 - (b0_mv - span_mv)))
    return (lo + hi) / 2 * 1e3, edge < 1e-6


def validate(dt=0.5e-12, c_ff=10.0, t_ns=60.0, seed=0):
    """kT/C through an on NMOS (to ground) and an on PMOS (to VDD) switch: transient variance vs kT/C,
    plus the table read-back of ln S against direct .noise at the operating point."""
    res = {}
    for dev, w, gate, rail in (("nfet_01v8", 1.0, 1.8, 0.0), ("pfet_01v8", 1.0, 0.0, 1.8)):
        d = {"name": "X1", "device": dev, "w": w, "l": 0.15}
        k = key(d, "tt", 27.0)
        table(d, "tt", 27.0)
        n = int(round(t_ns * 1e-9 / dt))
        xi = np.random.default_rng(seed).standard_normal(n) / np.sqrt(2 * dt)
        src = "c rail" if dev.startswith("nfet") else "rail c"
        terms = "%vd(c rail) %vd(g rail) %vd(rail rail)" if dev.startswith("nfet") else \
            "%vd(rail c) %vd(rail g) %vd(rail rail)"
        body = (f"v\n.option scale=1u reltol=1e-5 abstol=1e-13 vntol=1e-7\n{_includes(dev, 'tt')}\n.temp 27\n"
                f"Vr rail 0 {rail}\nVg g 0 {gate} ac 1\nX1 c g rail rail sky130_fd_pr__{dev} w={w:g} l=0.15\n"
                f"C1 c 0 {c_ff:g}f\naT {terms} %id(0 ls) tab\nRls ls 0 1\n"
                f".model tab table3d (offset=0.0 gain=1.0 order=2 file=\"{(TAB / (k + '.table')).as_posix()}\")\n"
                f"Vnz nz 0 {pwl(xi, dt)}\n"
                f"Bn {src} I = exp(0.5*v(ls))*v(nz)\n.ic v(c)={rail}\n"
                ".control\nset numdgt=10\n"
                f"tran 20p {NOISE_ON_S + t_ns * 1e-9:.4e} 0 {dt:.3e} uic\n"
                f"linearize v(c) v(ls)\nset wr_singlescale\nwrdata vc.tsv v(c) v(ls)\ndestroy all\n"
                "set sqrnoise\nnoise v(c) Vg dec 40 1e3 1e14\nsetplot noise2\nprint onoise_total\nquit 0\n"
                ".endc\n.end\n")
        out, files = R3.ngspice(body)
        arr = np.array([[float(v) for v in ln.split()] for ln in files["vc.tsv"].splitlines() if ln.strip()])
        t, vc, ls = arr[:, 0], arr[:, 1], arr[:, 2]
        sel = t > NOISE_ON_S + 1e-9
        kt_c = K_B * 300.15 / (c_ff * 1e-15)
        ref = float(re.search(r"^onoise_total = (\S+)", out, re.M).group(1))
        direct = white_psd(d, "tt", 27.0, [(0.0, 1.8, 0.0)])[0]
        res[dev] = {"var_v2": float(np.var(vc[sel])), "kT_over_C_v2": kt_c, "ratio": float(np.var(vc[sel]) / kt_c),
                    "dotnoise_total_v2": ref, "ratio_to_dotnoise": float(np.var(vc[sel]) / ref),
                    "rms_mv": float(np.std(vc[sel]) * 1e3), "S_table": float(np.exp(np.median(ls[sel]))),
                    "S_direct_at_vds0": float(direct), "n_samples": int(sel.sum())}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"validate_dt{dt * 1e12:g}ps.json").write_text(json.dumps(res, indent=1))
    return res


def tag(design, corner, vdd, temp, dt, prune=""):
    suffix = {"": "", "prune": "_pruned"}.get(prune, "_" + prune.replace(":", "-"))
    return f"{design}_{corner}_{vdd:g}V_{temp:g}C_dt{dt * 1e12:g}ps{suffix}"


def noiseless(design, corner, vdd, temp):
    path = OUT / f"b0_{design}_{corner}_{vdd:g}V_{temp:g}C.json"
    if path.exists():
        return json.loads(path.read_text())["b0_mv"]
    b0, edge = bisect(design, corner, vdd, temp, 0.0, 0, 1e-12, noisy=False, span_mv=40.0, steps=24)
    assert not edge
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"b0_mv": b0}))
    return b0


def off_devices(design):
    """Trim-branch devices (Xt*/Xs*, incl. unit copies): at code 0 every series switch is off."""
    return sorted(d["name"] for d in devices(design) if re.match(r"^X[ts][pn]\d", d["name"]))


def run(design, corner, vdd, temp, start, n, dt, prune=""):
    tables(design, corner, vdd, temp)
    b0 = noiseless(design, corner, vdd, temp)
    path = OUT / f"run_{tag(design, corner, vdd, temp, dt, prune)}_s{start}.jsonl"
    done = set()
    if path.exists():
        done = {json.loads(ln)["realization"] for ln in path.read_text().splitlines() if ln.strip()}
    pr = ()
    if prune == "prune":
        pr = off_devices(design)
    elif prune.startswith("only:"):
        pr = [d["name"] for d in devices(design) if d["name"] not in GROUPS[prune[5:]]]
    for r in range(start, start + n):
        if r in done:
            continue
        thr, edge = bisect(design, corner, vdd, temp, b0, r, dt, pr)
        with path.open("a", encoding="ascii") as fh:
            fh.write(json.dumps({"realization": r, "threshold_mv": thr, "noise_mv": thr - b0, "edge": edge}) + "\n")


MC = [("lvt_base_3b", "tt_1.8V_27C", "r3/mc_lvt_base_3b_*.jsonl"),
      ("lvt_balanced_4b", "tt_1.8V_27C", "r3/mc_lvt_balanced_4b_*.jsonl"),
      ("lvt_balanced_4b", "ss_1.62V_-40C", "r3/mc_ss1.62V-40C_lvt_balanced_4b_*.jsonl"),
      ("lvt_balanced_4b", "sf_1.95V_125C", "r22/mc_sf1.95V125C_lvt_balanced_4b_*.jsonl"),
      ("unit6_w6", "tt_1.8V_27C", "r16/mc_unit6_tt1.8V27C_*.jsonl"),
      ("u6_w12_l05", "tt_1.8V_27C", "r19/mc_w12_tt1.8V27C_*.jsonl")]


def phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def collect():
    runs = {}
    for path in sorted(OUT.glob("run_*.jsonl")):
        name = path.stem[4:path.stem.rindex("_s")]
        for ln in path.read_text().splitlines():
            if ln.strip():
                r = json.loads(ln)
                runs.setdefault(name, {})[r["realization"]] = r
    return runs


def stats(values):
    a = np.array(values)
    s = float(a.std(ddof=1))
    half = 1.96 / math.sqrt(2 * (len(a) - 1))
    return {"n": len(a), "sigma_mv": s, "ci95_mv": [s * (1 - half), s * (1 + half)], "mean_mv": float(a.mean())}


def report(dt_ps=None):
    runs = collect()
    res = {"validation": {p.stem: json.loads(p.read_text()) for p in sorted(OUT.glob("validate_*.json"))},
           "sigma": {k: stats([r["noise_mv"] for r in v.values()]) | {"edge_hits": sum(r["edge"] for r in v.values())}
                     for k, v in runs.items()}}
    pairs = {}
    for k, v in runs.items():
        if k.endswith("_pruned") and k[:-7] in runs:
            full = runs[k[:-7]]
            d = [v[i]["noise_mv"] - full[i]["noise_mv"] for i in sorted(set(v) & set(full))]
            pairs[k] = {"n": len(d), "max_abs_diff_mv": float(np.max(np.abs(d))),
                        "rms_diff_mv": float(np.sqrt(np.mean(np.square(d))))}
    res["pruning"] = pairs
    groups = {}
    for k, v in runs.items():
        if "_only-" in k:
            base, g = k.split("_only-")
            groups.setdefault(base, {})[g] = stats([r["noise_mv"] for r in v.values()])
    for base, g in groups.items():
        full = res["sigma"].get(base) or res["sigma"].get(base + "_pruned")
        g["sum_of_variances_mv2"] = float(sum(x["sigma_mv"] ** 2 for x in g.values()))
        g["total_variance_mv2"] = full["sigma_mv"] ** 2 if full else None
        tot = runs.get(base + "_pruned") or runs.get(base)
        parts = [runs[f"{base}_only-{n}"] for n in GROUPS]
        common = sorted(set(tot).intersection(*parts)) if tot and len(parts) == len(GROUPS) else []
        if common:
            d = [tot[i]["noise_mv"] - sum(p[i]["noise_mv"] for p in parts) for i in common]
            g["superposition"] = {"n": len(common), "rms_total_minus_sum_mv": float(np.sqrt(np.mean(np.square(d)))),
                                  "rms_total_mv": float(np.sqrt(np.mean([tot[i]["noise_mv"] ** 2 for i in common])))}
    res["groups"] = groups
    errs = {}
    for design, cond, pattern in MC:
        cands = [k for k in res["sigma"] if k.startswith(f"{design}_{cond}_dt") and "only" not in k
                 and (dt_ps is None or f"_dt{dt_ps:g}ps" in k)]
        if not cands:
            continue
        best = min(cands, key=lambda k: float(re.search(r"_dt([0-9.]+)ps", k).group(1)) * 1e6 - res["sigma"][k]["n"])
        sn = res["sigma"][best]["sigma_mv"]
        ms = [json.loads(ln) for p in sorted((HERE / "out").glob(pattern)) for ln in p.read_text().splitlines() if ln]
        m = np.array([abs(r["m_mv"]) for r in ms if r["covered"]])
        n_all = len(ms)
        p_err = np.array([phi(-(1.0 - x) / sn) for x in m])
        need = m + 4.753 * sn
        errs[f"{design}_{cond}"] = {
            "sigma_from": best, "sigma_n_mv": sn, "mc_samples": n_all, "covered": int(len(m)),
            "mean_p_err_at_1mV": float(p_err.mean()), "median_p_err_at_1mV": float(np.median(p_err)),
            "share_p_err_above_1e-3": float(np.mean(p_err > 1e-3)),
            "share_p_err_above_1e-6": float(np.mean(p_err > 1e-6)),
            "noiseless_share_within_1mV": float(np.mean(m < 1.0)),
            "share_within_1mV_at_1e-6": float(np.mean(need < 1.0)),
            "input_for_1e-6_p50_p90_mv": [float(np.percentile(need, 50)), float(np.percentile(need, 90))]}
    res["error_rate"] = errs
    (OUT / "r23_report.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    cmd = ARGS[0]
    if cmd == "tables":
        print(json.dumps({k: str(v) for k, v in tables(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4])).items()},
                         indent=1))
    elif cmd == "validate":
        print(json.dumps(validate(float(ARGS[1]) * 1e-12 if len(ARGS) > 1 else 2e-12), indent=1))
    elif cmd == "run":
        run(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4]), int(ARGS[5]), int(ARGS[6]),
            float(ARGS[7]) * 1e-12 if len(ARGS) > 7 else 2e-12, ARGS[8] if len(ARGS) > 8 else "")
    elif cmd == "report":
        print(json.dumps(report(float(ARGS[1]) if len(ARGS) > 1 else None), indent=1))
