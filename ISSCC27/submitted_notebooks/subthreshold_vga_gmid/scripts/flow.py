"""
flow.py - the sizing flow as one call:  spec + topology + design space  ->  SPICE-verified design.

    res = run_flow(Spec(), "12T")

Stages (each one is a function below, and each one's output is cached and shown in the notebook):
  1. screen   - every point of the design space is evaluated by the LUT model (evaluator.evaluate_gate): gain at
                each control step, bandwidth window, monotonicity, range, supply current, headroom, noise.
                No SPICE. ~0.1 s per design.
  2. filter   - LUT-feasible designs: every spec limit met at tt with the LUT screening margins.
  3. corner   - the tt-feasible designs are re-evaluated on the corner tables and at V_DD +/- 10 %.
  4. extend   - wherever the noise-current front touches the edge of the grid, the grid is extended along that axis
                (one step beyond it) and the new designs are screened; repeated until no front design has an
                unexplored neighbour. Each axis stops only at a model or practicality limit (EXTEND).
  5. front    - Pareto front of the corner-feasible set over (noise, supply current).
  6. verify   - front designs, spread evenly in current, are simulated in SPICE at all seven corners (spice_gate),
                checked against the same spec, with the SPICE headroom margin.
  7. pick     - the lowest SPICE-measured noise among designs that pass at every corner (ties: headroom, current).
  8. audit    - every single-axis neighbour of the pick is evaluated: each one either violates a named limit at a
                named corner, or has more noise, or lies beyond a model limit - so the pick is not an edge artefact.
Nothing in the flow is specific to one specification: the generalisation run in the notebook calls run_flow
with a different Spec and the same code.
SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations
import math, json, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
import numpy as np, pandas as pd
import warnings
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)   # fragmented-frame notices, not results
import os
import vga_flow as vf, evaluator as ev

# The gate's corners. Process at nominal temperature and supply; temperature and supply one at a time (tt); and, for
# every process corner, the three combined extremes that bound the limits: cold and low supply (headroom), hot and low
# supply (bandwidth), hot and high supply (supply current).
CORNERS = (("tt", 27), ("ss", 27), ("ff", 27), ("sf", 27), ("fs", 27), ("tt", -20), ("tt", 85))
COMBOS = tuple((c, t, v) for c in ("tt", "ss", "ff", "sf", "fs") for t, v in ((-20, 1.62), (85, 1.62), (85, 1.98)))
AREA_TIE = 0.05                                                # gate areas this close are treated as equal
GATE_DEVS = ("m2", "m5", "m6", "m9")
NOISE_TIE = 0.02                                               # 2 %: designs this close in noise are treated as equal
FINE = tuple(np.round(np.arange(0.3, -0.3001, -0.05), 3))     # SPICE gain grid, max gain first


@dataclass
class Spec:
    name: str = "Table 2 (hearing-aid gain core)"
    CL: float = 1e-12                 # F, load on v_out for every bandwidth figure
    range_min_db: float = 30.0        # monotonic control range inside the bandwidth window, from +0.3 V down
    bw_min_hz: float = 10e3           # f_-3dB at every sampled gain step in the window
    i_tot_max: float = 5e-6           # total supply current, reference branch included
    mm_k: float = 3.0                 # the current limit holds with this many sigma of local bias mismatch (99.87 %)
    vds_min_v: float = 0.130          # weak-inversion saturation limit (specification)
    vds_margin_v: float = 0.020       # flow margin on top of it in SPICE  -> 150 mV
    lut_vds_extra_v: float = 0.010    # extra LUT screening margin (LUT vs SPICE headroom error, section 6)
    lut_bw_factor: float = 1.12       # LUT bandwidth margin: covers the evaluator's worst bandwidth error (Table 9b)
    noise_max_vrms: float = 29.1e-6   # adoption gate: the 9T hand-sized baseline at maximum gain
    noise_target_vrms: float = 7e-6   # graded noise targets (Table 2); the pick rule prefers designs meeting more of them
    vn1k_target: float = 50e-9
    nef_target: float = 5.0
    band: tuple = (20.0, 20e3)
    corners: tuple = CORNERS
    supplies: tuple = (1.62, 1.98)    # V_DD +/- 10 % (tt, 27 C), gated like the process/temperature corners
    combos: tuple = COMBOS            # combined process/temperature/supply extremes
    max_spice: int = 30               # front designs carried into SPICE (evenly spread in power if more)
    extend: bool = True               # grow the grid where the best designs touch its edge (stage 4)
    ext_seeds: int = 12               # the lowest-noise feasible designs whose neighbours are explored each round
    ext_tol: float = 0.005            # stop when two rounds together improve the best noise by less than 0.5 %
    ext_max_iter: int = 60
    c_wire: float = 0.0               # F, output wiring capacitance measured on an extracted layout: added to C_L in
                                      #   every SPICE bandwidth figure; the LUT bandwidth limit scales by (C_L + c_wire)/C_L

    @property
    def lut_bw_hz(self):
        """Bandwidth the LUT screen requires: the spec with the LUT margin, scaled for the measured output wiring."""
        return self.lut_bw_factor * self.bw_min_hz * (self.CL + self.c_wire) / self.CL

    def _lim(self, df, pre=""):
        g = lambda k: df[pre + k] if (pre + k) in df else pd.Series(0.0, index=df.index)
        return (g("monotonic").astype(bool) & (g("range_db") >= self.range_min_db)
                & (g("bw_min") >= self.lut_bw_hz) & (self.i_eff(g("i_tot"), g("i_sig")) <= self.i_tot_max)
                & (g("vds_min") >= self.vds_min_v + self.vds_margin_v + self.lut_vds_extra_v))

    def i_eff(self, i_tot, i_sig):
        """Supply current the limit is checked against: nominal plus mm_k sigma of local mismatch."""
        if hasattr(i_sig, "fillna"):
            i_sig = i_sig.fillna(0.0)
        return i_tot * (1 + self.mm_k * i_sig)

    def lut_feasible(self, df):
        """tt screen: every limit with the LUT margins, plus the noise gate and weak inversion of the input pair."""
        return df["ok"] & self._lim(df) & (df["vrms"] <= self.noise_max_vrms) & (df["vov_in"] <= 0)

    def corner_names(self):
        """Names of every corner besides tt/27 C/nominal V_DD, as used in the corner-screen columns."""
        return ([f"{c}_{t}" for c, t in self.corners if not (c == "tt" and t == 27)] + [f"vdd_{v:g}" for v in self.supplies]
                + [f"{c}_{t:g}_vdd_{v:g}" for c, t, v in self.combos])

    def tables(self):
        """Corner tables the LUT screen needs."""
        return sorted({f"{c}_{t}" for c, t in self.corners if not (c == "tt" and t == 27)} | {f"{c}_{t:g}" for c, t, _ in self.combos})

    def n_corners(self):
        return len(self.corners) + len(self.supplies) + len(self.combos)

    def lut_corner_feasible(self, dc, corner_names):
        ok = np.ones(len(dc), bool)
        for c in corner_names:
            ok &= dc[f"{c}_ok"].fillna(False).astype(bool).values
            ok &= self._lim(dc, f"{c}_").fillna(False).values
        return ok


def wire_spec(cache_dir, base=None, step=0.05e-12):
    """Layout in the loop: the specification with the first extracted layout's output wiring added to the load - the
    lumped capacitance fitted to the extraction (cache/wire_fit.json, tools/freeze_pick.py --fit), rounded up to `step`.
    Everything else as `base` (default: Table 2)."""
    f = Path(cache_dir) / "wire_fit.json"
    cw = round(math.ceil(json.loads(f.read_text())["c_wire"] / step - 1e-9) * step, 15) if f.exists() else 0.0
    return Spec(**{**asdict(base or Spec()), "name": "Wire-aware (Table 2 + the first layout's output wiring)", "c_wire": cw})


# ----------------------------------------------------------------------------------------- SPICE gate
def spice_gate(p, corner="tt", temp=27, spec: Spec = Spec(), noise=True):
    """SPICE counterpart of evaluator.evaluate_gate at one corner: gain on a 50 mV grid over the control span,
    bandwidth (C_L on v_out) at the evaluator's control steps, operating points at both ends of the span,
    and input-referred noise at maximum gain."""
    q = dict(p, corner=corner, temp=temp)
    g = 20 * np.log10(np.asarray(vf.gain_curve(q, FINE)))
    steps = ev.VSTEPS
    bw = np.array([vf.bandwidth(q, v, spec.CL + spec.c_wire)["f3db"] for v in steps])
    ops = {v: vf.characterise(q, v) for v in steps}      # headroom at every step: M2's minimum is mid-span
    k = 0
    while k + 1 < len(steps) and bw[k + 1] >= spec.bw_min_hz:
        k += 1
    win_ok = bool(bw[0] >= spec.bw_min_hz)
    lo_v = steps[k]
    sel = np.array(FINE) >= lo_v - 1e-9
    mono = bool(win_ok and np.all(g[sel][:-1] - g[sel][1:] > -ev.MONO_TOL_DB))
    r = dict(corner=f"{corner}/{temp}", av_max_db=float(g[0]), av_curve_db=g.tolist(), bw_curve=bw.tolist(),
             window_lo_v=lo_v if win_ok else None, monotonic=mono,
             range_db=float(g[0] - g[sel][-1]) if win_ok else 0.0,
             bw_min=float(bw[:k + 1].min()) if win_ok else float(bw[0]),
             i_tot=max(o["i_tot"] for o in ops.values()),
             vds_min=min(o[f"{d}_vds"] for o in ops.values() for d in GATE_DEVS),
             av_steps_db=[float(np.interp(v, FINE[::-1], g[::-1])) for v in steps],
             vds_by_step={f"{v:+.1f}": {d: ops[v][f"{d}_vds"] for d in GATE_DEVS} for v in ops},
             v_out={f"{v:+.1f}": ops[v]["v_out"] for v in ops})
    if noise:
        nz = vf.noise(q, 0.3, *spec.band)
        r.update(vrms=nz["vrms"], vn_1k=nz["vn_1k"])
    return r


def corner_pass(r, spec: Spec = Spec(), margin=True):
    """One corner against the spec. Headroom uses the flow margin (150 mV) when margin=True."""
    vlim = spec.vds_min_v + (spec.vds_margin_v if margin else 0.0)
    checks = dict(monotonic=r["monotonic"], range=r["range_db"] >= spec.range_min_db,
                  bandwidth=r["bw_min"] >= spec.bw_min_hz, current=spec.i_eff(r["i_tot"], r.get("i_sig", 0.0)) <= spec.i_tot_max,
                  headroom=r["vds_min"] >= vlim)
    return all(checks.values()), [k for k, v in checks.items() if not v]


def cname_of(r):
    """Corner-row name ('ss/27', 'tt/27/1.62V') -> corner-screen column prefix ('ss_27', 'vdd_1.62')."""
    parts = r["corner"].split("/")
    if len(parts) > 2:
        return f"vdd_{parts[2][:-1]}" if parts[:2] == ["tt", "27"] else f"{parts[0]}_{parts[1]}_vdd_{parts[2][:-1]}"
    return f"{parts[0]}_{parts[1]}"


def corner_label(r):
    """'tt/27' -> 'tt, 27 °C'; 'tt/27/1.62V' -> 'tt, 27 °C, V_DD 1.62 V'."""
    parts = r["corner"].split("/")
    s = f"{parts[0]}, {parts[1]} °C"
    return s + (f", V_DD {parts[2][:-1]} V" if len(parts) > 2 else "")


_LUT_TT, _LUT_C, _SIG = None, None, None
def current_sigma_abs(p, corner="tt/27"):
    """One-sigma spread (A) of the supply current from local mismatch of the bias units (evaluator.VGAModel.i_sigma),
    with the unit's gm/I_D from the table of that corner - the same estimate the LUT corner screen uses, so the
    screen and the SPICE judgement agree. 0 for designs without a unit-device mirror."""
    global _LUT_TT, _LUT_C
    if vf.bias_mode(p) != "unit":
        return 0.0
    import lut as _l
    root = Path(__file__).resolve().parent.parent / "cache"
    if _LUT_TT is None:
        _LUT_TT = _l.load(root / "lut_sky130.npz")
    parts = corner.split("/")
    key = f"{parts[0]}_{parts[1]}"
    q = dict(p, vdd=float(parts[2][:-1])) if len(parts) > 2 else p
    # memo on disk (cache/current_sigma.json): the corner tables are not shipped, so a tier-1 run re-judges cached
    # SPICE rows with the sigma stored when the tables were present
    global _SIG
    f_sig = root / "current_sigma.json"
    if _SIG is None:
        _SIG = json.loads(f_sig.read_text()) if f_sig.exists() else {}
    mk = json.dumps([corner] + [q.get(k) for k in ("W_u", "L_u", "nf_u", "m_tail", "m_sink", "iref", "vdd", "vin_cm",
                                                   "vctrl_cm")], default=float)
    if mk in _SIG:
        return _SIG[mk]
    if key == "tt_27":                                    # nominal, or a supply corner (tt table at that V_DD)
        val = ev.VGAModel(_LUT_TT, q).i_sigma(1.0)
    else:
        if _LUT_C is None:
            _LUT_C = _l.load_corners(root / "lut_corners.npz")
        val = ev.VGAModel(_LUT_C[key], q).i_sigma(1.0)
    _SIG[mk] = float(val)
    try:                                                  # merge with what other processes stored; atomic replace
        disk = json.loads(f_sig.read_text()) if f_sig.exists() else {}
    except ValueError:
        disk = {}
    disk.update(_SIG); _SIG = disk
    tmp = f_sig.with_name(f"current_sigma.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(_SIG, indent=0)); os.replace(tmp, f_sig)
    return float(val)


def judge(v, p, spec: Spec = Spec()):
    """(Re)apply the spec to SPICE corner rows of design p: every corner's gate, the supply current with mm_k sigma of
    local mismatch, and the noise gate at tt. Cached SPICE rows are re-judged, never re-simulated, when the spec
    changes."""
    sa = current_sigma_abs(p)
    fails = {}
    for r in v["corners"]:
        r["i_sig"] = current_sigma_abs(p, r["corner"]) / r["i_tot"]
        ok, why = corner_pass(r, spec)
        if not ok:
            fails[r["corner"]] = why
    if v["corners"][0]["vrms"] > spec.noise_max_vrms:
        fails.setdefault("tt/27", []).append("noise")
    v.update(passed=not fails, fails=fails, i_sig_abs=sa,
             i_eff_max=max(spec.i_eff(r["i_tot"], r["i_sig"]) for r in v["corners"]))
    return v


def verify(p, spec: Spec = Spec(), done=None):
    """Every process/temperature corner and every supply corner, plus the noise gate (tt only). `done` holds corner
    rows already simulated for this design (keyed by corner name); only the missing ones are run."""
    t0 = time.time(); done = done or {}
    rows = []
    for c, t in spec.corners:
        k = f"{c}/{t}"
        rows.append(done.get(k) or spice_gate(p, c, t, spec, noise=(c == "tt" and t == 27)))
    for c, t, v in [("tt", 27, v) for v in spec.supplies] + list(spec.combos):
        k = f"{c}/{t:g}/{v:g}V"
        if k in done:
            rows.append(done[k]); continue
        r = spice_gate(dict(p, vdd=v), c, t, spec, noise=False); r["corner"] = k; rows.append(r)
    tt = rows[0]
    v = dict(corners=rows, vrms=tt["vrms"], vn_1k=tt["vn_1k"], seconds=time.time() - t0,
             i_tot_max=max(r["i_tot"] for r in rows), i_tot_min=min(r["i_tot"] for r in rows),
             vds_min=min(r["vds_min"] for r in rows), bw_min=min(r["bw_min"] for r in rows),
             range_min=min(r["range_db"] for r in rows))
    return judge(v, p, spec)


def _need(spec):
    return ([f"{c}/{t}" for c, t in spec.corners] + [f"tt/27/{v:g}V" for v in spec.supplies]
            + [f"{c}/{t:g}/{v:g}V" for c, t, v in spec.combos])


def _complete(entry, spec):
    """A cached SPICE entry holds every corner the spec asks for."""
    have = {r["corner"] for r in (entry or {}).get("corners", [])}
    return bool(entry) and all(n in have for n in _need(spec))


def _verify_init():
    """Pool worker: its own ngspice work directory, so parallel decks never share file names."""
    w = vf.WORK / f"w{os.getpid()}"
    w.mkdir(parents=True, exist_ok=True)
    (w / ".spiceinit").write_text((vf.WORK / ".spiceinit").read_text())
    vf.WORK = w


def _verify_job(args):
    p, spec, done = args
    return verify(p, spec, done=done)


def verify_many(points, cache, f_spice, spec, base, procs=None):
    """SPICE verification (every corner) of design points missing from `cache`, in parallel; the cache file is
    rewritten after each design, so an interrupted run resumes where it stopped."""
    import multiprocessing as mp
    jobs, keys_ = [], []
    for point in points:
        key = json.dumps(point, sort_keys=True)
        if key in keys_ or _complete(cache.get(key), spec):
            continue
        have = {r["corner"]: r for r in cache.get(key, {}).get("corners", [])}
        jobs.append((ev.materialise(base, point), spec, have)); keys_.append(key)
    if not jobs:
        return
    n = max(1, min(procs or os.cpu_count() or 1, len(jobs)))
    with mp.Pool(n, initializer=_verify_init) as pool:
        for key, res in zip(keys_, pool.imap(_verify_job, jobs)):
            cache[key] = res
            f_spice.write_text(json.dumps(cache, indent=0))


# ----------------------------------------------------------------------------------------- the flow
def design_keys(space):
    return list(space)


def _point(row, keys):
    return {k: (int(round(float(row[k]))) if k.startswith(("nf_", "m_")) else round(float(row[k]), 6)) for k in keys}


# How each axis may be extended beyond the grid, and where it must stop. Finger counts double (or halve), lengths
# move to the next tabulated length, multiplicities and bias levels move by one step. The limits are the table's
# range (L), layout practicality (128 fingers = 640 um per device) and the signal ranges of the neighbouring stages.
EXTEND = dict(
    nf_in=("x2", 1, 128), nf_st=("x2", 1, 128), nf_mir=("x2", 1, 128), nf_u=("x2", 1, 32),
    L_in=("lut",), L_st=("lut",), L_mir=("lut",), L_u=("lut",),
    m_tail=("step", 1, 1, 40), m_sink=("step", 1, 1, 20),
    vin_cm=("step", 0.05, 0.55, 1.00), vctrl_cm=("step", 0.05, 0.90, 1.40), vbias=("step", 0.02, 0.45, 0.80),
)


def _step(axis, v, d, lut_L):
    """Next value of `axis` beyond v in direction d (+1/-1), or None at a model or practicality limit."""
    rule = EXTEND.get(axis)
    if rule is None:
        return None
    if rule[0] == "x2":
        nv = v * 2 if d > 0 else (v // 2 if v % 2 == 0 else None)
        return nv if nv is not None and rule[1] <= nv <= rule[2] else None
    if rule[0] == "lut":
        Ls = sorted(float(x) for x in lut_L)
        i = int(np.argmin([abs(x - v) for x in Ls])) + d
        return Ls[i] if 0 <= i < len(Ls) else None
    st, lo, hi = rule[1:]
    nv = v + d * st
    nv = int(nv) if axis.startswith("m_") else round(nv, 4)
    return nv if lo - 1e-9 <= nv <= hi + 1e-9 else None


def gate_area(pt):
    """Drawn gate area (um^2) of a 12T design point: sum of W*L*m over its twelve devices."""
    g = lambda k, d=1.0: float(pt.get(k, d))
    a = 2 * g("nf_in") * vf.W_F * g("L_in") + 4 * g("nf_st") * vf.W_F * g("L_st") + 2 * g("nf_mir") * vf.W_F * g("L_mir")
    if "m_tail" in pt:
        a += (g("m_tail") + 2 * g("m_sink", 0) + 1) * g("nf_u") * vf.W_F * g("L_u")
    return a


def n_targets_met(vrms, vn_1k, i_tot, spec):
    """How many of the graded noise targets (integrated noise, density at 1 kHz, NEF at tt current) a design meets."""
    nef = vf.nef(vrms, i_tot, spec.band[1] - spec.band[0])
    return int(vrms <= spec.noise_target_vrms) + int(vn_1k <= spec.vn1k_target) + int(nef <= spec.nef_target)


def _targets_v(v, spec):
    return n_targets_met(v["vrms"], v["vn_1k"], v["corners"][0]["i_tot"], spec)


def better(a, b, spec, targets_a=None, targets_b=None):
    """The pick rule as a comparison of two designs that both pass every corner: more graded targets met; then noise
    lower by more than NOISE_TIE; then, within NOISE_TIE, the rule key (least area, most headroom, lower current)."""
    ta = _targets_v(a, spec) if targets_a is None else targets_a
    tb = _targets_v(b, spec) if targets_b is None else targets_b
    if ta != tb:
        return ta > tb
    if a["vrms"] < b["vrms"] * (1 - NOISE_TIE):
        return True
    if a["vrms"] > b["vrms"] * (1 + NOISE_TIE):
        return False
    aa, ab = gate_area(a["point"]), gate_area(b["point"])
    if aa < ab * (1 - AREA_TIE):
        return True
    if aa > ab * (1 + AREA_TIE):
        return False
    return _rule_key(a) < _rule_key(b)


def _rule_key(v):
    """Secondary order inside the noise tie band: most worst-corner headroom, then the lower current (area is
    handled first, as a band - see _tie_pick)."""
    return (-round(v["vds_min"], 3), v["i_tot_max"])


def _tie_pick(vs):
    """Among designs already tied in noise: those within AREA_TIE of the least gate area, then _rule_key."""
    a0 = min(gate_area(v["point"]) for v in vs)
    return min((v for v in vs if gate_area(v["point"]) <= a0 * (1 + AREA_TIE)), key=_rule_key)


def why_infeasible(row, spec, cnames):
    """The first limit a screened design violates, with the corner ('' if it passes everywhere)."""
    if not bool(row.get("ok", False)):
        return "model: " + str(row.get("err", ""))[:40]
    vlim = spec.vds_min_v + spec.vds_margin_v + spec.lut_vds_extra_v
    def _t(x):                                     # True only for a real true value (NaN counts as False)
        return x is not None and not (isinstance(x, float) and math.isnan(x)) and bool(x)
    def lim(pre):
        g = lambda k: row.get(pre + k, np.nan)
        if pre and not _t(g("ok")):
            return "no operating point"
        if not _t(g("monotonic")): return "monotonic"
        if not g("range_db") >= spec.range_min_db: return "range"
        if not g("bw_min") >= spec.lut_bw_hz: return "bandwidth"
        if not spec.i_eff(g("i_tot"), 0.0 if pd.isna(g("i_sig")) else g("i_sig")) <= spec.i_tot_max: return "current"
        if not g("vds_min") >= vlim: return "headroom"
        return ""
    w = lim("")
    if w: return f"{w} (tt)"
    if not row.get("vrms", np.inf) <= spec.noise_max_vrms: return "noise gate (tt)"
    if not row.get("vov_in", 1) <= 0: return "input pair leaves weak inversion"
    if not all(f"{c}_ok" in row for c in cnames):
        return "not screened at the corners"
    for c in cnames:
        w = lim(f"{c}_")
        if w: return f"{w} ({c})"
    return ""


def violation(df, spec, cnames=()):
    """How far each screened design is from feasible: the sum of its normalised shortfalls (range, bandwidth with the
    LUT margin, current, headroom with the LUT margin, monotonicity) at tt, plus the noise gate and weak inversion;
    with corner names, the worst corner's shortfall is added. 0 = feasible everywhere it was checked."""
    vlim = spec.vds_min_v + spec.vds_margin_v + spec.lut_vds_extra_v
    bw = spec.lut_bw_hz
    def one(pre):
        g = lambda k: pd.to_numeric(df[pre + k], errors="coerce").fillna(-1e9 if k != "i_tot" else 1e9).values
        mono = df[pre + "monotonic"].fillna(False).astype(bool).values
        sg = lambda: pd.to_numeric(df[pre + "i_sig"], errors="coerce").values if pre + "i_sig" in df else np.zeros(len(df))
        return (np.maximum(0, (spec.range_min_db - g("range_db")) / spec.range_min_db) + np.maximum(0, (bw - g("bw_min")) / bw)
                + np.maximum(0, (g("i_tot") * (1 + spec.mm_k * np.nan_to_num(sg(), nan=0.0)) - spec.i_tot_max) / spec.i_tot_max)
                + np.maximum(0, (vlim - g("vds_min")) / vlim)
                + (~mono).astype(float))
    v = one("") + np.maximum(0, (df["vrms"].values - spec.noise_max_vrms) / spec.noise_max_vrms) + np.maximum(0, df["vov_in"].values / 0.1)
    if len(cnames):
        v = v + np.max([np.minimum(one(f"{c}_"), 10.0) for c in cnames], axis=0)
    return np.minimum(v, 1e6)


