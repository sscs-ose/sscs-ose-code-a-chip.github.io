"""r24: impulse sensitivity function (ISF) of the comparator decision, and noise predicted from it.

r23 found the decision linear in the device noise (group shifts add to the all-on shift within 0.016 mV),
so the input-referred noise is sigma_n^2 = sum_k int (h_s(k) - h_d(k))^2 S_k(t) / 2 dt, with h_n(tau) the
shift of the switching input per unit charge injected into node n at time tau and S_k(t) the one-sided
white drain-noise PSD of device k along the noiseless trajectory at the switching input.
h_n(tau) is measured directly: a 2 ps triangular charge pulse of +q and -q into node n at time tau and the
switching input bisected for each (same deck, same breakpoints), h = (b+ - b-) / 2q.
  python -B r24_isf.py isf <design> <corner> <vdd> <temp> [fast]     # h on the tau grid (fast: xp, qp)
  python -B r24_isf.py traj <design> <corner> <vdd> <temp>           # S_k(t) at the switching input
  python -B r24_isf.py predict <design> <corner> <vdd> <temp>        # sigma_n from h and S
  python -B r24_isf.py atlas <design>                                # sigma_n at the 45 PVT conditions
  python -B r24_isf.py mc <design> <corner> <vdd> <temp> [n]         # r23 noise MC on the same deck
  python -B r24_isf.py memory [strip|swap]                           # decision memory vs the prior input
  python -B r24_isf.py trimsteps                                     # trim LSB/MSB, original vs swapped
Set R24_PRIOR_MV (e.g. -5) to pin the two earlier clock cycles to a fixed input (outputs under out/r24/prior<mv>).
Set R24_CM_V (e.g. 0.7) to move the input common mode from VDD/2 (outputs under .../cm<CM>).
"""
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r23_noise as N  # noqa: E402
from r23_noise import HERE, R3  # noqa: E402

OUT = HERE / "out" / "r24"


def pin_prior(h, prior_mv):
    """Series PWL sources hold a fixed differential prior_mv on the inputs until the last reset (19-19.5 ns)."""
    s = prior_mv * 0.5e-3
    for name, node, sign in (("Vinp", "vinp", 1), ("Vinn", "vinn", -1)):
        old = re.search(rf"^{name} {node} 0 (\S+)$", h, re.M)
        assert old, name
        h = h.replace(old.group(0), f"{name} {node}a 0 {old.group(1)}\n"
                      f"Vh{node} {node} {node}a PWL(0 {sign * s:.6e} 19n {sign * s:.6e} 19.5n 0)")
    return h


PRIOR = os.environ.get("R24_PRIOR_MV")
if PRIOR is not None:
    # Pinned prior state: the two earlier clock cycles see a fixed differential PRIOR mV, so their decisions
    # no longer follow the bisected input (see memory()).
    OUT = OUT / f"prior{float(PRIOR):g}"
    N.OUT = OUT / "r23"
    _plain_header = N.Simulator._header
    N.Simulator._header = lambda self, p: pin_prior(_plain_header(self, p), float(PRIOR))


def shift_cm(h, dv):
    """Series DC sources move both inputs by dv; every 'alter Vinp/Vinn' (cm = VDD/2 +- mid/2) still applies."""
    for name, node in (("Vinp", "vinp"), ("Vinn", "vinn")):
        old = re.search(rf"^{name} (\S+) 0 (\S+)$", h, re.M)
        assert old, name
        h = h.replace(old.group(0), f"{name} {old.group(1)}c 0 {old.group(2)}\n"
                      f"Vcm{node} {old.group(1)} {old.group(1)}c {dv:.9g}")
    return h


CM = os.environ.get("R24_CM_V")
if CM is not None:
    # Input common mode CM volts instead of VDD/2 (outputs under .../cm<CM>).
    OUT = OUT / f"cm{float(CM):g}"
    N.OUT = OUT / "r23"
    _cm_header = N.Simulator._header
    N.Simulator._header = lambda self, p: shift_cm(_cm_header(self, p), float(CM) - 0.5 * p.vdd_v)
