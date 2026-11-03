"""Compiled simulation core (optional): same algorithm as ``PulseSimulator``, in C++.

``PulseSimulator(..., engine="auto")`` (the default, or ``GS_ENGINE=auto|native|python``)
runs each ``run()`` through the compiled core when it can: a Liberty delay provider, an
``M2Model`` (or no) r-filter, and a C++ compiler on first use (``g++``/``c++``; the
shared library is cached next to the source or in ``~/.cache/glitchscope``).  The
compiled core returns the same trace, suppressed pulses and event metadata as the
Python engine (event ids included; ``tests/test_fastsim.py`` checks this on every
benchmark), so everything downstream is unchanged.  Anything it cannot handle falls
back to the Python engine, which also re-raises any simulation error with its usual
message.

Liberty arc selection (``when`` conditions, timing-sense filtering) and the cell
functions are evaluated once per (library cell, pin order) here in Python and
passed down as lookup tables; the core interpolates the selected NLDM tables with
the same floating-point operation order as ``liberty.bilinear``.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from .logic import eval_primitive
from .model import TraceEvent

SRC = Path(__file__).resolve().parent / "_fast" / "fastsim.cpp"
_LIB = None
_LIB_ERR = None
_REASONS = ("M2_REJECTED_ROLLBACK", "M1_INERTIAL", "M2_BELOW_REJECTION", "NONPOSITIVE_WIDTH")
_ERRORS = {1: "M2 rollback cycled", 2: "M2 rollback did not converge", 3: "timed/final mismatch",
           4: "causal-event ambiguity", 5: "no valid timing arc"}

_I = ctypes.POINTER(ctypes.c_int)
_L = ctypes.POINTER(ctypes.c_longlong)
_D = ctypes.POINTER(ctypes.c_double)
_U = ctypes.POINTER(ctypes.c_uint8)


def _build(out):
    cxx = os.environ.get("CXX") or shutil.which("g++") or shutil.which("c++") or shutil.which("clang++")
    if not cxx:
        raise RuntimeError("no C++ compiler found (g++, c++ or clang++)")
    tmp = out.with_suffix(f".{os.getpid()}.tmp")
    subprocess.run([cxx, "-O2", "-std=c++14", "-ffp-contract=off", "-shared", "-fPIC", str(SRC), "-o", str(tmp)],
                   check=True, capture_output=True, text=True)
    os.replace(tmp, out)


def load_library():
    """ctypes handle to the compiled core (compiled on first use); raises if unavailable."""
    global _LIB, _LIB_ERR
    if _LIB is not None:
        return _LIB
    if _LIB_ERR is not None:
        raise RuntimeError(_LIB_ERR)
    try:
        tag = hashlib.sha1(SRC.read_bytes()).hexdigest()[:12]
        name = f"libgsfast-{tag}.so"
        dirs = [SRC.parent, Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "glitchscope"]
        path = next((d / name for d in dirs if (d / name).exists()), None)
        if path is None:
            for d in dirs:
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    _build(d / name)
                    path = d / name
                    break
                except PermissionError:
                    continue
                except subprocess.CalledProcessError as e:
                    raise RuntimeError("compiling the native core failed:\n" + e.stderr[-2000:])
        if path is None:
            raise RuntimeError("no writable directory for the native core")
        lib = ctypes.CDLL(str(path))
    except Exception as e:  # noqa: BLE001 - recorded, Python engine used instead
        _LIB_ERR = str(e)
        raise
    lib.gs_create.restype = ctypes.c_void_p
    lib.gs_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, _I, _I, _I, _I, _U, _I, ctypes.c_int,
                              _I, _I, _I, _I, _I, _D, _I, _I, ctypes.c_int, ctypes.c_int, _I, _I, _I, _D,
                              ctypes.c_int, ctypes.c_double, ctypes.c_double, _D, _U, ctypes.c_double,
                              ctypes.c_double, _L]
    lib.gs_free.argtypes = [ctypes.c_void_p]
    lib.gs_set_scale.argtypes = [ctypes.c_void_p, ctypes.c_int, _D]
    lib.gs_set_talpha.argtypes = [ctypes.c_void_p, ctypes.c_int, _D]
    lib.gs_run.argtypes = [ctypes.c_void_p, ctypes.c_int, _L, _I, _I, _I, _I, _U, _U, ctypes.c_int, ctypes.c_int,
                           ctypes.c_int]
    for f in ("gs_n_trace", "gs_n_sup", "gs_reruns", "gs_n_trace_parents"):
        getattr(lib, f).argtypes = [ctypes.c_void_p]
    lib.gs_n_sup_parents.argtypes = [ctypes.c_void_p, _I]
    lib.gs_get_trace.argtypes = [ctypes.c_void_p, _I, _L, _I, _I, _I, _I, _I, _I, _I, _L, _L, _L, _L, _L,
                                 _I, _I, _I]
    lib.gs_get_sup.argtypes = [ctypes.c_void_p, _I, _I, _I, _L, _L, _L, _L, _L, _I, _I, _I, _I, _I, _I]
    lib.gs_get_final.argtypes = [ctypes.c_void_p, _U]
    lib.gs_get_rcalls.argtypes = [ctypes.c_void_p, _I]
    _LIB = lib
    return lib


def available():
    try:
        load_library()
        return True
    except Exception:  # noqa: BLE001
        return False


def _p(a):
    t = {np.int32: _I, np.int64: _L, np.float64: _D, np.uint8: _U}[a.dtype.type]
    return a.ctypes.data_as(t)


def _arr(x, dt):
    return np.ascontiguousarray(np.asarray(x, dtype=dt))


class NativeCore:
    """Compiled counterpart of one ``PulseSimulator`` (fixed cells, loads, model, r-filter).
    The network's ``initial_inputs`` may change between runs."""

    def __init__(self, sim):
        from .liberty import LibertyDelayProvider
        from .m2model import M2Model
        if type(sim.dp) is not LibertyDelayProvider:
            raise TypeError("native core needs a LibertyDelayProvider")
        if sim.model == "M2" and not isinstance(sim.r_filter, M2Model):
            raise TypeError("native core needs an M2Model r-filter")
        self.lib = load_library()
        self.core_seconds = 0.0          # time spent inside the compiled kernel
        net = sim.network
        cells = list(net.cells)
        self.cells_obj = net.cells
        self.cell_names = [c.name for c in cells]
        drivers = {c.output for c in cells}
        names = set(net.primary_inputs) | set(net.initial_inputs) | drivers
        for c in cells:
            names.update(c.inputs.values())
        self.nets = sorted(names)
        nid = {n: i for i, n in enumerate(self.nets)}
        self.nid = nid
        self.sources = [n for n in self.nets if n not in drivers]
        self.pis = set(net.primary_inputs)
        cell_rank = {n: i for i, n in enumerate(sorted(self.cell_names))}
        lib = sim.dp.lib
        # per-cell structure
        cell_out, in_off, in_net, pin_rank, truth_off, arc_off = [], [0], [], [], [], []
        truth, arc = [], []
        tcache, acache = {}, {}
        tabs, tab_id = [], {}
        self.pin_names = []

        def tab(t):
            if len(t.index_1) < 2 or len(t.index_2) < 2:
                return -1
            k = id(t)
            if k not in tab_id:
                tab_id[k] = len(tabs)
                tabs.append(t)
            return tab_id[k]

        for c in cells:
            pins = list(c.inputs)
            k = len(pins)
            if k > 12:
                raise ValueError(f"{c.name}: too many inputs for the native core")
            self.pin_names.append(pins)
            cell_out.append(nid[c.output])
            in_net.extend(nid[c.inputs[p]] for p in pins)
            srt = sorted(pins)
            pin_rank.extend(srt.index(p) for p in pins)
            in_off.append(len(in_net))
            tk = (c.kind, tuple(pins))
            if tk not in tcache:
                tcache[tk] = len(truth)
                for b in range(1 << k):
                    truth.append(int(eval_primitive(c.kind, {p: (b >> j) & 1 for j, p in enumerate(pins)})))
            truth_off.append(tcache[tk])
            ak = (c.library_cell or c.kind, c.library_output_pin, tuple(pins))
            if ak not in acache:
                acache[ak] = len(arc) // 2
                for j, pin in enumerate(pins):
                    for newv in (0, 1):
                        for old in (0, 1):
                            for b in range(1 << k):
                                pv = {p: (b >> i) & 1 for i, p in enumerate(pins)}
                                try:
                                    a = sim.dp.select_arc(c, newv, related_pin=pin, pin_values=pv,
                                                          input_transition=(old, pv[pin]))
                                    dt = tab(a.cell_rise if newv else a.cell_fall)
                                    st = tab(a.rise_transition if newv else a.fall_transition)
                                    if dt < 0 or st < 0:
                                        dt = st = -1
                                except (ValueError, KeyError):
                                    dt = st = -1
                                arc.extend((dt, st))
            arc_off.append(acache[ak])
        self._net_obj = np.array(self.nets + [""], dtype=object)
        self._cell_obj = np.array(self.cell_names + ["$PI"], dtype=object)    # index -1 -> "$PI"
        self._pin_obj = np.array([p for ps in self.pin_names for p in ps] + [""], dtype=object)
        tab_n1, tab_n2, tab_off, data = [], [], [], []
        for t in tabs:
            tab_n1.append(len(t.index_1)); tab_n2.append(len(t.index_2)); tab_off.append(len(data))
            data.extend(float(x) for x in t.index_1)
            data.extend(float(x) for x in t.index_2)
            for row in t.values:
                if len(row) != len(t.index_2):
                    raise ValueError("ragged Liberty table")
                data.extend(float(x) for x in row)
            if len(t.values) != len(t.index_1):
                raise ValueError("ragged Liberty table")
        fan_off, fan_cell = [0], []
        idx = {c.name: i for i, c in enumerate(cells)}
        for n in self.nets:
            fan_cell.extend(idx[c.name] for c in sim.fanout.get(n, []))
            fan_off.append(len(fan_cell))
        # M2 rejection coefficients
        rab = np.zeros(4 * len(cells)); rcal = np.zeros(2 * len(cells), dtype=np.uint8)
        clamp = (0.3, 2.5)
        self.r_keys = None
        if sim.model == "M2":
            from .m2model import proxy_key
            m2 = sim.r_filter
            clamp = m2.clamp
            self.r_keys = []
            for i, c in enumerate(cells):
                key = m2._key(c)
                kk = proxy_key(key, m2.cells) or key
                self.r_keys.append(kk)
                for pol_i, pol in enumerate(("positive", "negative")):
                    m = m2.cells.get(kk, {}).get(pol, {}).get("r_filter")
                    if m is not None and m["a"] == m["a"]:
                        rab[4 * i + 2 * pol_i] = float(m["a"]); rab[4 * i + 2 * pol_i + 1] = float(m["b"])
                        rcal[2 * i + pol_i] = 1
        pi_slew = [sim.input_slew_fs_by_net.get(n, sim.default_input_slew_fs) for n in self.nets]
        self._keep = dict(
            cell_out=_arr(cell_out, np.int32), in_off=_arr(in_off, np.int32), in_net=_arr(in_net, np.int32),
            pin_rank=_arr(pin_rank, np.int32), truth=_arr(truth, np.uint8), truth_off=_arr(truth_off, np.int32),
            topo=_arr([sim.topo_index[c.name] for c in cells], np.int32),
            crank=_arr([cell_rank[c.name] for c in cells], np.int32),
            nrank=_arr(range(len(self.nets)), np.int32), fan_off=_arr(fan_off, np.int32),
            fan_cell=_arr(fan_cell, np.int32), load=_arr([sim.loads.get(n, 0.0) for n in self.nets], np.float64),
            arc_off=_arr(arc_off, np.int32), arc=_arr(arc, np.int32), tab_n1=_arr(tab_n1, np.int32),
            tab_n2=_arr(tab_n2, np.int32), tab_off=_arr(tab_off, np.int32), data=_arr(data, np.float64),
            rab=_arr(rab, np.float64), rcal=_arr(rcal, np.uint8), pi_slew=_arr(pi_slew, np.int64))
        k_ = self._keep
        model = {"M0": 0, "M1": 1, "M2": 2}[sim.model]
        self.h = self.lib.gs_create(
            len(self.nets), len(cells), model, _p(k_["cell_out"]), _p(k_["in_off"]), _p(k_["in_net"]),
            _p(k_["pin_rank"]), _p(k_["truth"]), _p(k_["truth_off"]), len(truth), _p(k_["topo"]), _p(k_["crank"]),
            _p(k_["nrank"]), _p(k_["fan_off"]), _p(k_["fan_cell"]), _p(k_["load"]), _p(k_["arc_off"]),
            _p(k_["arc"]), len(arc), len(tabs), _p(k_["tab_n1"]), _p(k_["tab_n2"]), _p(k_["tab_off"]),
            _p(k_["data"]), len(data), float(lib.time_unit_ps), float(lib.capacitance_unit_ff), _p(k_["rab"]),
            _p(k_["rcal"]), float(clamp[0]), float(clamp[1]), _p(k_["pi_slew"]))

    def __del__(self):
        h = getattr(self, "h", None)
        if h:
            self.lib.gs_free(h)
            self.h = None

    # ------------------------------------------------------------------
    def supports(self, network):
        return network.cells is self.cells_obj and all(n in network.initial_inputs for n in self.sources)

    def _talpha(self, sim):
        """Per (cell, pulse polarity) trailing-slew coefficients, or None when all are 0."""
        if sim.model != "M2":
            return None
        key = (sim.trail_slew_alpha, id(sim.r_filter))
        if getattr(self, "_ta_key", None) != key:
            byname = {c.name: c for c in sim.network.cells}
            ta = np.zeros(2 * len(self.cell_names), dtype=np.float64)
            for i, n in enumerate(self.cell_names):
                for j, v in enumerate((1, 0)):
                    ta[2 * i + j] = sim._trail_alpha(byname[n], v)
            self._ta_key, self._ta = key, (ta if ta.any() else None)
        return self._ta

    def run(self, sim, epochs):
        """Result dict like ``PulseSimulator.run``, or None when the core reports an error
        (the caller re-runs in Python to raise the usual exception)."""
        from .sim import EventMeta, Suppressed
        lib, nid = self.lib, self.nid
        net = sim.network
        ordered = sorted(epochs, key=lambda e: (e.time_fs, e.epoch_id))
        for a, b in zip(ordered, ordered[1:]):
            if a.time_fs == b.time_fs:
                raise ValueError("same-time epochs must be merged into one atomic epoch")
        ep_time, ep_id, ep_off, ep_net, ep_val = [], [], [0], [], []
        for ep in ordered:
            ep_time.append(ep.time_fs); ep_id.append(ep.epoch_id)
            for n in sorted(ep.updates):
                if n not in self.pis:
                    raise ValueError(f"non-PI stimulus {n}")
                ep_net.append(nid[n]); ep_val.append(int(ep.updates[n]))
            ep_off.append(len(ep_net))
        init = np.zeros(len(self.nets), dtype=np.uint8)
        for n, v in net.initial_inputs.items():
            init[nid[n]] = int(v)
        ideal = np.zeros(len(self.cell_names), dtype=np.uint8)
        if sim.ideal:
            for i, n in enumerate(self.cell_names):
                ideal[i] = n in sim.ideal
        a = dict(t=_arr(ep_time, np.int64), id=_arr(ep_id, np.int32), off=_arr(ep_off, np.int32),
                 net=_arr(ep_net or [0], np.int32), val=_arr(ep_val or [0], np.int32))
        ds = getattr(sim, "delay_scale", None)
        if ds:
            sc = np.array([float(ds.get(n, 1.0)) for n in self.cell_names], dtype=np.float64)
            lib.gs_set_scale(self.h, len(sc), _p(sc))
        else:
            lib.gs_set_scale(self.h, 0, _p(np.zeros(1)))
        ta = self._talpha(sim)
        if ta is not None:
            lib.gs_set_talpha(self.h, len(ta), _p(ta))
        else:
            lib.gs_set_talpha(self.h, 0, _p(np.zeros(1)))
        t0 = time.perf_counter()
        rc = lib.gs_run(self.h, len(ordered), _p(a["t"]), _p(a["id"]), _p(a["off"]), _p(a["net"]), _p(a["val"]),
                        _p(init), _p(ideal), int(sim.max_reruns), int(sim.rollback),
                        int(sim.checkpoint_every))
        self.core_seconds += time.perf_counter() - t0
        self._rcalls(sim)
        if rc:
            return None
        return self._collect(sim, EventMeta, Suppressed)

    def _rcalls(self, sim):
        if self.r_keys is None:
            return
        n = len(self.cell_names)
        calls = np.zeros(2 * n, dtype=np.int32)
        self.lib.gs_get_rcalls(self.h, _p(calls))
        m2 = sim.r_filter
        for i in np.nonzero(calls)[0]:
            c, pol = divmod(int(i), 2)
            key = self.r_keys[c]
            m2.resolve(m2._key(sim.network.cells[c]))       # records drive-strength proxies
            if not self._keep["rcal"][i]:
                m2.uncalibrated[key] = m2.uncalibrated.get(key, 0) + int(calls[i])

    def _collect(self, sim, EventMeta, Suppressed):
        lib, h = self.lib, self.h
        nt, ns = lib.gs_n_trace(h), lib.gs_n_sup(h)
        npar = lib.gs_n_trace_parents(h)
        I = lambda n: np.zeros(max(1, n), dtype=np.int32)      # noqa: E731
        L = lambda n: np.zeros(max(1, n), dtype=np.int64)      # noqa: E731
        t = dict(eid=I(nt), time=L(nt), epoch=I(nt), net=I(nt), old=I(nt), new=I(nt), cell=I(nt), poff=I(nt + 1),
                 par=I(npar), cause=L(nt), delay=L(nt), sin=L(nt), sout=L(nt), R=L(nt), pin=I(nt), multi=I(nt),
                 has=I(nt))
        lib.gs_get_trace(h, *(_p(t[k]) for k in ("eid", "time", "epoch", "net", "old", "new", "cell", "poff", "par",
                                                 "cause", "delay", "sin", "sout", "R", "pin", "multi", "has")))
        nets, cn, pn = self.nets, self.cell_names, self.pin_names
        t = {k: v[:nt] if k not in ("poff", "par") else v for k, v in t.items()}
        poff, par = t["poff"].tolist(), t["par"].tolist()
        parents = [tuple(par[a:b]) for a, b in zip(poff, poff[1:])]
        trace = list(map(TraceEvent, t["eid"].tolist(), t["time"].tolist(), t["epoch"].tolist(),
                         self._net_obj[t["net"]].tolist(), t["old"].tolist(), t["new"].tolist(),
                         self._cell_obj[t["cell"]].tolist(), parents))
        mk = t["has"].astype(bool)
        mc = t["cell"][mk]
        meta = dict(zip(t["eid"][mk].tolist(), map(
            EventMeta, t["cause"][mk].tolist(), t["delay"][mk].tolist(), t["sin"][mk].tolist(), t["sout"][mk].tolist(),
            self._pin_obj[self._keep["in_off"][mc] + t["pin"][mk]].tolist(), t["R"][mk].tolist(),
            t["multi"][mk].astype(bool).tolist())))
        cnt = np.zeros(2, dtype=np.int32)
        lib.gs_n_sup_parents(h, _p(cnt))
        s = dict(cell=I(ns), epoch=I(ns), lead=I(ns), cause=L(ns), cancel=L(ns), delay=L(ns), R=L(ns), slew=L(ns),
                 reason=I(ns), pin=I(ns), lpo=I(ns + 1), lp=I(int(cnt[0])), cpo=I(ns + 1), cp=I(int(cnt[1])))
        lib.gs_get_sup(h, *(_p(s[k]) for k in ("cell", "epoch", "lead", "cause", "cancel", "delay", "R", "slew",
                                               "reason", "pin", "lpo", "lp", "cpo", "cp")))
        sl = {k: v.tolist() for k, v in s.items()}
        sup = []
        for i in range(ns):
            c = sl["cell"][i]
            pin = sl["pin"][i]
            sup.append(Suppressed(cn[c], nets[self._keep["cell_out"][c]], sl["epoch"][i], sl["lead"][i],
                                  sl["cause"][i], sl["cancel"][i], sl["cancel"][i] - sl["cause"][i], sl["delay"][i],
                                  sl["R"][i], sl["slew"][i], _REASONS[sl["reason"][i]],
                                  tuple(sl["lp"][sl["lpo"][i]:sl["lpo"][i + 1]]),
                                  tuple(sl["cp"][sl["cpo"][i]:sl["cpo"][i + 1]]),
                                  pn[c][pin] if pin >= 0 else ""))
        fin = np.zeros(len(nets), dtype=np.uint8)
        lib.gs_get_final(h, _p(fin))
        final = dict(zip(nets, fin.tolist()))
        return {"trace": trace, "final": final, "suppressed": sup, "violations": [], "stale": [], "meta": meta,
                "loads": sim.loads, "model": sim.model, "reruns": lib.gs_reruns(h), "engine": "native"}


_CACHE = {}


def core_for(sim):
    """Shared compiled model for every simulator over the same cells, delay provider,
    pulse model, r-filter, loads and input slews (e.g. all interventions of one
    attribution run)."""
    key = (id(sim.network.cells), id(sim.dp), sim.model, id(sim.r_filter), sim.default_input_slew_fs,
           tuple(sorted(sim.input_slew_fs_by_net.items())), tuple(sorted(sim.loads.items())))
    hit = _CACHE.get(key)
    if hit is not None and hit[0] is sim.network.cells and hit[1] is sim.dp and hit[2] is sim.r_filter:
        return hit[3]
    core = NativeCore(sim)
    if len(_CACHE) >= 8:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (sim.network.cells, sim.dp, sim.r_filter, core)
    return core


def engine_default():
    e = os.environ.get("GS_ENGINE", "auto").lower()
    return e if e in ("auto", "native", "python") else "auto"