def _full_corner_cols(dc, cnames):
    """Corner-screen columns for every corner, also when no design in the batch had an operating point at some corner
    (sweep_corners then writes no column for it): missing values mean 'no operating point', which fails that corner."""
    for c in cnames:
        if f"{c}_ok" not in dc:
            dc[f"{c}_ok"] = False
        for k in ev.CORNER_COLS:
            if f"{c}_{k}" not in dc:
                dc[f"{c}_{k}"] = False if k == "monotonic" else np.nan
    return dc


def _screen_points(points, spec, base, lut_path, corners_path, procs, keys, cnames):
    """tt screen + corner screen of explicit design points (dicts of design keys). Returns a DataFrame."""
    P = [ev.materialise(base, q) for q in points]
    d = ev.sweep_points(lut_path, P, procs=procs, CL=spec.CL)
    d["feas_tt"] = spec.lut_feasible(d)
    d["feas_corner"] = False
    idx = np.where(d["feas_tt"].values)[0]
    if len(idx):
        dc = ev.sweep_corners(corners_path, [P[i] for i in idx], procs=procs, CL=spec.CL, lut_path=lut_path,
                              supplies=spec.supplies, combos=spec.combos, tables=spec.tables())
        dc = _full_corner_cols(dc, cnames)
        for col in dc.columns:
            d.loc[d.index[idx], col] = dc[col].values
        d.loc[d.index[idx], "feas_corner"] = spec.lut_corner_feasible(dc, cnames)
    return d