NODES = ("xp", "xn", "tail", "qp", "qn")
RAILS = {"vdd", "vss", "0"}
Q = 20e-18
RISE = 1e-12
TMAX = 10e-12
STEPS = 14
SPAN_MV = 2.0
EDGE_S = 22.025e-9


def grid(name="default"):
    if name == "default":
        parts = [np.arange(21.70, 22.30, 0.010), np.arange(22.30, 23.00, 0.025), np.arange(23.0, 25.51, 0.1)]
    elif name == "scout":
        parts = [np.arange(21.70, 22.30, 0.020), np.arange(22.30, 23.00, 0.050), np.arange(23.0, 25.51, 0.2)]
    else:
        raise ValueError(name)
    return [round(float(t), 4) for t in np.concatenate(parts)]


def _header(design, corner, vdd, temp):
    sim = N.Simulator(HERE / "cache" / "r3_unused", workers=1)
    p = N.Point(design_name=design, pair_skew=0.0, trim_code=0, differential_v=0.0, corner=corner, vdd_v=vdd,
                temperature_c=temp)
    header = sim._header(p)
    if design in N.UNIT:
        header = header.replace(N.circuit_text(N.get_design(design)), N.netlist(design))
    return header


def _bisect_block(label, cm, b0_mv, span_mv, steps):
    lo, hi = (b0_mv - span_mv) * 1e-3, (b0_mv + span_mv) * 1e-3
    return [f"set lo = {lo:.12e}", f"set hi = {hi:.12e}", f"repeat {steps}",
            "  let mid = ($lo + $hi) / 2", f"  let vp = {cm:.12g} + mid / 2", f"  let vn = {cm:.12g} - mid / 2",
            "  set mids = \"$&mid\"", "  alter Vinp $&vp", "  alter Vinn $&vn",
            f"  tran 10p {N.NOISE_OFF_S:.4e} 19n {TMAX:.3e}",
            f"  meas tran qa find v(qp) at={N.DEADLINE_S:.6e}", f"  meas tran qb find v(qn) at={N.DEADLINE_S:.6e}",
            "  let dq = qa - qb", f"  echo ISF {label} $mids $&dq",
            "  if dq > 0", "    set hi = \"$mids\"", "  else", "    set lo = \"$mids\"", "  end",
            "  destroy all", "end"]


def isf_deck(design, corner, vdd, temp, b0_mv, tau_ns, q=Q, span_mv=SPAN_MV, steps=STEPS, nodes=NODES, ref=True):
    header = _header(design, corner, vdd, temp)
    sels = " ".join(f"injsel{n}" for n in nodes)
    inner = "\n".join(f"Binj{n} 0 {n} I = {q / RISE:.6e}*v(injpls)*v(injsel{n})" for n in nodes)
    header = header.replace(".subckt atlas", f".global injpls {sels}\n.subckt atlas", 1)
    header = header.replace(".ends atlas", inner + "\n.ends atlas")
    tau = tau_ns * 1e-9
    top = [f"Vinjpls injpls 0 PULSE(0 1 {tau - RISE:.6e} {RISE:.3e} {RISE:.3e} 0 1)"]
    top += [f"Vinjsel{n} injsel{n} 0 0" for n in nodes]
    lines = [header] + top + [".control", "set numdgt=12"]
    if ref:
        lines += _bisect_block("ref 0", 0.5 * vdd, b0_mv, span_mv, steps)
    for n in nodes:
        for sign in (1, -1):
            lines.append(f"alter Vinjsel{n} {sign}")
            lines += _bisect_block(f"{n} {sign}", 0.5 * vdd, b0_mv, span_mv, steps)
        lines.append(f"alter Vinjsel{n} 0")
    lines += ["quit 0", ".endc", ".end"]
    return "\n".join(lines) + "\n"


def _resolve(rows, b0_mv, span_mv):
    lo, hi = (b0_mv - span_mv) * 1e-3, (b0_mv + span_mv) * 1e-3
    for mid, dq in rows:
        if dq > 0:
            hi = mid
        else:
            lo = mid
    edge = min(abs(hi * 1e3 - (b0_mv + span_mv)), abs(lo * 1e3 - (b0_mv - span_mv))) < 1e-6
    return (lo + hi) / 2 * 1e3, edge


