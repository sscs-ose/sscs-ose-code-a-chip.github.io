"""r24 probe: direct, causal test of the decision-memory mechanism (no branch deletion).

r24 attributed the decision memory to the floating source node between each off trim device and its off
series switch (sp<k> / sn<k>). Deleting the branches removed it, but also removed their capacitance. Here
the branches stay in place and only the state of those nodes is manipulated during the last reset
(ideal switches, closed 20.0-21.9 ns, released before the 22 ns evaluation edge):

  base       nothing connected (the switches are open throughout): the r24 memory
  self       each node forced to the value it already has under the same prior: switch control
  short      sp<k> shorted to sn<k>: differential state erased, common mode kept
  transplant each node forced to the value it has under the opposite prior: memory should flip sign

  python -B r24_probe.py run [design ...]      # default: baseline lvt_balanced_4b unit6_w6 u6_w12_l05
  python -B r24_probe.py qualify [design bits [variant ...]] # memory fixes vs the shipped trim
  python -B r24_probe.py spot [design bits]    # light version for 6-bit trims (memory, LSB, half range)
  python -B r24_probe.py energy [design bits]  # energy per comparison at TT (VDD + clock-edge charge)
Fix candidates: 'swap' (r24: series switch on the x side), 'precharge' (a minimum PMOS, gate clk,
precharges each floating node to VDD during reset) and 'equalize' (a minimum NMOS per bit, gate clkb from
one minimum inverter, shorts sp<k> to sn<k> during reset). No trim device moves. Thresholds with the
earlier cycles pinned at -5 mV; signed code k drives the |k| bits of the p (k > 0) or n (k < 0) side.
"""
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor

ARGS, sys.argv = sys.argv[1:], sys.argv[:1]
import r24_isf as R  # noqa: E402
from r24_isf import N  # noqa: E402

PRIORS = (-1.0, 1.0, -5.0, 5.0)
DESIGNS = ("baseline", "lvt_balanced_4b", "unit6_w6", "u6_w12_l05")
ON_S, OFF_S, READ_S = 20.0e-9, 21.9e-9, 21.95e-9
MODEL = ".model prbsw sw vt=0.5 vh=0.1 ron=10 roff=1e14"


def float_nodes(h):
    """Source nodes of the trim devices (Xt*: drain x, gate input, source s<side><bit>)."""
    return sorted(set(re.findall(r"^Xt[pn]\S* x[pn] vin[pn] (s[pn]\d+) vss", h, re.M)))


def probe_header(design, corner, vdd, temp, prior_mv, mode, fixed=None):
    h = R._header(design, corner, vdd, temp)
    nodes = float_nodes(h)
    assert nodes, design
    sw = []
    if mode == "short":
        sw = [f"Sprb_{n} {n} sn{n[2:]} prb 0 prbsw" for n in nodes if n.startswith("sp")]
    elif mode in ("self", "transplant"):
        for n in nodes:
            sw += [f"Vfx_{n} fx_{n} 0 {fixed[n]:.12g}", f"Sprb_{n} {n} fx_{n} prb 0 prbsw"]
    else:
        assert mode == "base", mode
    if sw:
        h = h.replace(".subckt atlas", f"{MODEL}\n.global prb\n.subckt atlas", 1)
        h = h.replace(".ends atlas", "\n".join(sw) + "\n.ends atlas")
        h += (f"Vprb prb 0 PWL(0 0 {ON_S:.4e} 0 {ON_S + 1e-11:.4e} 1 {OFF_S:.4e} 1 "
              f"{OFF_S + 1e-11:.4e} 0)\n")
    return R.pin_prior(h, prior_mv), nodes


def _read(args):
    """Floating-node voltages at 21.95 ns (end of the last reset) for a zero last-cycle input."""
    design, corner, vdd, temp, prior_mv = args
    h, nodes = probe_header(design, corner, vdd, temp, prior_mv, "base")
    h += ".save " + " ".join(f"v(xdut.{n})" for n in nodes) + "\n"
    lines = [h, ".control", "set numdgt=12", f"tran 10p {N.NOISE_OFF_S:.4e} 19n {R.TMAX:.3e}"]
    lines += [f"meas tran m_{n} find v(xdut.{n}) at={READ_S:.6e}" for n in nodes]
    lines += [f"echo NODE {n} $&m_{n}" for n in nodes] + ["quit 0", ".endc", ".end"]
    out, _ = N.ngspice_long("\n".join(lines) + "\n")
    vals = dict(re.findall(r"^NODE (\S+) (\S+)", out, re.M))
    assert set(vals) == set(nodes), (args, out[-2000:])
    return {k: float(v) for k, v in vals.items()}