def extend_search(spec, df, keys, base, lut_path, corners_path, procs=None, log=print):
    """Stage 4. A pattern search on the design grid, aimed at the pick rule (lowest noise). Each round takes the
    spec.ext_seeds lowest-noise corner-feasible designs (or, while nothing is feasible, the 20 designs closest to
    feasible - see violation) and screens every unexplored single-axis neighbour of them - one step beyond the grid
    wherever a seed sits on its edge (EXTEND). Neighbours inside the grid are already screened, so only edges grow.
    Stops when no seed has an unexplored neighbour, when two rounds together improve the best noise by less than
    spec.ext_tol, or (reported) at spec.ext_max_iter rounds. Returns (new rows, history)."""
    lut_L = np.load(lut_path)["nfet__L"]
    cnames = spec.corner_names()
    seen = set(map(tuple, df[keys].round(6).values.tolist()))
    new, hist = [], []
    nxt = int(df.index.max()) + 1
    for it in range(1, spec.ext_max_iter + 1):
        allr = pd.concat([df] + new) if new else df
        feas = allr[allr["feas_corner"]]
        if len(feas):
            seeds, mode = feas.nsmallest(spec.ext_seeds, "vrms"), "lowest noise"
        else:                                      # nothing feasible yet: grow around the designs closest to feasible
            okr = allr[allr["ok"].astype(bool)]
            ttf = okr[okr["feas_tt"].astype(bool)]
            pool = ttf if len(ttf) else okr
            vio = violation(pool, spec, cnames if len(ttf) else ())
            seeds, mode = pool.iloc[np.argsort(vio, kind="stable")[:20]], "closest to feasible"
            best_vio, vpool = float(np.min(vio)), ("corners" if len(ttf) else "tt")
        cand = {}
        for _, r in seeds.iterrows():
            pt = _point(r, keys)
            for ax in keys:
                for dd in (1, -1):
                    nv = _step(ax, pt[ax], dd, lut_L)
                    if nv is None:
                        continue
                    q = dict(pt); q[ax] = nv
                    t = tuple(round(float(q[k]), 6) for k in keys)
                    if t not in seen and t not in cand:
                        cand[t] = (q, ax)
        if not cand:
            hist.append(dict(iter=it, seeds=len(seeds), mode=mode, new=0, stop="no unexplored neighbour"))
            break
        pts = [q for q, _ in cand.values()]; seen.update(cand)
        d = _screen_points(pts, spec, base, lut_path, corners_path, procs, keys, cnames)
        d["ext_iter"] = it; d["ext_axis"] = [ax for _, ax in cand.values()]
        d.index = range(nxt, nxt + len(d)); nxt += len(d)
        best0 = float(feas["vrms"].min()) if len(feas) else float("nan")
        new.append(d)
        f_new = d[d["feas_corner"]]
        allf = pd.concat([feas, f_new])
        front_new = ev.pareto(allf, minimize=("vrms", "i_tot")) if len(allf) else allf
        joined = int(front_new.index.isin(d.index).sum())
        if not len(feas):                          # the same measure as the round's seeds (tt only, or tt + corners)
            okn = pd.concat([allr, d]); okn = okn[okn["ok"].astype(bool)]
            if vpool == "corners":
                okn = okn[okn["feas_tt"].astype(bool)]
            vio_new = float(np.min(violation(okn, spec, cnames if vpool == "corners" else ())))
        h = dict(iter=it, seeds=len(seeds), mode=mode, new=len(d), tt_feasible=int(d["feas_tt"].sum()),
                 corner_feasible=len(f_new), joined_front=joined,
                 best_vrms=float(allf["vrms"].min()) if len(allf) else float("nan"), best_vrms_before=best0,
                 best_range=float(pd.concat([allr, d])["range_db"].max()),
                 axes=sorted({ax for ax, f_ in zip(d["ext_axis"], d["feas_corner"]) if f_}))
        if not len(feas):
            h.update(violation_before=best_vio, violation_after=vio_new, violation_measure=vpool)
        hist.append(h)
        log(f"  extend {it}: {len(d)} new designs around {len(seeds)} seeds ({mode}); {len(f_new)} corner-feasible, "
            f"{joined} join the front; best noise {1e6*h['best_vrms']:.2f} uV")
        if len(feas) and len(hist) >= 2:
            b2 = hist[-2].get("best_vrms_before", float("nan"))
            if np.isfinite(b2) and h["best_vrms"] > b2 * (1 - spec.ext_tol):
                hist[-1]["stop"] = (f"best noise improved by {100*(1-h['best_vrms']/b2):.2f} % over two rounds "
                                    f"(< {100*spec.ext_tol:g} %)")
                break
        if it == spec.ext_max_iter:
            hist[-1]["stop"] = "round limit reached (search not converged)"
        if (not len(feas) and not len(f_new) and len(hist) >= 2
                and hist[-2].get("violation_measure") == h["violation_measure"]):
            v0 = hist[-2]["violation_before"]                # nothing feasible yet: stop once the shortfall stops shrinking
            if h["violation_after"] > v0 * (1 - 0.02) - 1e-9:
                hist[-1]["stop"] = (f"distance to feasibility improved by < 2 % over two rounds "
                                    f"({v0:.3f} -> {h['violation_after']:.3f})")
                break
    return (pd.concat(new) if new else df.iloc[:0]), hist