def isf_point(args):
    design, corner, vdd, temp, b0_mv, tau_ns, q, span_mv, steps, nodes = args
    out, _ = N.ngspice_long(isf_deck(design, corner, vdd, temp, b0_mv, tau_ns, q, span_mv, steps, nodes,
                                     ref=len(nodes) == len(NODES)))
    rows = {}
    for label, sign, mid, dq in re.findall(r"^ISF (\S+) (\S+) (\S+) (\S+)", out, re.M):
        rows.setdefault((label, int(sign)), []).append((float(mid), float(dq)))
    res = {"tau_ns": tau_ns, "q": q}
    for (label, sign), r in rows.items():
        assert len(r) == steps, (label, sign, len(r))
        res[f"{label}{'+' if sign > 0 else '-' if sign < 0 else ''}"] = _resolve(r, b0_mv, span_mv)
    return res


def tag(design, corner, vdd, temp):
    return f"{design}_{corner}_{vdd:g}V_{temp:g}C"


def b0_of(design, corner, vdd, temp):
    return N.noiseless(design, corner, vdd, temp)


FAST = {"nodes": ("xp", "qp"), "steps": 12, "grid": "scout"}


def isf_path(design, corner, vdd, temp, fast=False, q=Q):
    qs = "" if q == Q else f"_q{q * 1e18:g}a"
    return OUT / f"isf_{tag(design, corner, vdd, temp)}{'_fast' if fast else ''}{qs}.jsonl"


def isf(design, corner, vdd, temp, name="default", workers=12, q=Q, fast=False):
    """Full mode: all five nodes and a q = 0 reference. Fast mode: xp and qp only (xn = -xp, qn = -qp and
    tail = 0 by the symmetry of the trim-code-0, zero-skew circuit; checked on the full-mode runs)."""
    OUT.mkdir(parents=True, exist_ok=True)
    b0 = b0_of(design, corner, vdd, temp)
    path = isf_path(design, corner, vdd, temp, fast, q)
    nodes, steps = (FAST["nodes"], FAST["steps"]) if fast else (NODES, STEPS)
    name = FAST["grid"] if fast else name
    done = set()
    if path.exists():
        done = {json.loads(ln)["tau_ns"] for ln in path.read_text().splitlines() if ln.strip()}
    todo = [t for t in grid(name) if t not in done]
    t0 = time.time()
    for _ in range(1 + REFINE):
        jobs = [(design, corner, vdd, temp, b0, t, q, SPAN_MV, steps, nodes) for t in todo]
        with ProcessPoolExecutor(workers) as ex, path.open("a") as f:
            for i, res in enumerate(ex.map(isf_point, jobs)):
                f.write(json.dumps(res) + "\n")
                f.flush()
                print(f"{i + 1}/{len(jobs)} tau {res['tau_ns']} {time.time() - t0:.0f}s", flush=True)
        todo = midpoints(*load_isf(design, corner, vdd, temp, q, fast)[:2])
        if not todo:
            break
    return path


REFINE = 2
MIN_GAP_NS = 0.005


def midpoints(tau, h, frac=0.02):
    """Interval midpoints where |h| (any node) exceeds frac of its peak at either end, down to 5 ps spacing."""
    mag = np.max([np.abs(v) / max(np.max(np.abs(v)), 1e-30) for v in h.values()], axis=0)
    t = tau * 1e9
    out = []
    for i in range(len(t) - 1):
        if max(mag[i], mag[i + 1]) > frac and t[i + 1] - t[i] > 2 * MIN_GAP_NS - 1e-9:
            out.append(round(float((t[i] + t[i + 1]) / 2), 4))
    return out


