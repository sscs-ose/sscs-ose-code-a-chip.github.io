"""Viaduct ngspice runner: batch simulation -> parsed .raw -> JSON metrics.

ngspice has no GUI to tap, so it runs as a batch job (the open-source
counterpart of a Spectre run from Maestro). Runs inside the container.

Each run gets its own directory under /foss/designs/viaduct/runs/sim_<id>/
holding the netlist copy, ngspice.log, every .raw file the run wrote,
metrics.json and a plot (bode.png / tran.png).
"""
import glob
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import time

import numpy as np

RUNS_DIR = "/foss/designs/viaduct/runs"


# ---- .raw parser (ngspice binary and ascii) --------------------------------

def parse_raw(path):
    """Return a list of plots: {title, plotname, flags, vars, data{name: ndarray}}."""
    plots = []
    with open(path, "rb") as f:
        blob = f.read()
    pos = 0
    while pos < len(blob):
        header = {}
        variables = []
        while True:
            end = blob.index(b"\n", pos)
            line = blob[pos:end].decode("latin-1")
            pos = end + 1
            key, _, value = line.partition(":")
            key = key.strip().lower()
            if key == "variables":
                for _ in range(int(header["no. variables"])):
                    end = blob.index(b"\n", pos)
                    parts = blob[pos:end].decode("latin-1").split()
                    pos = end + 1
                    variables.append((parts[1], parts[2] if len(parts) > 2 else ""))
            elif key in ("binary", "values"):
                header["format"] = key
                break
            else:
                header[key] = value.strip()
        nvars, npts = len(variables), int(header["no. points"])
        is_complex = "complex" in header.get("flags", "").lower()
        if header["format"] == "binary":
            width = 16 if is_complex else 8
            count = nvars * npts * (2 if is_complex else 1)
            raw = np.frombuffer(blob, dtype="<f8", count=count, offset=pos)
            pos += nvars * npts * width
            raw = raw.reshape(npts, nvars, 2) if is_complex else raw.reshape(npts, nvars)
            values = raw[..., 0] + 1j * raw[..., 1] if is_complex else raw
        else:
            rows = []
            text = blob[pos:].decode("latin-1").split("\n")
            consumed = 0
            tokens = []
            for consumed, line in enumerate(text):
                if line.strip() == "" and len(tokens) >= nvars * npts:
                    break
                for tok in line.split()[(1 if re.match(r"^\s*\d+\s", line) else 0):]:
                    tokens.append(complex(*map(float, tok.split(","))) if "," in tok else float(tok))
                if len(tokens) >= nvars * npts:
                    break
            pos += len("\n".join(text[:consumed + 1])) + 1
            values = np.array(tokens[:nvars * npts]).reshape(npts, nvars)
        data = {name: values[:, i] for i, (name, _) in enumerate(variables)}
        plots.append({"title": header.get("title", ""), "plotname": header.get("plotname", ""),
                      "flags": header.get("flags", ""), "points": npts,
                      "vars": [{"name": n, "type": t} for n, t in variables], "data": data})
        while pos < len(blob) and blob[pos:pos + 1] in (b"\n", b"\r"):
            pos += 1
    return plots


# ---- metrics -----------------------------------------------------------------

def find_vector(data, node):
    want = node.lower()
    for name in data:
        n = name.lower()
        if n == want or n == "v(%s)" % want or (want.startswith("v(") and n == want[2:-1]):
            return name
    return None


def _crossing(x, y, level, falling=True):
    """First log-x interpolated crossing of y through level, or None."""
    for i in range(1, len(y)):
        a, b = y[i - 1] - level, y[i] - level
        if (a >= 0 > b) if falling else (a <= 0 < b):
            t = a / (a - b)
            return float(10 ** (np.log10(x[i - 1]) + t * (np.log10(x[i]) - np.log10(x[i - 1]))))
    return None