def edge_audit(pick_point, df, keys, spec, base, lut_path, corners_path, procs=None):
    """Stage 8. Every single-axis neighbour of the pick (one step each way): screened if not yet, and classified
    as 'limit' (beyond a model/practicality limit), 'infeasible: <limit> (<corner>)' or 'feasible, noise +x %'."""
    lut_L = np.load(lut_path)["nfet__L"]; cnames = spec.corner_names()
    look = {tuple(round(float(x), 6) for x in r): i for i, r in zip(df.index, df[keys].values.tolist())}
    kp = tuple(round(float(pick_point[k]), 6) for k in keys)
    if kp in look:
        rowp = df.loc[look[kp]]
    else:                                   # a pick found by polishing: a neighbour screened in an earlier audit
        rowp = _screen_points([dict(pick_point)], spec, base, lut_path, corners_path, 1, keys, cnames).iloc[0]
    todo, rows = [], []
    for ax in keys:
        for dd in (1, -1):
            nv = _step(ax, pick_point[ax], dd, lut_L)
            q = None if nv is None else dict(pick_point, **{ax: nv})
            rows.append([ax, dd, nv, q])
            if q is not None and tuple(round(float(q[k]), 6) for k in keys) not in look:
                todo.append(q)
    extra = _screen_points(todo, spec, base, lut_path, corners_path, procs, keys, cnames) if todo else None
    if extra is not None:
        for q, (_, r) in zip(todo, extra.iterrows()):
            look[tuple(round(float(q[k]), 6) for k in keys)] = ("x", r)
    out = []
    for ax, dd, nv, q in rows:
        if q is None:
            out.append(dict(axis=ax, dir=dd, value=None, status="limit", detail="model / practicality limit")); continue
        h = look[tuple(round(float(q[k]), 6) for k in keys)]
        r = h[1] if isinstance(h, tuple) else df.loc[h]
        w = why_infeasible(r, spec, cnames)
        if w:
            out.append(dict(axis=ax, dir=dd, value=nv, status="infeasible", detail=w))
        else:
            dn = float(r["vrms"]) / float(rowp["vrms"]) - 1
            da = gate_area(q) / gate_area(pick_point) - 1
            tn = n_targets_met(float(r["vrms"]), float(r["vn_1k"]), float(r["i_tot"]), spec)
            tp = n_targets_met(float(rowp["vrms"]), float(rowp["vn_1k"]), float(rowp["i_tot"]), spec)
            beats = tn > tp or (tn == tp and (dn < -NOISE_TIE or (dn <= NOISE_TIE and da < -AREA_TIE)))
            out.append(dict(axis=ax, dir=dd, value=nv, status="feasible", point=q, dnoise=dn, darea=da, beats=bool(beats),
                            di=float(r["i_tot"]) / float(rowp["i_tot"]) - 1,
                            detail=f"noise {100*dn:+.1f} %, area {100*da:+.0f} %"))
    return out


