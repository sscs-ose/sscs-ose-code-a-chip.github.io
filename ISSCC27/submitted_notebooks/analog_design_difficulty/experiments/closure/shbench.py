#!/usr/bin/env python3
"""Sequential (repeated-sample) sample-and-hold bench for the restart closure work.

A *design* (driver subcircuit, sampling network, Cs, clock edges, bias) and a *PVT
condition* (process corner, supply, temperature) are turned into an ngspice netlist
in which the driver command steps through a sequence of target levels and the
sampling switch closes and opens once per period. The voltage held on Cs at the end
of one acquisition is therefore the initial state of the next acquisition: no ideal
precharge switch is used.

Timing of cycle k (period T):
    k*T                 sampling clock starts to close the switch (edge ``edge``)
    k*T + Tacq          sampling clock starts to open the switch
    (k+1)*T             next acquisition
Cycle 0 is the start-up cycle: the transient starts from the DC operating point with
the switch closed and the command at the first level, so Cs starts at the driver
output. Cycle 0 is never counted in a metric.

The command of sample k is applied at ``k*T + t_in`` (``t_in`` may be negative: the
command changes during the hold of the previous sample, as a continuous input would).

Netlists and raw outputs are written under ``results/generated/closure/`` (git-ignored).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
NETLISTS = HERE / "netlists"
GENERATED = REPO / "results" / "generated" / "closure"


def pdk_library() -> Path:
    explicit = os.environ.get("SKY130_NGSPICE_LIB")
    if explicit:
        lib = Path(explicit)
    else:
        root = Path(os.environ.get("PDK_ROOT", Path.home() / ".volare"))
        lib = root / "sky130A" / "libs.tech" / "ngspice" / "sky130.lib.spice"
    if not lib.is_file():
        raise FileNotFoundError(f"SKY130 ngspice library not found at {lib}. Set PDK_ROOT or SKY130_NGSPICE_LIB.")
    return lib


def ngspice_version() -> str:
    exe = shutil.which("ngspice")
    if exe is None:
        raise FileNotFoundError("ngspice not found on PATH")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    m = re.search(r"ngspice-\S+", out)
    return m.group(0) if m else out.strip().splitlines()[0]


# --------------------------------------------------------------------------- design

@dataclass(frozen=True)
class Switch:
    """Sampling network. ``kind``: ``tg`` (transmission gate), ``tg_dummy`` (TG with
    half-size dummies on the Cs side), ``tg_bp`` (TG on the top plate plus an NMOS
    bottom-plate switch that opens ``t_lead`` before the top-plate switch)."""
    kind: str = "tg"
    wn: float = 5.0          # finger width, um
    mn: int = 3              # NMOS fingers
    wp: float = 5.0
    mp: int = 6
    l: float = 0.15
    w_bot: float = 5.0       # bottom-plate NMOS finger width (tg_bp)
    m_bot: int = 4
    t_lead: float = 1e-9     # bottom-plate switch opens this much earlier (tg_bp)
    dummy_scale: float = 0.5
    # --- extension (R3 sampling-network study) ---
    nmodel: str = "sky130_fd_pr__nfet_01v8"   # device flavour of the TG / dummy NMOS
    pmodel: str = "sky130_fd_pr__pfet_01v8"   # device flavour of the TG / dummy PMOS
    lp: float = 0.0          # PMOS channel length (0: same as ``l``); pfet_01v8_lvt needs >= 0.35
    # kind ``sub``: a transistor-level switch subcircuit with ports
    #   (in out phi phib vdd vss), e.g. a bootstrapped NMOS switch
    subckt_file: str = ""
    subckt_name: str = ""
    subckt_params: tuple = ()  # (name, value) pairs appended to the instance line
    probes: tuple = ()         # extra node names inside the switch to save, e.g. ("xsw.g",)
    # initial conditions of internal switch nodes for the start-up operating point:
    # (node, expression) with ``{vdd}`` and ``{v0}`` (first command level) substituted;
    # used so that a bootstrapped switch starts "closed" with a charged CB, as the bench
    # definition (DC operating point with the switch closed) requires
    ic: tuple = ()


@dataclass(frozen=True)
class Design:
    name: str
    driver_file: str = "driver_f2.spice"
    driver_subckt: str = "drv_f2"
    iref: float = 10e-6
    switch: Switch = field(default_factory=Switch)
    cs: float = 1e-12
    edge: float = 0.2e-9
    skew: float = 0.0         # phib edges delayed by this much relative to phi (sensitivity runs)
    extra_params: tuple = ()  # (name, value) pairs passed as .param


@dataclass(frozen=True)
class PVT:
    corner: str = "tt"
    vdd: float = 1.8
    temp: float = 27.0

    @property
    def tag(self) -> str:
        return f"{self.corner}_{self.vdd:.2f}V_{self.temp:+.0f}C"


@dataclass(frozen=True)
class Timing:
    period: float = 100e-9
    tacq: float = 40e-9
    t_in: float = -59e-9     # command change of sample k relative to k*T (primary: t_o[k-1] + 1 ns)
    in_edge: float = 0.5e-9


# Stress variant of CLOSURE_BRIEF.md: the command of sample k steps when the switch starts to close.
# 1 ps after the clock breakpoint: exactly coincident PWL breakpoints make ngspice abort.
STRESS = Timing(t_in=1e-12)


@dataclass(frozen=True)
class SimOpts:
    tmax: float = 5e-12
    reltol: float = 1e-5
    vntol: float = 1e-7
    abstol: float = 1e-13
    tstep_out: float = 5e-12
    method: str = "trap"


# --------------------------------------------------------------------------- netlist

def _pwl(points: list[tuple[float, float]]) -> str:
    return "PWL(" + " ".join(f"{t:.10e} {v:.6g}" for t, v in points) + ")"


def _clock(n: int, tm: Timing, edge: float, vhi: float, active_high_during_acq: bool,
           open_shift: float = 0.0, delay: float = 0.0) -> str:
    """Clock that is 'on' during each acquisition. The switch is on from t=0 (cycle 0)."""
    on, off = (vhi, 0.0) if active_high_during_acq else (0.0, vhi)
    pts = [(0.0, on)]
    for k in range(n):
        t_open = k * tm.period + tm.tacq - open_shift + delay
        pts += [(t_open, on), (t_open + edge, off)]
        if k + 1 < n:
            t_close = (k + 1) * tm.period + delay
            pts += [(t_close, off), (t_close + edge, on)]
    return _pwl(pts)


def _command(levels: list[float], tm: Timing) -> str:
    pts = [(0.0, levels[0])]
    for k in range(1, len(levels)):
        t = k * tm.period + tm.t_in
        pts += [(t, levels[k - 1]), (t + tm.in_edge, levels[k])]
    return _pwl(pts)


def _switch_lines(sw: Switch) -> list[str]:
    n = sw.nmodel
    p = sw.pmodel
    lp = sw.lp or sw.l
    if sw.kind == "sub":
        prm = " ".join(f"{k}={v}" for k, v in sw.subckt_params)
        return [f"XSW out samp phi phib vdd 0 {sw.subckt_name} {prm}".rstrip()]
    lines = [
        f"XSWN out phi samp 0 {n} W={sw.wn} L={sw.l} m={sw.mn}",
        f"XSWP out phib samp vdd {p} W={sw.wp} L={lp} m={sw.mp}",
    ]
    if sw.kind == "tg_dummy":
        # dummies: source and drain on the Cs node, gates on the complementary clocks
        lines += [
            f"XDMN samp phib samp 0 {n} W={sw.wn * sw.dummy_scale} L={sw.l} m={sw.mn}",
            f"XDMP samp phi samp vdd {p} W={sw.wp * sw.dummy_scale} L={lp} m={sw.mp}",
        ]
    if sw.kind == "tg_bp":
        lines += [f"XSWB bot phie 0 0 {n} W={sw.w_bot} L={sw.l} m={sw.m_bot}"]
    return lines


def build_netlist(design: Design, pvt: PVT, levels: list[float], tm: Timing, so: SimOpts,
                  outdir: Path, save_internal: bool = False) -> str:
    n = len(levels)
    tstop = n * tm.period
    sw = design.switch
    bot = "bot" if sw.kind == "tg_bp" else "0"
    lines = [
        f"* closure bench: {design.name} {pvt.tag} {n} cycles",
        f'.lib "{pdk_library()}" {pvt.corner}',
        f".temp {pvt.temp}",
        f'.include "{outdir / design.driver_file}"',
    ]
    if sw.kind == "sub":
        lines.append(f'.include "{outdir / sw.subckt_file}"')
    lines += [
        f".option reltol={so.reltol} vntol={so.vntol} abstol={so.abstol}"
        + (f" method={so.method}" if so.method != "trap" else ""),
    ]
    for k, v in design.extra_params:
        lines.append(f".param {k}={v}")
    lines += [
        f"VDD vdd 0 {pvt.vdd}",
        f"IREF vdd ibias {design.iref}",
        f"XDRV vcmd out out ibias vdd 0 {design.driver_subckt}",
        f"VCMD vcmd 0 {_command(levels, tm)}",
        f"VPHI phi 0 {_clock(n, tm, design.edge, pvt.vdd, True)}",
        f"VPHIB phib 0 {_clock(n, tm, design.edge, pvt.vdd, False, delay=design.skew)}",
    ]
    if sw.kind == "tg_bp":
        lines.append(f"VPHIE phie 0 {_clock(n, tm, design.edge, pvt.vdd, True, open_shift=sw.t_lead)}")
    lines += _switch_lines(sw)
    if sw.ic:
        vals = [f"v({nd})={eval(ex.format(vdd=pvt.vdd, v0=levels[0])):.6g}" for nd, ex in sw.ic]
        lines.append(".ic " + " ".join(vals))
    lines.append(f"CS samp {bot} {design.cs}")
    vecs = [f"v({nm})" if nm != "ivdd" else "i(VDD)" for nm in _vec_names(sw)]
    lines += [
        ".control",
        "save " + " ".join(vecs),
        f"tran {so.tstep_out} {tstop} 0 {so.tmax}",
        f"linearize {' '.join(vecs)}",
        f"wrdata {outdir / 'tran.dat'} {' '.join(vecs)}",
        ".endc",
        ".end",
    ]
    return "\n".join(lines) + "\n"


def _vec_names(sw: Switch) -> list[str]:
    names = ["samp", "out", "vcmd", "ivdd"]
    if sw.kind == "tg_bp":
        names.insert(1, "bot")
    return names + list(sw.probes)


def _key(*objs) -> str:
    blob = json.dumps([asdict(o) if hasattr(o, "__dataclass_fields__") else o for o in objs],
                      sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def run_sequence(design: Design, pvt: PVT, levels: list[float], tm: Timing = Timing(),
                 so: SimOpts = SimOpts(), label: str = "seq", reuse: bool | None = None) -> dict:
    """Run one sequence and return the waveform arrays plus timing metadata."""
    if reuse is None:
        reuse = os.environ.get("CLOSURE_REUSE", "1") == "1"
    key = _key(design, pvt, levels, tm, so)
    outdir = GENERATED / design.name / f"{label}_{pvt.tag}_{key}"
    outdir.mkdir(parents=True, exist_ok=True)
    shutil.copy(NETLISTS / design.driver_file, outdir / design.driver_file)
    if design.switch.kind == "sub":
        shutil.copy(NETLISTS / design.switch.subckt_file, outdir / design.switch.subckt_file)
    text = build_netlist(design, pvt, levels, tm, so, outdir)
    netlist = outdir / "bench.spice"
    log = outdir / "ngspice.log"
    dat = outdir / "tran.dat"
    if not (reuse and netlist.is_file() and dat.is_file() and netlist.read_text() == text):
        netlist.write_text(text)
        proc = subprocess.run(["ngspice", "-b", str(netlist)], cwd=HERE, capture_output=True, text=True)
        log.write_text(proc.stdout + proc.stderr)
        if proc.returncode != 0 or not dat.is_file():
            raise RuntimeError(f"ngspice failed: {log}")
    names = _vec_names(design.switch)
    raw = np.loadtxt(dat, ndmin=2)
    w = {"t": raw[:, 0]}
    for i, nm in enumerate(names):
        w[nm] = raw[:, 2 * i + 1]
    w.update({"levels": list(levels), "timing": asdict(tm), "pvt": asdict(pvt), "design": design.name,
              "dir": str(outdir)})
    return w


def run_many(jobs: list[tuple], workers: int | None = None) -> list[dict]:
    """``jobs``: tuples of positional args for :func:`run_sequence`."""
    workers = workers or int(os.environ.get("CLOSURE_WORKERS", max(1, (os.cpu_count() or 2) - 1)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda j: run_sequence(*j), jobs))


# --------------------------------------------------------------------------- reading

def window_mean(w: dict, t0: float, t1: float, node: str = "samp") -> float:
    t = w["t"]
    sel = (t >= t0) & (t <= t1)
    return float(np.mean(w[node][sel]))


def window_extremes(w: dict, t0: float, t1: float, node: str = "samp") -> tuple[float, float]:
    t = w["t"]
    sel = (t >= t0) & (t <= t1)
    return float(np.min(w[node][sel])), float(np.max(w[node][sel]))


def supply_current(w: dict) -> float:
    """Average supply current (A, positive = drawn from VDD) over the counted cycles."""
    tm = w["timing"]
    t = w["t"]
    sel = t >= tm["period"]
    return float(-np.mean(w["ivdd"][sel]))