def ac_metrics(freq, h):
    mag = 20 * np.log10(np.maximum(np.abs(h), 1e-300))
    phase = np.degrees(np.unwrap(np.angle(h)))
    a0 = float(mag[0])
    ipk = int(np.argmax(mag))
    f3 = _crossing(freq, mag, a0 - 3)
    ugf = _crossing(freq, mag, 0.0) if a0 > 0 else None
    out = {"f_start_hz": float(freq[0]), "f_stop_hz": float(freq[-1]),
           "dc_gain_db": round(a0, 4), "dc_gain_vv": round(float(np.abs(h[0])), 6),
           "dc_phase_deg": round(float(phase[0]), 3),
           "peak_db": round(float(mag[ipk]), 4), "f_peak_hz": float(freq[ipk]),
           "peaking_db": round(float(mag[ipk]) - a0, 4),
           "f3db_hz": f3, "ugf_hz": ugf}
    if f3:
        out["gbw_hz"] = float(np.abs(h[0]) * f3)
    if ugf:
        out["phase_at_ugf_deg"] = round(float(np.interp(np.log10(ugf), np.log10(freq), phase)), 3)
    return out


def tran_metrics(t, v):
    v = np.real(v)
    return {"t_stop_s": float(t[-1]), "min": float(v.min()), "max": float(v.max()),
            "final": float(v[-1]), "pk_pk": float(v.max() - v.min())}


def summarize(plots, nodes):
    """Metrics per plot: AC/tran metrics for the requested nodes, op values in full."""
    summary = []
    for p in plots:
        kind = p["plotname"].lower()
        entry = {"plot": p["plotname"], "points": p["points"],
                 "vectors": [v["name"] for v in p["vars"]]}
        data = p["data"]
        scale = p["vars"][0]["name"]
        if "ac" in kind:
            freq = np.real(data[scale])
            entry["nodes"] = {}
            for node in nodes:
                name = find_vector(data, node)
                entry["nodes"][node] = ac_metrics(freq, data[name]) if name else "not saved"
        elif "transient" in kind:
            entry["nodes"] = {}
            for node in nodes:
                name = find_vector(data, node)
                entry["nodes"][node] = tran_metrics(np.real(data[scale]), data[name]) if name else "not saved"
        elif "operating point" in kind or kind.startswith("op"):
            entry["values"] = {k: float(np.real(v[0])) for k, v in data.items()}
        summary.append(entry)
    return summary