def load_isf(design, corner, vdd, temp, q=Q, fast=None, subset=None):
    """h_n(tau) in V/C. fast=None uses the full-mode file if present; subset keeps only those tau (ns)."""
    path = isf_path(design, corner, vdd, temp, False, q)
    if fast or (fast is None and not path.exists()):
        path = isf_path(design, corner, vdd, temp, True, q)
    rows = sorted((json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()), key=lambda r: r["tau_ns"])
    if subset is not None:
        keep = {round(t, 4) for t in subset}
        rows = [r for r in rows if round(r["tau_ns"], 4) in keep]
    tau = np.array([r["tau_ns"] for r in rows]) * 1e-9
    h = {n: np.array([(r[n + "+"][0] - r[n + "-"][0]) * 1e-3 / (2 * r["q"]) for r in rows])
         for n in NODES if n + "+" in rows[0]}
    if "xn" not in h:
        h["xn"], h["qn"], h["tail"] = -h["xp"], -h["qp"], np.zeros_like(h["xp"])
    sym = {n: np.array([(r[n + "+"][0] + r[n + "-"][0]) / 2 - r["ref"][0] for r in rows])
           for n in NODES if "ref" in rows[0] and n + "+" in rows[0]}
    edge = sum(r[k][1] for r in rows for k in r if isinstance(r[k], list))
    return tau, h, sym, edge


def noisy_devices(design):
    """Devices noisy in the r23 'prune' runs: every device except the off trim branches."""
    off = set(N.off_devices(design))
    return [d for d in N.devices(design) if d["name"] not in off]


TRAJ_DT = 0.5e-12


def traj(design, corner, vdd, temp):
    """ln S_k(t) of every noisy device along the noiseless trajectory at the switching input, read through
    the same r23 table3d models (so S is exactly the r23 noise model), on a uniform 0.5 ps grid."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"traj_{tag(design, corner, vdd, temp)}.npz"
    if path.exists():
        return path
    N.tables(design, corner, vdd, temp)
    b0 = b0_of(design, corner, vdd, temp)
    devs = noisy_devices(design)
    header = _header(design, corner, vdd, temp)
    inner, models = [], {}
    for d in devs:
        k = N.key(d, corner, temp)
        models[k] = (f'.model tab_{k} table3d (offset=0.0 gain=1.0 order=2 '
                     f'file="{(N.TAB / (k + ".table")).as_posix()}")')
        dn, gn, sn, bn = d["nodes"]
        terms = f"%vd({dn} {sn}) %vd({gn} {sn}) %vd({bn} {sn})"
        if d["device"].startswith("pfet"):
            terms = f"%vd({sn} {dn}) %vd({sn} {gn}) %vd({sn} {bn})"
        inner += [f"aT{d['name']} {terms} %id(0 ls{d['name']}) tab_{k}", f"Rls{d['name']} ls{d['name']} 0 1"]
    header = header.replace(".ends atlas", "\n".join(inner) + "\n.ends atlas") + "\n".join(models.values()) + "\n"
    vecs = [f"v(xdut.ls{d['name']})" for d in devs] + ["v(qp)", "v(qn)", "v(xdut.xp)", "v(xdut.xn)", "v(xdut.tail)"]
    header += ".save " + " ".join(vecs) + "\n"
    cm, b = 0.5 * vdd, b0 * 1e-3
    lines = [header, ".control", "set numdgt=12", f"alter Vinp {cm + b / 2:.12g}", f"alter Vinn {cm - b / 2:.12g}",
             f"tran {TRAJ_DT:.3e} {N.DEADLINE_S:.6e} 19n {TRAJ_DT:.3e}", "linearize " + " ".join(vecs),
             "set wr_singlescale", "wrdata traj.tsv " + " ".join(vecs), "quit 0", ".endc", ".end"]
    out, files = R3.ngspice("\n".join(lines) + "\n")
    arr = np.array([[float(v) for v in ln.split()] for ln in files["traj.tsv"].splitlines() if ln.strip()])
    np.savez_compressed(path, t=arr[:, 0], lnS=arr[:, 1:1 + len(devs)].T, v=arr[:, 1 + len(devs):].T,
                        names=np.array([d["name"] for d in devs]))
    return path


def load_traj(design, corner, vdd, temp):
    z = np.load(traj(design, corner, vdd, temp))
    return z["t"], dict(zip([str(n) for n in z["names"]], z["lnS"])), z["v"]


def gains(design, corner, vdd, temp, t, **kw):
    """g_k(t) = h_source - h_drain (V/C): input-referred shift per charge of device k's drain-source current."""
    tau, h, _, _ = load_isf(design, corner, vdd, temp, **kw)
    hn = {n: np.interp(t, tau, h[n], left=0.0, right=0.0) for n in NODES}
    out = {}
    for d in noisy_devices(design):
        dn, _, sn, _ = d["nodes"]
        missing = {dn, sn} - RAILS - set(NODES)
        assert not missing, (d["name"], missing)
        out[d["name"]] = hn.get(sn, 0.0) - hn.get(dn, 0.0)
    return out