def run_flow(spec: Spec, topology: str, lut_path, base: dict, space: dict | None = None, cache_dir=None,
             corners_path=None, rerun_screen=False, rerun_spice=False, procs=None, log=print, spice=True, points=None):
    """Spec + topology -> screened space, corner screen, front, SPICE-verified front and the pick.
    Every stage is cached per (topology, spec) so the notebook can re-render without simulators."""
    space = space or (ev.SPACE_12T if topology == "12T" else ev.SPACE_9T)
    tag = f"{topology}_{spec.name.split()[0].lower().strip('()')}"
    cache_dir = Path(cache_dir or "cache")
    corners_path = corners_path or (Path(lut_path).parent / "lut_corners.npz")
    f_screen = cache_dir / f"flow_{topology}_screen_cl{spec.CL*1e12:g}p.csv.gz"   # spec-independent except C_L
    f_corner = cache_dir / f"flow_{topology}_corners_cl{spec.CL*1e12:g}p.csv.gz"
    f_spice = cache_dir / f"flow_{tag}_spice.json"
    f_meta = cache_dir / f"flow_{topology}_meta_cl{spec.CL*1e12:g}p.json"     # measured stage times
    meta = json.loads(f_meta.read_text()) if f_meta.exists() else {}
    keys = design_keys(space)
    cnames = spec.corner_names()
    # 1. screen at tt (the LUT is exact at tt; noise is evaluated here)
    t0 = time.time()
    if f_screen.exists() and not rerun_screen:
        df = pd.read_csv(f_screen, low_memory=False)
    else:
        if points is not None:                  # an explicit set of starting points instead of a grid
            df = ev.sweep_points(lut_path, [ev.materialise(base, q) for q in points], procs=procs, CL=spec.CL)
            for k in keys:
                df[k] = [q[k] for q in points]
        else:
            df = ev.sweep(lut_path, base, space, kind="gate", procs=procs, CL=spec.CL)
        df.to_csv(f_screen, index=False, float_format="%.6g")
        df = pd.read_csv(f_screen, low_memory=False)              # continue from the stored values: a re-run from the cache is identical
        meta.update(screen_s=time.time() - t0, screen_n=len(df), procs=procs or __import__("os").cpu_count(),
                    platform=__import__("platform").platform())
        f_meta.write_text(json.dumps(meta, indent=1))
    t_screen = meta.get("screen_s", time.time() - t0)
    # 2. tt filter
    df["feas_tt"] = spec.lut_feasible(df)
    tt_ok = df[df["feas_tt"]]
    # 3. corner screen of the tt-feasible designs (corner tables, no noise)
    t0 = time.time()
    if len(tt_ok):
        dc = None
        if f_corner.exists() and not rerun_screen:
            dc = pd.read_csv(f_corner, low_memory=False)
            if all(f"{c}_ok" in dc.columns for c in cnames) and set(tt_ok.index) <= set(dc["row"]):
                dc = dc.set_index("row").reindex(tt_ok.index).reset_index()
            else:
                dc = None                                   # cached screen lacks a corner or a design: redo it
        if dc is None:
            pts = [ev.materialise(base, _point(r, keys)) for _, r in tt_ok.iterrows()]
            dc = ev.sweep_corners(corners_path, pts, procs=procs, CL=spec.CL, lut_path=lut_path, supplies=spec.supplies,
                                  combos=spec.combos, tables=spec.tables())
            dc = _full_corner_cols(dc, cnames)
            dc.insert(0, "row", tt_ok.index.values)
            dc.to_csv(f_corner, index=False, float_format="%.6g")
            dc = pd.read_csv(f_corner, low_memory=False).set_index("row").reindex(tt_ok.index).reset_index()
            meta.update(corner_s=time.time() - t0, corner_n=len(pts)); f_meta.write_text(json.dumps(meta, indent=1))
        df["feas_corner"] = False
        df.loc[tt_ok.index, "feas_corner"] = spec.lut_corner_feasible(dc, cnames)
        for c in cnames:
            for k in ev.CORNER_COLS + ("ok",):
                df.loc[tt_ok.index, f"{c}_{k}"] = dc[f"{c}_{k}"].values
    else:
        df["feas_corner"] = False
    t_corner = meta.get("corner_s", time.time() - t0)
    df["ext_iter"] = 0
    # 4. extend the grid where the front touches its edge
    f_ext, f_exth = cache_dir / f"flow_{tag}_extend.csv.gz", cache_dir / f"flow_{tag}_extend.json"
    hist, n_base = [], len(df)
    if spec.extend:
        t0 = time.time()
        if f_ext.exists() and f_exth.exists() and not rerun_screen:
            de = pd.read_csv(f_ext, index_col=0, low_memory=False); hist = json.loads(f_exth.read_text())
        else:
            de, hist = extend_search(spec, df, keys, base, lut_path, corners_path, procs=procs, log=log)
            de.to_csv(f_ext, float_format="%.6g"); f_exth.write_text(json.dumps(hist, indent=1))
            de = pd.read_csv(f_ext, index_col=0, low_memory=False)
            meta.update({f"extend_s_{tag}": time.time() - t0}); f_meta.write_text(json.dumps(meta, indent=1))
        if len(de):
            for col in ("feas_tt", "feas_corner", "ok"):
                de[col] = de[col].astype(bool)
            df = pd.concat([df, de])
    feas = df[df["feas_corner"]]
    # 4. front: integrated input noise against supply current
    front = ev.pareto(feas, minimize=("vrms", "i_tot")).sort_values("i_tot") if len(feas) else feas
    short = front
    if len(front) > spec.max_spice:
        short = front.iloc[np.unique(np.linspace(0, len(front) - 1, spec.max_spice).round().astype(int))]
    if len(feas):                       # the rule's tie-break is area: add the smallest designs tied with the best noise
        tie = feas[feas["vrms"] <= feas["vrms"].min() * (1 + NOISE_TIE)]
        tie = tie.iloc[np.argsort([gate_area(_point(r, keys)) for _, r in tie.iterrows()], kind="stable")[:5]]
        short = pd.concat([short, tie]); short = short[~short.index.duplicated()]
    log(f"[{topology} | {spec.name}] {n_base:,} designs screened ({t_screen:.0f} s) + {len(df) - n_base:,} by extension "
        f"| tt-feasible {int(df['feas_tt'].sum()):,} | corner-feasible {len(feas):,} | front {len(front)} | to SPICE {len(short)}")
    # 5. SPICE at every corner (cached per design)
    cache = json.loads(f_spice.read_text()) if f_spice.exists() and not rerun_spice else {}
    ver = []
    if spice:
        verify_many([_point(row, keys) for _, row in short.iterrows()], cache, f_spice, spec, base, procs)
    for idx, row in short.iterrows():
        point = _point(row, keys); key = json.dumps(point, sort_keys=True)
        if not _complete(cache.get(key), spec):
            continue
        v = judge(json.loads(json.dumps(cache[key])), ev.materialise(base, point), spec)
        v["point"] = point; v["row"] = int(idx)
        v["lut"] = {k: float(row[k]) for k in ("av_max_db", "range_db", "bw_min", "i_tot", "vds_min", "vrms", "vn_1k")}
        v["lut_corners"] = {c: {k: float(row.get(f"{c}_{k}", np.nan)) for k in ("vds_min", "bw_min", "range_db")} for c in cnames}
        ver.append(v)
    # 7. pick, among designs passing every corner in SPICE: the most graded noise targets met (Table 2: 7 uV, 50 nV/rtHz,
    #    NEF 5); then the lowest noise, designs within NOISE_TIE of it counting as equal (that is below the LUT-vs-SPICE
    #    noise error); among those, designs within AREA_TIE of the least gate area, then the most worst-corner headroom,
    #    then the lower current.
    def _pick(vs):
        ps = [v for v in vs if v["passed"]]
        if not ps:
            return None
        tmax = max(_targets_v(v, spec) for v in ps)          # first: the most graded targets met
        ps = [v for v in ps if _targets_v(v, spec) == tmax]
        n0 = min(v["vrms"] for v in ps)
        return _tie_pick([v for v in ps if v["vrms"] <= n0 * (1 + NOISE_TIE)])
    pick = _pick(ver)
    log(f"[{topology} | {spec.name}] SPICE: {sum(v['passed'] for v in ver)} of {len(ver)} pass at every corner"
        + (f"; pick: {pick['vrms']*1e6:.1f} uV, {pick['i_tot_max']*1e6:.2f} uA" if pick else "; no pick"))
    # 8. edge audit and polish: every single-axis neighbour of the pick is screened (LUT). A feasible neighbour that
    #    would win under the pick rule is simulated in SPICE at every corner and joins the verified set; the rule is
    #    re-applied, and the audit repeats around a new pick, until no neighbour beats it.
    audit, polish = None, []
    if pick and spec.extend:
        f_aud = cache_dir / f"flow_{tag}_audit.json"
        ac = json.loads(f_aud.read_text()) if f_aud.exists() and not rerun_screen else {}
        for _ in range(6):
            key = json.dumps(pick["point"], sort_keys=True)
            if key not in ac:
                ac[key] = edge_audit(pick["point"], df, keys, spec, base, lut_path, corners_path, procs=procs)
                f_aud.write_text(json.dumps(ac, indent=1))
            audit = ac[key]
            have = {json.dumps(v["point"], sort_keys=True) for v in ver}
            new_ = [a for a in audit if a.get("beats") and json.dumps(a["point"], sort_keys=True) not in have]
            if spice:
                verify_many([a["point"] for a in new_], cache, f_spice, spec, base, procs)
            for a in new_:
                ck = json.dumps(a["point"], sort_keys=True)
                if not _complete(cache.get(ck), spec):
                    continue
                c_ = cache[ck]
                if "lut" not in c_ or "lut_corners" not in c_:   # the polished design's LUT row, stored with its SPICE rows
                    r1 = _screen_points([a["point"]], spec, base, lut_path, corners_path, 1, keys, cnames).iloc[0]
                    c_["lut"] = {k: float(r1[k]) for k in ("av_max_db", "range_db", "bw_min", "i_tot", "vds_min", "vrms", "vn_1k")}
                    c_["lut_corners"] = {c: {k: float(r1.get(f"{c}_{k}", np.nan)) for k in ("vds_min", "bw_min", "range_db")}
                                         for c in cnames}
                    f_spice.write_text(json.dumps(cache, indent=0))
                v = judge(json.loads(json.dumps(c_)), ev.materialise(base, a["point"]), spec)
                v["point"] = a["point"]; v["row"] = -1; v["polish"] = True
                ver.append(v)
            if not new_:
                break
            new_pick = _pick(ver)
            polish.append(dict(challengers=len(new_), passed=sum(1 for v in ver if v.get("polish") and v["passed"]),
                               pick_changed=new_pick is not pick))
            if new_pick is pick:
                break
            pick = new_pick
        vmap = {json.dumps(v["point"], sort_keys=True): v for v in ver}
        for a in audit or []:                         # what SPICE said about any neighbour it simulated
            v = vmap.get(json.dumps(a["point"], sort_keys=True)) if a.get("point") else None
            if v is not None:
                a["spice"] = ("passes every corner, noise " + f"{100*(v['vrms']/pick['vrms']-1):+.1f} %") if v["passed"] \
                    else "fails: " + "; ".join(f"{k} {', '.join(w)}" for k, w in v["fails"].items())
                a["spice_beats"] = bool(v["passed"] and v is not pick and better(v, pick, spec))
        log(f"[{topology} | {spec.name}] audit: {sum(1 for a in audit if a['status'] == 'feasible')} feasible neighbours, "
            f"{sum(1 for a in audit if a.get('beats'))} would win in the LUT, polish rounds {len(polish)}; "
            f"pick: {pick['vrms']*1e6:.2f} uV, area {gate_area(pick['point']):.0f} um^2")
    ok = df[df["ok"]]
    secs = [v["seconds"] for v in ver if "seconds" in v]
    return dict(spec=asdict(spec), topology=topology, n=len(df), n_ok=int(df["ok"].sum()), n_tt=int(df["feas_tt"].sum()), meta=meta,
                spice_s_per_design=float(np.mean(secs)) if secs else None,
                n_feasible=len(feas), n_front=len(front), screen_s=t_screen, corner_s=t_corner,
                n_base=n_base, n_extended=len(df) - n_base, extend_hist=hist, audit=audit, polish=polish,
                best_lut_range_db=float(ok["range_db"].max()) if len(ok) else float("nan"),
                df=df, front=front, verified=ver, pick=pick, keys=keys, corners=cnames)