def plot(plots, nodes, run_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    written = []
    for p in plots:
        kind = p["plotname"].lower()
        data = p["data"]
        scale = np.real(data[p["vars"][0]["name"]])
        series = [(n, data[find_vector(data, n)]) for n in nodes if find_vector(data, n)]
        if not series:
            continue
        if "ac" in kind:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
            for n, h in series:
                ax1.semilogx(scale, 20 * np.log10(np.abs(h)), label=n)
                ax2.semilogx(scale, np.degrees(np.unwrap(np.angle(h))), label=n)
            ax1.set_ylabel("Magnitude (dB)")
            ax2.set_ylabel("Phase (deg)")
            ax2.set_xlabel("Frequency (Hz)")
            ax1.legend()
            for ax in (ax1, ax2):
                ax.grid(True, which="both", alpha=.3)
            name = "bode.png"
        elif "transient" in kind:
            fig, ax1 = plt.subplots(figsize=(8, 4))
            for n, v in series:
                ax1.plot(scale, np.real(v), label=n)
            ax1.set_xlabel("Time (s)")
            ax1.set_ylabel("V")
            ax1.legend()
            ax1.grid(True, alpha=.3)
            name = "tran.png"
        else:
            continue
        fig.suptitle(os.path.basename(run_dir) + " - " + p["plotname"])
        fig.tight_layout()
        path = os.path.join(run_dir, name)
        fig.savefig(path, dpi=110)
        plt.close(fig)
        written.append(path)
    return written


# ---- xschem graphs ----------------------------------------------------------

def graph_records(result, nodes, box):
    """xschem graph records for the first AC (magnitude + phase) or tran plot of a run."""
    x0, y0, w, h = box
    for entry in result["raw_files"]:
        for plot in parse_raw(entry["raw"]):
            kind = plot["plotname"].lower()
            data = plot["data"]
            names = [(n, find_vector(data, n)) for n in nodes]
            names = [(n, v) for n, v in names if v]
            if not names or not ("ac" in kind or "transient" in kind):
                continue
            scale = np.real(data[plot["vars"][0]["name"]])
            colors = " ".join(str(4 + i) for i in range(len(names)))
            common = "ypos1=0\nypos2=2\ndivy=5\nsubdivy=1\nunity=1\ndivx=5\nsubdivx=8\ndataset=-1\nunitx=1\nlogy=0\nviaduct=1\n"
            if "ac" in kind:
                mag = np.concatenate([20 * np.log10(np.abs(data[v])) for _, v in names])
                ph = np.concatenate([np.degrees(np.unwrap(np.angle(data[v]))) for _, v in names])
                x1, x2 = np.log10(scale[0]), np.log10(scale[-1])
                mag_nodes = "\n".join('\\\\"dB(%s); %s db20()\\\\"' % (n, n) for n, _ in names)
                ph_nodes = "\n".join('\\\\"ph(%s); ph(%s)\\\\"' % (n, n) for n, _ in names)
                recs = [("ac", mag_nodes, np.floor(mag.min() / 10) * 10 - 5, np.ceil(mag.max() / 10) * 10 + 5, y0),
                        ("ac", ph_nodes, np.floor(ph.min() / 45) * 45, np.ceil(ph.max() / 45) * 45, y0 + h + 20)]
                logx = 1
            else:
                v = np.concatenate([np.real(data[v]) for _, v in names])
                pad = 0.05 * (v.max() - v.min() or 1)
                x1, x2 = scale[0], scale[-1]
                recs = [("tran", "\n".join(n for n, _ in names), v.min() - pad, v.max() + pad, y0)]
                logx = 0
            text = ""
            for _, node_expr, ylo, yhi, top in recs:
                text += ("B 2 %g %g %g %g {flags=graph\ny1=%g\ny2=%g\nx1=%g\nx2=%g\nlogx=%d\n"
                         'node="%s"\ncolor="%s"\n%s}\n') % (
                    x0, top, x0 + w, top + h, ylo, yhi, x1, x2, logx, node_expr, colors, common)
            return entry["raw"], ("ac" if "ac" in kind else "tran"), text
    return None


# ---- run -----------------------------------------------------------------------

def ensure_write(text):
    """A .control block that runs analyses but writes nothing leaves no results to parse:
    add `write auto.raw` (all vectors of every analysis) before its last .endc.
    Returns (text, added)."""
    blocks = re.findall(r"^\s*\.control\b(.*?)^\s*\.endc\b", text, re.S | re.M | re.I)
    if not blocks or any(re.search(r"^\s*write\b", b, re.M | re.I) for b in blocks):
        return text, False
    ends = list(re.finditer(r"^\s*\.endc\b", text, re.M | re.I))
    i = ends[-1].start()
    return text[:i] + "write auto.raw\n" + text[i:], True


def run(netlist, nodes=("out",), pdk="sky130A", timeout=300, plots=True):
    if not os.path.isfile(netlist):
        raise FileNotFoundError(netlist)
    run_id = time.strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    run_dir = os.path.join(RUNS_DIR, "sim_" + run_id)
    os.makedirs(run_dir)
    local = os.path.join(run_dir, os.path.basename(netlist))
    # The netlist's .control block decides what is simulated and written. Without
    # one, -r makes ngspice write every analysis to out.raw; with one that writes
    # nothing, `write auto.raw` is added to the run copy (the original is untouched).
    text, added_write = ensure_write(open(netlist, errors="replace").read())
    with open(local, "w") as f:
        f.write(text)
    has_control = re.search(r"^\s*\.control", text, re.M | re.I)
    cmd = "ngspice -b %s%s" % ("" if has_control else "-r out.raw ", os.path.basename(local))
    script = "source /foss/tools/sak/sak-pdk-script.sh %s >/dev/null; cd %s; %s" % (pdk, run_dir, cmd)
    t0 = time.time()
    proc = subprocess.run(["bash", "-lc", script], capture_output=True, text=True, timeout=timeout)
    seconds = round(time.time() - t0, 2)
    log = "\n".join(l for l in (proc.stdout + proc.stderr).splitlines() if not l.startswith("[INFO]"))
    with open(os.path.join(run_dir, "ngspice.log"), "w") as f:
        f.write(log)
    errors = [l for l in log.splitlines() if re.match(r"^\s*(error|fatal)", l, re.I)]
    raws = sorted(glob.glob(os.path.join(run_dir, "*.raw")))
    all_plots, results = [], []
    for raw in raws:
        parsed = parse_raw(raw)
        all_plots += parsed
        results.append({"raw": raw, "plots": summarize(parsed, nodes)})
    images = plot(all_plots, nodes, run_dir) if plots and all_plots else []
    ok = proc.returncode == 0 and not errors and bool(raws)
    result = {"run_id": run_id, "run_dir": run_dir, "status": "COMPLETE" if ok else "FAILED",
              "engine": "ngspice", "pdk": pdk, "netlist": local, "command": cmd,
              "exit_code": proc.returncode, "seconds": seconds, "errors": errors[:20],
              "raw_files": results, "images": images,
              "log_tail": log.splitlines()[-15:]}
    if added_write:
        result["note"] = "the .control block wrote no results; `write auto.raw` was added to the run copy"
    zero_ac = sorted({n for r in results for p in r["plots"] for n, m in (p.get("nodes") or {}).items()
                      if isinstance(m, dict) and m.get("dc_gain_vv") == 0.0 and "f3db_hz" in m})
    if zero_ac:
        result["warnings"] = ["AC response of %s is exactly zero: no source in the netlist has an `ac` "
                              "magnitude (e.g. `VINP INP 0 dc 0.9 ac 1`)" % ", ".join(zero_ac)]
    with open(os.path.join(run_dir, "metrics.json"), "w") as f:
        json.dump(result, f, indent=2)
    return result


# ---- operating point per device ------------------------------------------------------

OP_QUANTITIES = ("id", "gm", "gds", "vgs", "vds", "vth", "vdsat")
FET = re.compile(r"^(x\S+)\s.*?\s(sky130_fd_pr__([np])fet_\w+)\b", re.I)


def _logical_lines(text):
    """Netlist lines with '+' continuations joined."""
    out = []
    for line in text.splitlines():
        if line.startswith("+") and out:
            out[-1] += " " + line[1:].strip()
        else:
            out.append(line)
    return out


def op_devices(text):
    """Top-level SKY130 MOSFET instances: [(name, internal device path, 'n'|'p')]."""
    devices, depth = [], 0
    for line in _logical_lines(text):
        s = line.strip().lower()
        if s.startswith(".subckt"):
            depth += 1
        elif s.startswith(".ends"):
            depth = max(0, depth - 1)
        elif depth == 0:
            m = FET.match(line.strip())
            if m:
                inst, model, kind = m.group(1), m.group(2), m.group(3).lower()
                devices.append((inst[1:], "@m.%s.m%s" % (inst.lower(), model.lower()), kind))
    return devices


def op_control(devices):
    lines = [".control", "set noaskquit", "op", "print all"]
    for _, path, _ in devices:
        lines.append("print " + " ".join("%s[%s]" % (path, q) for q in OP_QUANTITIES))
    return lines + [".endc"]


def parse_op_log(log, devices):
    """'name = value' lines from `print` -> node voltages and per-device quantities."""
    values = {}
    for line in log.splitlines():
        m = re.match(r"^\s*(\S+)\s*=\s*([-+0-9.eE]+)\s*$", line)
        if m:
            values[m.group(1).lower()] = float(m.group(2))
    # circuit nodes and source branch currents; not the models' internal m.x...#body nodes
    nodes = {k: v for k, v in values.items() if not k.startswith(("@", "m."))}
    report, warnings = {}, []
    for name, path, kind in devices:
        q = {k: values.get("%s[%s]" % (path, k)) for k in OP_QUANTITIES}
        if any(v is None for v in q.values()):
            report[name] = {"error": "not in the op output"}
            continue
        vov = abs(q["vgs"]) - abs(q["vth"])
        margin = abs(q["vds"]) - abs(q["vdsat"])
        region = "triode" if margin < 0 else ("saturation, edge" if margin < 0.05 else "saturation")
        d = {"type": "nmos" if kind == "n" else "pmos", "id_ua": round(abs(q["id"]) * 1e6, 3),
             "vgs": round(abs(q["vgs"]), 4), "vds": round(abs(q["vds"]), 4), "vth": round(abs(q["vth"]), 4),
             "vov": round(vov, 4), "vdsat": round(abs(q["vdsat"]), 4), "vds_margin": round(margin, 4),
             "gm_us": round(q["gm"] * 1e6, 3), "gds_us": round(q["gds"] * 1e6, 4),
             "gm_id": round(q["gm"] / abs(q["id"]), 2) if q["id"] else None,
             "intrinsic_gain": round(q["gm"] / q["gds"], 1) if q["gds"] else None,
             "region": region, "inversion": "weak" if vov < 0 else ("moderate" if vov < 0.1 else "strong")}
        report[name] = d
        if margin < 0.05:
            warnings.append("%s: %s (|Vds| %.3f V vs Vdsat %.3f V)" % (name, region, d["vds"], d["vdsat"]))
    return nodes, report, warnings


def op(netlist, pdk="sky130A", timeout=300):
    """DC operating point of every top-level SKY130 MOSFET: Id, gm, gds, Vgs, Vds, Vth, Vdsat,
    the |Vds| - Vdsat margin and the region. The netlist's own .control block is replaced."""
    if not os.path.isfile(netlist):
        raise FileNotFoundError(netlist)
    text = open(netlist, errors="replace").read()
    devices = op_devices(text)
    text = re.sub(r"^\s*\.control\b.*?^\s*\.endc\b[^\n]*\n?", "", text, flags=re.S | re.M | re.I)
    text = re.sub(r"^\s*\.end\s*$", "", text, flags=re.M | re.I).rstrip() + "\n"
    run_id = time.strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    run_dir = os.path.join(RUNS_DIR, "op_" + run_id)
    os.makedirs(run_dir)
    with open(os.path.join(run_dir, "op.spice"), "w") as f:
        f.write(text + "\n".join(op_control(devices)) + "\n.end\n")
    script = "source /foss/tools/sak/sak-pdk-script.sh %s >/dev/null; cd %s; ngspice -b op.spice" % (pdk, run_dir)
    t0 = time.time()
    proc = subprocess.run(["bash", "-lc", script], capture_output=True, text=True, timeout=timeout)
    log = "\n".join(l for l in (proc.stdout + proc.stderr).splitlines() if not l.startswith("[INFO]"))
    with open(os.path.join(run_dir, "ngspice.log"), "w") as f:
        f.write(log)
    nodes, report, warnings = parse_op_log(log, devices)
    errors = [l for l in log.splitlines() if re.match(r"^\s*(error|fatal)", l, re.I)]
    ok = proc.returncode == 0 and not errors and bool(report) and all("error" not in d for d in report.values())
    result = {"run_id": run_id, "run_dir": run_dir, "status": "COMPLETE" if ok else "FAILED",
              "engine": "ngspice", "pdk": pdk, "netlist": netlist, "seconds": round(time.time() - t0, 2),
              "devices": report, "nodes": nodes, "warnings": warnings, "errors": errors[:20],
              "log_tail": log.splitlines()[-10:]}
    with open(os.path.join(run_dir, "op.json"), "w") as f:
        json.dump(result, f, indent=2)
    return result


# ---- parameter sweep (one ngspice process) -------------------------------------------

def sweep(netlist, params=None, node="out", pdk="sky130A", fixed=None, cases=None,
          ac="dec 40 1e8 2e11", timeout=1800, plot_cases=True):
    """AC metrics of `node` for many .param combinations in one ngspice run.

    params: {name: [values]} -> full grid;  cases: [{"label":..., name: value, ...}] -> explicit points.
    fixed:  {name: value} applied to every point. The netlist's own .control block is
    replaced by: alterparam ... ; reset ; ac <ac> ; wrdata pt_<i>.txt v(node).
    Every swept or fixed name must be a .param of the netlist.
    """
    import itertools
    if cases is None:
        names = list(params)
        cases = [dict(zip(names, combo)) for combo in itertools.product(*(params[n] for n in names))]
    cases = [dict(c) for c in cases]
    fixed = fixed or {}
    run_id = time.strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    run_dir = os.path.join(RUNS_DIR, "sweep_" + run_id)
    os.makedirs(os.path.join(run_dir, "pts"))
    text = open(netlist, errors="replace").read()
    text = re.sub(r"^\s*\.control\b.*?^\s*\.endc\b[^\n]*\n?", "", text, flags=re.S | re.M | re.I)
    text = re.sub(r"^\s*\.end\s*$", "", text, flags=re.M | re.I).rstrip() + "\n"
    defaults = {}
    for line in re.findall(r"^\s*\.param\s+(.*)$", text, re.M | re.I):
        for n, v in re.findall(r"(\w+)\s*=\s*(\S+)", line):
            defaults[n.lower()] = v
    declared = set(defaults)
    for name in set(fixed) | {k for c in cases for k in c if k != "label"}:
        if name.lower() not in declared:
            raise ValueError(".param %s is not declared in %s" % (name, netlist))
    ctl = [".control", "set noaskquit"]
    for k, v in fixed.items():
        ctl.append("alterparam %s=%s" % (k, v))
    # alterparam values persist from one case to the next: give every case the full set
    # of swept names, unspecified ones at their netlist default (or the fixed value).
    swept = sorted({k for c in cases for k in c if k != "label"})
    for i, case in enumerate(cases):
        for k in swept:
            v = case.get(k, fixed.get(k, defaults[k.lower()]))
            ctl.append("alterparam %s=%s" % (k, v))
        ctl += ["reset", "ac %s" % ac, "wrdata pts/pt_%d.txt v(%s)" % (i, node)]
    ctl += [".endc", ".end"]
    local = os.path.join(run_dir, "sweep.spice")
    with open(local, "w") as f:
        f.write(text + "\n".join(ctl) + "\n")
    script = "source /foss/tools/sak/sak-pdk-script.sh %s >/dev/null; cd %s; ngspice -b sweep.spice" % (pdk, run_dir)
    t0 = time.time()
    proc = subprocess.run(["bash", "-lc", script], capture_output=True, text=True, timeout=timeout)
    log = "\n".join(l for l in (proc.stdout + proc.stderr).splitlines() if not l.startswith("[INFO]"))
    with open(os.path.join(run_dir, "ngspice.log"), "w") as f:
        f.write(log)
    points, curves = [], []
    for i, case in enumerate(cases):
        path = os.path.join(run_dir, "pts", "pt_%d.txt" % i)
        if not os.path.exists(path):
            points.append(dict(case, error="no data"))
            continue
        d = np.loadtxt(path)
        freq, h = d[:, 0], d[:, 1] + 1j * d[:, 2]
        points.append(dict(case, **ac_metrics(freq, h)))
        curves.append((case.get("label", str(i)), freq, h))
    errors = [l for l in log.splitlines() if re.match(r"^\s*(error|fatal)", l, re.I)]
    ok = proc.returncode == 0 and not errors and all("error" not in p for p in points)
    images = []
    if plot_cases and curves and len(curves) <= 8:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for label, freq, h in curves:
            ax.semilogx(freq, 20 * np.log10(np.abs(h)), label=label)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("|v(%s)| (dB)" % node)
        ax.grid(True, which="both", alpha=.3)
        ax.legend(fontsize=8)
        ax.set_title("sweep " + run_id)
        fig.tight_layout()
        images.append(os.path.join(run_dir, "compare.png"))
        fig.savefig(images[0], dpi=110)
        plt.close(fig)
    import csv
    keys = sorted({k for p in points for k in p})
    with open(os.path.join(run_dir, "points.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(points)
    result = {"run_id": run_id, "run_dir": run_dir, "status": "COMPLETE" if ok else "FAILED",
              "engine": "ngspice", "node": node, "ac": ac, "fixed": fixed, "count": len(cases),
              "seconds": round(time.time() - t0, 2), "errors": errors[:20], "points": points,
              "images": images, "log_tail": log.splitlines()[-10:]}
    with open(os.path.join(run_dir, "metrics.json"), "w") as f:
        json.dump(result, f, indent=2, default=str)
    return result