def predict(design, corner, vdd, temp, **kw):
    t, lns, _ = load_traj(design, corner, vdd, temp)
    sel = t >= N.NOISE_ON_S
    t = t[sel]
    g = gains(design, corner, vdd, temp, t, **kw)
    var = {k: float(np.trapezoid(g[k] ** 2 * np.exp(lns[k][sel]) / 2, t)) for k in g}
    by_group = {grp: sum(var.get(n, 0.0) for n in names) for grp, names in N.GROUPS.items()}
    total = sum(var.values())
    return {"sigma_mv": float(np.sqrt(total) * 1e3), "var_v2": var,
            "group_sigma_mv": {k: float(np.sqrt(v) * 1e3) for k, v in by_group.items()},
            "group_share": {k: v / total for k, v in by_group.items()}}


def realization_shift(design, corner, vdd, temp, realization, dt=2e-12, only=None, **kw):
    """Predicted r23 shift (mV) of one noise realization: sum_k int g_k sqrt(S_k) xi_k dt on the 0.5 ps grid."""
    t, lns, _ = load_traj(design, corner, vdd, temp)
    sel = t >= N.NOISE_ON_S
    t = t[sel]
    g = gains(design, corner, vdd, temp, t, **kw)
    total = 0.0
    for name, gk in g.items():
        if only and name not in only:
            continue
        xi = N.sequence(name, realization, dt)
        tx = N.NOISE_ON_S + np.arange(len(xi)) * dt
        x = np.interp(t, tx, xi, left=0.0, right=0.0)
        total += float(np.trapezoid(gk * np.exp(0.5 * lns[name][sel]) * x, t))
    return total * 1e3


def timing(design, corner, vdd, temp, **kw):
    """When sigma_n^2 accumulates (t10/t50/t90 of the cumulative variance, ps from the clock edge; pre-edge
    share) and how long integration lasts on the noiseless trajectory (x common mode to VDD/2; |qp-qn| to
    100 mV), both in ps from the edge."""
    t, lns, v = load_traj(design, corner, vdd, temp)
    sel = t >= N.NOISE_ON_S
    t, v = t[sel], v[:, sel]
    g = gains(design, corner, vdd, temp, t, **kw)
    rate = sum(g[k] ** 2 * np.exp(lns[k][sel]) / 2 for k in g)
    cum = np.concatenate([[0.0], np.cumsum(np.diff(t) * (rate[1:] + rate[:-1]) / 2)])
    cum /= cum[-1]
    ps = (lambda x: round(float((x - EDGE_S) * 1e12), 1))
    after = t > EDGE_S
    xcm = (v[2] + v[3]) / 2
    dq = np.abs(v[0] - v[1])
    return {"t10_ps": ps(np.interp(0.1, cum, t)), "t50_ps": ps(np.interp(0.5, cum, t)),
            "t90_ps": ps(np.interp(0.9, cum, t)), "pre_edge_share": float(np.interp(EDGE_S, t, cum)),
            "x_half_ps": ps(t[after][np.argmax(xcm[after] < vdd / 2)]),
            "dq100_ps": ps(t[after][np.argmax(dq[after] > 0.1)]) if np.any(dq[after] > 0.1) else None}