def _thr(args):
    design, corner, vdd, temp, prior_mv, mode, fixed = args
    h, _ = probe_header(design, corner, vdd, temp, prior_mv, mode, fixed)
    lines = [h, ".control", "set numdgt=12"] + R._bisect_block("thr 0", 0.5 * vdd, 0.0, 0.5, 16)
    out, _ = N.ngspice_long("\n".join(lines + ["quit 0", ".endc", ".end"]) + "\n")
    rows = [(float(m), float(d)) for _, _, m, d in re.findall(r"^ISF (\S+) (\S+) (\S+) (\S+)", out, re.M)]
    b, edge = R._resolve(rows, 0.0, 0.5)
    assert not edge, args[:6]
    return b


def _fit(v):
    c = (v["5"] - v["1"]) / 4.0
    return {"decision_uv": (v["1"] - c) * 1e3, "input_carry": c}


def run(designs=DESIGNS, corner="tt", vdd=1.8, temp=27.0, workers=12):
    assert R.PRIOR is None, "run without R24_PRIOR_MV"
    cond = (corner, vdd, temp)
    with ProcessPoolExecutor(workers) as ex:
        rjobs = [(d, *cond, p) for d in designs for p in PRIORS]
        reads = {}
        for job, v in zip(rjobs, ex.map(_read, rjobs)):
            reads.setdefault(job[0], {})[f"{job[4]:g}"] = v
        jobs = []
        for d in designs:
            for p in PRIORS:
                jobs += [(d, *cond, p, "base", None), (d, *cond, p, "short", None),
                         (d, *cond, p, "self", reads[d][f"{p:g}"]),
                         (d, *cond, p, "transplant", reads[d][f"{-p:g}"])]
        thr = {}
        for job, b in zip(jobs, ex.map(_thr, jobs)):
            thr.setdefault(job[0], {}).setdefault(job[5], {})[f"{job[4]:g}"] = b
    res = {"condition": list(cond), "window_ns": [ON_S * 1e9, OFF_S * 1e9], "nodes_v": reads, "threshold_mv": thr,
           "fit": {d: {m: _fit(v) for m, v in thr[d].items()} for d in thr}}
    for d in designs:
        dv = {n: reads[d]["5"][n] - reads[d]["-5"][n] for n in reads[d]["5"]}
        res.setdefault("node_split_mv", {})[d] = {n: v * 1e3 for n, v in dv.items()}
    R.OUT.mkdir(parents=True, exist_ok=True)
    (R.OUT / "memory_probe.json").write_text(json.dumps(res, indent=1))
    for d in designs:
        print(d, {m: round(f["decision_uv"], 2) for m, f in res["fit"][d].items()},
              {m: round(f["input_carry"] * 100, 3) for m, f in res["fit"][d].items()}, flush=True)
    return res


def _mos(name, d, g, s, b, kind, w=0.42, l=0.15):
    return (f"{name} {d} {g} {s} {b} sky130_fd_pr__{kind}_01v8\n+ w={{{w}}} l={l}\n"
            f"+ ad={{0.29*({w})}} as={{0.29*({w})}}\n+ pd={{2*(0.29+({w}))}} ps={{2*(0.29+({w}))}}")


def precharge(h):
    """Drop-in memory fix: a minimum PMOS (gate clk, like Xrxp) precharges every floating trim node to VDD in reset."""
    pc = [_mos(f"Xpc_{n}", n, "clk", "vdd", "vdd", "pfet") for n in float_nodes(h)]
    return h.replace(".ends atlas", "\n".join(pc) + "\n.ends atlas")


def equalize(h):
    """Drop-in memory fix without supply charge: a minimum NMOS per bit shorts sp<k> to sn<k> during reset
    (gate clkb from one minimum inverter, included). This is the 'short' probe built from real devices."""
    nodes = float_nodes(h)
    eq = [_mos("Xeqi_p", "clkb", "clk", "vdd", "vdd", "pfet"), _mos("Xeqi_n", "clkb", "clk", "vss", "vss", "nfet")]
    eq += [_mos(f"Xeq_{n[2:]}", n, "clkb", "sn" + n[2:], "vss", "nfet") for n in nodes if n.startswith("sp")]
    return h.replace(".ends atlas", "\n".join(eq) + "\n.ends atlas")


def variant_header(design, corner, vdd, temp, variant):
    h = R._header(design, corner, vdd, temp)
    if variant == "precharge":
        return precharge(h)
    if variant == "equalize":
        return equalize(h)
    return R._variant(h, design, None if variant == "original" else variant)