# Alternative starting points for the search (convergence check): every axis moved by one step from the main grid,
# and random points on the same lattice the search steps on.
SPACE_12T_SHIFTED = dict(
    nf_in=[8, 32], L_in=[2.0, 4.0], nf_st=[2, 4], L_st=[2.0, 4.0], nf_mir=[2, 8, 32], L_mir=[2.0, 4.0],
    vctrl_cm=[0.95, 1.05, 1.15], vin_cm=[0.70, 0.80], L_u=[4.0, 8.0], m_tail=[7, 9, 11], m_sink=[1, 2], nf_u=[2, 8],
)
LATTICE_12T = dict(
    nf_in=[2 ** k for k in range(1, 8)], L_in=[0.5, 1.0, 2.0, 4.0, 8.0, 16.0], nf_st=[1, 2, 4, 8, 16],
    L_st=[0.5, 1.0, 2.0, 4.0, 8.0], nf_mir=[2 ** k for k in range(0, 8)], L_mir=[0.5, 1.0, 2.0, 4.0, 8.0],
    vctrl_cm=[round(0.90 + 0.05 * k, 2) for k in range(11)], vin_cm=[round(0.55 + 0.05 * k, 2) for k in range(10)],
    L_u=[1.0, 2.0, 4.0, 8.0, 16.0], m_tail=list(range(4, 17)), m_sink=[1, 2, 3, 4, 5], nf_u=[1, 2, 4, 8, 16],
)