def strip_devices(h, names):
    """Delete the instance lines (and their + continuations) of the given devices."""
    keep, drop = [], False
    for ln in h.splitlines():
        if not ln.startswith("+"):
            drop = bool(ln.split()) and ln.split()[0] in names
        if not drop:
            keep.append(ln)
    return "\n".join(keep)


def swap_trim(h):
    """Swapped trim branch: series switch on the x side, trim device source on the tail (no floating node)."""
    h, n1 = re.subn(r"^(Xt[pn]\d+(?:u\d+)?) (x[pn]) (vin[pn]) (s[pn]\d+) vss", r"\1 \4 \3 tail vss", h, flags=re.M)
    h, n2 = re.subn(r"^(Xs([pn])\d+(?:u\d+)?) (s[pn]\d+) (t[pn]\d+) tail vss", r"\1 x\2 \4 \3 vss", h, flags=re.M)
    assert n1 and n2, (n1, n2)
    return h


def _variant(h, design, variant):
    if variant == "strip":
        return strip_devices(h, set(N.off_devices(design)))
    if variant == "swap":
        return swap_trim(h)
    assert variant is None, variant
    return h


def _threshold(args):
    """Noiseless switching input (mV) with the earlier cycles pinned to prior_mv and the given trim pins on."""
    design, corner, vdd, temp, prior_mv, variant, pins, span_mv, steps = args
    h = _variant(_header(design, corner, vdd, temp), design, variant)
    lines = [pin_prior(h, prior_mv), ".control", "set numdgt=12"] + [f"alter {p} {vdd:g}" for p in pins]
    lines += _bisect_block("thr 0", 0.5 * vdd, 0.0, span_mv, steps) + ["quit 0", ".endc", ".end"]
    out, _ = N.ngspice_long("\n".join(lines) + "\n")
    rows = [(float(m), float(d)) for _, _, m, d in re.findall(r"^ISF (\S+) (\S+) (\S+) (\S+)", out, re.M)]
    b, edge = _resolve(rows, 0.0, span_mv)
    assert not edge, args
    return b


def memory(designs=("baseline", "lvt_balanced_4b", "unit6_w6", "u6_w12_l05"), corner="tt", vdd=1.8, temp=27.0,
           priors=(-1.0, 1.0, -5.0, 5.0), workers=12, variant=None):
    """Decision memory: noiseless switching input of the last cycle when both earlier cycles see a fixed
    differential prior; fit thr = a * sign(prior) + c * prior (a: decision memory, c: input carry-over).
    variant 'strip' deletes the off trim branches (Xt*/Xs*), 'swap' puts their switches on the x side."""
    assert PRIOR is None, "run memory without R24_PRIOR_MV"
    jobs = [(d, corner, vdd, temp, p, variant, (), 0.5, 16) for d in designs for p in priors]
    thr = {}
    with ProcessPoolExecutor(workers) as ex:
        for job, b in zip(jobs, ex.map(_threshold, jobs)):
            thr.setdefault(job[0], {})[f"{job[4]:g}"] = b
    fit = {}
    for d, v in thr.items():
        c = (v["5"] - v["1"]) / 4.0
        fit[d] = {"decision_uv": (v["1"] - c) * 1e3, "input_carry": c}
    res = {"condition": [corner, vdd, temp], "variant": variant, "threshold_mv": thr, "fit": fit}
    cond = tag(designs[0], corner, vdd, temp)[len(designs[0]) + 1:]
    (OUT / f"memory_{cond}{'_' + variant if variant else ''}.json").write_text(json.dumps(res, indent=1))
    return res


def trim_steps(designs=(("lvt_balanced_4b", "Vtp3"), ("unit6_w6", "Vtp5")), corner="tt", vdd=1.8, temp=27.0,
               workers=12):
    """Threshold at code 0, LSB (Vtp0) and MSB on, original vs swapped trim branches (prior pinned at -5 mV)."""
    jobs = [(d, corner, vdd, temp, -5.0, v, pins, 60.0, 22) for d, msb in designs for v in (None, "swap")
            for pins in ((), ("Vtp0",), (msb,))]
    res = {}
    with ProcessPoolExecutor(workers) as ex:
        for job, b in zip(jobs, ex.map(_threshold, jobs)):
            res.setdefault(job[0], {}).setdefault(job[5] or "original", {})["+".join(job[6]) or "code0"] = b
    (OUT / "trim_steps_swap.json").write_text(json.dumps(res, indent=1))
    return res