def pins_of(code, bits):
    """Signed trim code -> pins driven to VDD (positive: p side, negative: n side)."""
    side = "p" if code > 0 else "n"
    return tuple(f"Vt{side}{k}" for k in range(bits) if abs(int(code)) >> k & 1)


def _thr_variant(args):
    design, corner, vdd, temp, prior_mv, variant, code, bits, span_mv, steps = args
    h = variant_header(design, corner, vdd, temp, variant)
    lines = [R.pin_prior(h, prior_mv), ".control", "set numdgt=12"]
    lines += [f"alter {p} {vdd:g}" for p in pins_of(code, bits)]
    lines += R._bisect_block("thr 0", 0.5 * vdd, 0.0, span_mv, steps) + ["quit 0", ".endc", ".end"]
    out, _ = N.ngspice_long("\n".join(lines) + "\n")
    rows = [(float(m), float(d)) for _, _, m, d in re.findall(r"^ISF (\S+) (\S+) (\S+) (\S+)", out, re.M)]
    b, edge = R._resolve(rows, 0.0, span_mv)
    return None if edge else b


VARIANTS = ("original", "swap", "precharge", "equalize")
FIXES = ("original", "precharge", "equalize")
TRANSFER_CONDS = (("tt", 1.8, 27.0), ("ss", 1.62, -40.0), ("fs", 1.62, -40.0))