def bias_tolerance(point, spec, base, lut_path, corners_path=None, step=0.005, span=0.10, procs=None):
    """How far each bias common mode can move from the pick before the specification itself fails at some corner -
    headroom at the specification's 130 mV, bandwidth at its 10 kHz, no design margin (LUT estimate; its headroom
    error is a few mV, Table 9b). Returns {axis: (largest step down, largest step up)} in V."""
    corners_path = corners_path or Path(lut_path).parent / "lut_corners.npz"
    spec = Spec(**{**asdict(spec), "vds_margin_v": 0.0, "lut_vds_extra_v": 0.0, "lut_bw_factor": 1.0})
    keys = list(point); cnames = spec.corner_names(); out = {}
    for ax in ("vin_cm", "vctrl_cm"):
        offs = [d for d in np.arange(-span, span + 1e-9, step) if abs(d) > 1e-9]
        pts = [dict(point, **{ax: round(point[ax] + d, 4)}) for d in offs]
        d_ = _screen_points(pts, spec, base, lut_path, corners_path, procs, keys, cnames)
        ok = dict(zip([round(x, 4) for x in offs], d_["feas_corner"].astype(bool).values))
        dn = 0.0
        for d in sorted((x for x in ok if x < 0), reverse=True):
            if not ok[d]: break
            dn = d
        up = 0.0
        for d in sorted(x for x in ok if x > 0):
            if not ok[d]: break
            up = d
        out[ax] = (dn, up)
    return out