def conditions():
    """The 45 PVT conditions of the sealed atlas."""
    from comparator_atlas.experiments import cases
    conds = sorted({(p.corner, p.vdd_v, p.temperature_c) for p in cases("full")})
    assert len(conds) == 45, len(conds)
    return conds


def atlas(design):
    """sigma_n at every PVT condition (fast mode with refinement); appends to atlas_<design>.jsonl."""
    path = OUT / f"atlas_{design}.jsonl"
    done = set()
    if path.exists():
        done = {tuple(json.loads(ln)["condition"]) for ln in path.read_text().splitlines() if ln.strip()}
    for corner, vdd, temp in conditions():
        if (corner, vdd, temp) in done:
            continue
        t0 = time.time()
        N.tables(design, corner, vdd, temp)
        isf(design, corner, vdd, temp, fast=True)
        traj(design, corner, vdd, temp)
        p = predict(design, corner, vdd, temp, fast=True)
        row = {"condition": [corner, vdd, temp], "b0_mv": b0_of(design, corner, vdd, temp),
               "sigma_mv": p["sigma_mv"], "group_sigma_mv": p["group_sigma_mv"],
               **timing(design, corner, vdd, temp, fast=True),
               "edge": load_isf(design, corner, vdd, temp, fast=True)[3], "seconds": round(time.time() - t0)}
        with path.open("a") as f:
            f.write(json.dumps(row) + "\n")
        print("ATLAS", json.dumps(row), flush=True)


def _mc_one(args):
    design, corner, vdd, temp, b0, r, prune = args
    thr, edge = N.bisect(design, corner, vdd, temp, b0, r, 2e-12, prune)
    return {"realization": r, "threshold_mv": thr, "noise_mv": thr - b0, "edge": edge}


def mc(design, corner, vdd, temp, n=40, workers=12):
    """r23 transient-noise MC (2 ps, off trim branches pruned) in parallel; under R24_PRIOR_MV this is the
    pinned-prior deck, so ISF and MC are compared on the same circuit."""
    N.OUT.mkdir(parents=True, exist_ok=True)
    N.tables(design, corner, vdd, temp)
    b0 = b0_of(design, corner, vdd, temp)
    path = N.OUT / f"run_{N.tag(design, corner, vdd, temp, 2e-12, 'prune')}_s0.jsonl"
    done = set()
    if path.exists():
        done = {json.loads(ln)["realization"] for ln in path.read_text().splitlines() if ln.strip()}
    jobs = [(design, corner, vdd, temp, b0, r, tuple(N.off_devices(design))) for r in range(n) if r not in done]
    with ProcessPoolExecutor(workers) as ex, path.open("a", encoding="ascii") as f:
        for row in ex.map(_mc_one, jobs):
            f.write(json.dumps(row) + "\n")
            f.flush()
    return path


if __name__ == "__main__":
    cmd = ARGS[0]
    if cmd == "mc":
        mc(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4]), int(ARGS[5]) if len(ARGS) > 5 else 40)
    elif cmd == "memory":
        print(json.dumps(memory(variant=(ARGS[1:] or [None])[0] or None)["fit"], indent=1))
    elif cmd == "trimsteps":
        print(json.dumps(trim_steps(), indent=1))
    elif cmd == "isf":
        d, c, v, t = ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4])
        isf(d, c, v, t, fast=len(ARGS) > 5 and ARGS[5] == "fast")
    elif cmd == "atlas":
        atlas(ARGS[1])
    elif cmd == "traj":
        print(traj(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4])))
    elif cmd == "predict":
        print(json.dumps(predict(ARGS[1], ARGS[2], float(ARGS[3]), float(ARGS[4])), indent=1))
    else:
        raise SystemExit(__doc__)