def qualify(design="lvt_balanced_4b", bits=4, workers=12, variants=VARIANTS):
    """Memory fix candidates vs the shipped trim: decision memory (TT), full code transfer at the r7
    conditions (max step, DNL, monotonicity) and the r22 half-range at the 45 PVT conditions. Variants
    already in out/r24/memory_fix_<design>.json are kept (merge)."""
    assert R.PRIOR is None, "run without R24_PRIOR_MV"
    top = 2 ** bits - 1
    tt = ("tt", 1.8, 27.0)
    mem_jobs = [(design, *tt, p, v, 0, bits, 0.5, 16) for v in variants for p in PRIORS]
    tr_jobs = [(design, *c, -5.0, v, k, bits, 150.0, 24) for v in variants for c in TRANSFER_CONDS
               for k in range(-top, top + 1)]
    rng_jobs = [(design, *c, -5.0, v, k, bits, 150.0, 24) for v in variants for c in R.conditions()
                for k in (-top, 0, top) if c not in TRANSFER_CONDS]
    path = R.OUT / f"memory_fix_{design}.json"
    res = json.loads(path.read_text()) if path.exists() else {"design": design, "memory": {}, "transfer_mv": {}}
    with ProcessPoolExecutor(workers) as ex:
        mem = {}
        for j, b in zip(mem_jobs, ex.map(_thr_variant, mem_jobs)):
            mem.setdefault(j[5], {})[f"{j[4]:g}"] = b
        res["memory"].update({v: {"threshold_mv": m, **_fit(m)} for v, m in mem.items()})
        print({v: round(m["decision_uv"], 2) for v, m in res["memory"].items()}, flush=True)
        tr = {}
        for j, b in zip(tr_jobs + rng_jobs, ex.map(_thr_variant, tr_jobs + rng_jobs)):
            tr.setdefault(j[5], {}).setdefault(f"{j[1]} {j[2]:g} {j[3]:g}", {})[str(j[6])] = b
    res["transfer_mv"].update(tr)
    res["variants"] = [v for v in VARIANTS if v in res["transfer_mv"]]
    tr = res["transfer_mv"]
    summ = {}
    for v, conds in tr.items():
        s = {"transfer": {}, "half_range_mv": {}}
        for c, codes in conds.items():
            lo, mid, hi = codes.get(str(-top)), codes.get("0"), codes.get(str(top))
            s["half_range_mv"][c] = None if None in (lo, mid, hi) else min(abs(hi - mid), abs(mid - lo))
            if len(codes) == 2 * top + 1 and None not in codes.values():
                y = [codes[str(k)] for k in range(-top, top + 1)]
                st = [b - a for a, b in zip(y, y[1:])]
                lsb = (y[-1] - y[0]) / (2 * top)
                s["transfer"][c] = {"lsb_mv": lsb, "max_step_mv": max(st, key=abs),
                                    "dnl_max_lsb": max(abs(x / lsb - 1) for x in st),
                                    "monotonic": all(x * lsb > 0 for x in st)}
        hr = [x for x in s["half_range_mv"].values() if x is not None]
        s["half_range_min_median_max"] = [min(hr), float(sorted(hr)[len(hr) // 2]), max(hr)] if hr else None
        s["edge_failures"] = sum(x is None for x in s["half_range_mv"].values())
        summ[v] = s
    res["summary"] = summ
    path.write_text(json.dumps(res, indent=1))
    for v, s in summ.items():
        print(v, s["half_range_min_median_max"], s["edge_failures"],
              {c: {k: (round(x, 3) if isinstance(x, float) else x) for k, x in t.items()}
               for c, t in s["transfer"].items()}, flush=True)
    return res


def spot(design="unit6_w6", bits=6, workers=12):
    """Light check for large trims: decision memory (TT) plus codes -top, -1, 0, +1, +top at the r7 conditions
    (LSB = code +1 step, half range). Writes out/r24/memory_spot_<design>.json."""
    assert R.PRIOR is None, "run without R24_PRIOR_MV"
    top = 2 ** bits - 1
    tt = ("tt", 1.8, 27.0)
    mem_jobs = [(design, *tt, p, v, 0, bits, 0.5, 16) for v in FIXES for p in PRIORS]
    jobs = [(design, *c, -5.0, v, k, bits, 150.0, 24) for v in FIXES for c in TRANSFER_CONDS
            for k in (-top, -1, 0, 1, top)]
    with ProcessPoolExecutor(workers) as ex:
        mem, tr = {}, {}
        for j, b in zip(mem_jobs, ex.map(_thr_variant, mem_jobs)):
            mem.setdefault(j[5], {})[f"{j[4]:g}"] = b
        for j, b in zip(jobs, ex.map(_thr_variant, jobs)):
            tr.setdefault(j[5], {}).setdefault(f"{j[1]} {j[2]:g} {j[3]:g}", {})[str(j[6])] = b
    summ = {v: {c: {"lsb_mv": k["1"] - k["0"], "lsb_n_mv": k["0"] - k["-1"],
                    "half_range_mv": min(abs(k[str(top)] - k["0"]), abs(k["0"] - k[str(-top)]))}
                for c, k in conds.items() if None not in k.values()} for v, conds in tr.items()}
    res = {"design": design, "bits": bits, "memory": {v: {"threshold_mv": m, **_fit(m)} for v, m in mem.items()},
           "codes_mv": tr, "summary": summ}
    (R.OUT / f"memory_spot_{design}.json").write_text(json.dumps(res, indent=1))
    print({v: round(m["decision_uv"], 2) for v, m in res["memory"].items()}, flush=True)
    for v, s in summ.items():
        print(v, {c: {k: round(x, 3) for k, x in t.items()} for c, t in s.items()}, flush=True)
    return res


def _energy(args):
    """Energy (fJ) per comparison from VDD over one full cycle (12-22 ns) and charge x VDD drawn from the
    clock source on its rising edge (clock-buffer energy)."""
    design, corner, vdd, temp, variant, code, bits = args
    h = variant_header(design, corner, vdd, temp, variant)
    lines = [R.pin_prior(h, -5.0) + ".save i(vclk)\n", ".control", "set numdgt=12"]
    lines += [f"alter {p} {vdd:g}" for p in pins_of(code, bits)]
    lines += [f"tran 2p 22n 0 {R.TMAX:.3e}", "meas tran qd integ i(vdd) from=12n to=22n",
              "meas tran qc integ i(vclk) from=11.9n to=12.6n", "echo EN $&qd $&qc", "quit 0", ".endc", ".end"]
    out, _ = N.ngspice_long("\n".join(lines) + "\n")
    qd, qc = map(float, re.search(r"^EN (\S+) (\S+)", out, re.M).groups())
    return {"vdd_fj": -qd * vdd * 1e15, "clk_fj": -qc * vdd * 1e15}


def energy(design="lvt_balanced_4b", bits=4, workers=12):
    top = 2 ** bits - 1
    jobs = [(design, "tt", 1.8, 27.0, v, k, bits) for v in FIXES for k in (0, top, -top)]
    with ProcessPoolExecutor(workers) as ex:
        res = {f"{j[4]} {j[5]}": e for j, e in zip(jobs, ex.map(_energy, jobs))}
    path = R.OUT / f"memory_energy_{design}.json"
    path.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1), flush=True)
    return res


if __name__ == "__main__":
    cmd, rest = (ARGS[0], ARGS[1:]) if ARGS else ("run", [])
    if cmd == "run":
        run(tuple(rest) or DESIGNS)
    elif cmd == "energy":
        energy(*(rest[:1] or ["lvt_balanced_4b"]), *[int(x) for x in rest[1:2]])
    elif cmd == "spot":
        spot(*(rest[:1] or ["unit6_w6"]), *[int(x) for x in rest[1:2]])
    elif cmd == "qualify":
        qualify(*(rest[:1] or ["lvt_balanced_4b"]), *[int(x) for x in rest[1:2]],
                variants=tuple(rest[2:]) or VARIANTS)
    else:
        raise SystemExit(__doc__)