def margin_check(res, spec, base, n=8, procs=None, cache=None):
    """What the screen's margins cost: designs that meet every corner with the LUT margins removed (headroom at the
    SPICE limit, bandwidth at the specification) but not with them, lowest noise first, simulated at every corner.
    Returns how many pass in SPICE and whether any would beat the pick."""
    import tempfile
    df = res["df"]; cn = spec.corner_names()
    loose = Spec(**{**asdict(spec), "lut_vds_extra_v": 0.0, "lut_bw_factor": 1.0})
    tt = df["ok"].astype(bool) & loose.lut_feasible(df)
    cand = df[tt & ~df["feas_corner"].astype(bool)]
    if not len(cand):
        return dict(n_candidates=0, verified=[])
    okc = loose.lut_corner_feasible(cand, cn)
    cand = cand[okc].nsmallest(n, "vrms")
    keys = res["keys"]; pts = [_point(r, keys) for _, r in cand.iterrows()]
    f = Path(cache or tempfile.mkdtemp()) / "margin_check_spice.json"
    c = json.loads(f.read_text()) if f.exists() else {}
    verify_many(pts, c, f, spec, base, procs)
    out = []
    for p_, (_, r) in zip(pts, cand.iterrows()):
        v = judge(json.loads(json.dumps(c[json.dumps(p_, sort_keys=True)])), ev.materialise(base, p_), spec)
        out.append(dict(point=p_, lut_vrms=float(r["vrms"]), vrms=v["vrms"], passed=v["passed"], fails=v["fails"]))
    pk = res["pick"]
    return dict(n_candidates=int(okc.sum()), verified=out, n_pass=sum(o["passed"] for o in out),
                beats_pick=sum(1 for o in out if o["passed"] and pk and o["vrms"] < pk["vrms"] * (1 - NOISE_TIE)))


def lut_choice(res, spec):
    """The pick rule applied to the LUT estimates of every corner-feasible design of a run: most targets met, lowest
    noise, then least area within NOISE_TIE. Used to compare searches without simulating each."""
    feas = res["df"][res["df"]["feas_corner"].astype(bool)]
    if not len(feas):
        return None
    keys = res["keys"]
    t = np.array([n_targets_met(float(r["vrms"]), float(r["vn_1k"]), float(r["i_tot"]), spec) for _, r in feas.iterrows()])
    f2 = feas[t == t.max()]
    tie = f2[f2["vrms"] <= f2["vrms"].min() * (1 + NOISE_TIE)]
    pts = [_point(r, keys) for _, r in tie.iterrows()]
    ar = np.array([gate_area(p_) for p_ in pts]); band = np.where(ar <= ar.min() * (1 + AREA_TIE))[0]
    i = int(band[np.argmax(tie["vds_min"].values[band])])
    r = tie.iloc[i]
    return dict(point=pts[i], vrms=float(r["vrms"]), vn_1k=float(r["vn_1k"]), i_tot=float(r["i_tot"]), targets=int(t.max()),
                area=gate_area(pts[i]), best_vrms=float(feas["vrms"].min()), n=len(res["df"]), n_feasible=len(feas),
                rounds=len(res["extend_hist"]))


def convergence_check(spec, base, lut_path, cache_dir=None, n_random=3000, seed=7, procs=None, log=print, rerun=False):
    """Run stages 1-4 (screen, corner screen, extension) from two other starting points - the grid moved by one step
    on every axis, and random lattice points - and report what each search converges to, next to the main run.
    The intermediate screens go to a scratch directory (only the summary is kept)."""
    import tempfile
    cache_dir = Path(cache_dir or tempfile.mkdtemp(prefix="vga_conv_"))
    out = {}
    rng = np.random.default_rng(seed)
    keys = list(ev.SPACE_12T)
    rand = []
    while len(rand) < n_random:
        q = {k: LATTICE_12T[k][int(rng.integers(len(LATTICE_12T[k])))] for k in keys}
        rand.append(q)
    for name, space in (("shifted grid", SPACE_12T_SHIFTED), ("random lattice points", rand)):
        cd = cache_dir / ("conv_shift" if name.startswith("shifted") else "conv_random")
        cd.mkdir(parents=True, exist_ok=True)
        res = run_flow(spec, "12T", lut_path, base, space=space if isinstance(space, dict) else None, points=None if isinstance(space, dict) else space,
                       cache_dir=cd, corners_path=Path(lut_path).parent / "lut_corners.npz", spice=False, procs=procs, log=log,
                       rerun_screen=rerun)
        out[name] = lut_choice(res, spec)
    return out


def verify_netlist(path, p, spec: Spec = Spec(), name="vga_core_12t"):
    """The full SPICE gate (process/temperature and supply corners, noise) on an external netlist of the core -
    the schematic netlist the flow wrote, or a layout-extracted one - biased as design p. Internal nets must keep
    the names net2..net5 (labels in the layout) for the headroom checks."""
    return verify(dict(p, subckt=(str(path), name)), spec)


def diagnose(df, spec: Spec = Spec()):
    """Which tt limit stops a topology: for each limit, how many solved designs fail it and how many fail ONLY it
    (they meet every other limit). The limit with the most sole failures is the binding one."""
    ok = df[df["ok"].astype(bool)]
    vlim = spec.vds_min_v + spec.vds_margin_v + spec.lut_vds_extra_v
    m = dict(monotonic=ok["monotonic"].astype(bool).values, range=(ok["range_db"] >= spec.range_min_db).values,
             bandwidth=(ok["bw_min"] >= spec.lut_bw_hz).values,
             current=(spec.i_eff(ok["i_tot"], ok["i_sig"] if "i_sig" in ok else 0.0) <= spec.i_tot_max).values,
             headroom=(ok["vds_min"] >= vlim).values,
             noise=(ok["vrms"] <= spec.noise_max_vrms).values, weak_inversion=(ok["vov_in"] <= 0).values)
    out = {}
    for k in m:
        others = np.all([m[j] for j in m if j != k], axis=0)
        out[k] = dict(fail=int((~m[k]).sum()), sole=int((others & ~m[k]).sum()))
    universal = [k for k in out if out[k]["fail"] == len(ok)]            # a limit no design meets: structural
    binding = universal[0] if universal else max(out, key=lambda k: out[k]["sole"])
    sel = np.ones(len(ok), bool) if universal else np.all([m[j] for j in m if j != binding], axis=0)
    col = {"range": "range_db", "bandwidth": "bw_min", "headroom": "vds_min", "noise": "vrms", "current": "i_tot"}.get(binding)
    best = None
    if col and sel.any():
        best = float(ok.loc[sel, col].max() if binding in ("range", "bandwidth", "headroom") else ok.loc[sel, col].min())
    return dict(n_solved=len(ok), limits=out, binding=binding, structural=bool(universal), best_binding_metric=best,
                metric=col)


def run_topologies(spec: Spec, library, lut_path, base, **kw):
    """The topology loop: run the flow on each topology of `library` in order (simplest first). A topology with no
    verified design is reported with the limit that stops it (diagnose); the first one with a pick is selected."""
    out, selected = {}, None
    for topo in library:
        res = run_flow(spec, topo, lut_path, base, **kw)
        res["diagnosis"] = diagnose(res["df"], spec)
        out[topo] = res
        if selected is None and res["pick"]:
            selected = topo
    return dict(results=out, selected=selected)


def confirm_best(res, base, k=6, spec: Spec = Spec()):
    """SPICE check (tt) of the k designs with the largest LUT control range - used when a topology has no feasible
    design, so that the infeasibility is confirmed by the simulator and not only by the model."""
    df = res["df"]; ok = df[df["ok"]].sort_values(["range_db", "mono_range_db"], ascending=False).head(k)
    out = []
    for _, row in ok.iterrows():
        point = _point(row, res["keys"]); p = ev.materialise(base, point)
        out.append(dict(point=point, lut=dict(range_db=float(row["range_db"]), mono_range_db=float(row["mono_range_db"]),
                                             bw_maxgain=float(row["bw_maxgain"])), spice=spice_gate(p, "tt", 27, spec)))
    return out
