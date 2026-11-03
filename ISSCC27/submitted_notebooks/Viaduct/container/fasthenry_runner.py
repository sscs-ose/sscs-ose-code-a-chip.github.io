"""Viaduct FastHenry runner: quasi-static L, R, Q, k of the T-coil.

The coil comes from devices/tcoil/tcoil_core.em_model(), i.e. the same
dimensions as the layout: winding centerlines on both parallel planes, the
'high' crossover on the winding metals, the 'low' crossover on every bridge
metal, the 11 inter-plane via sites and the bridge via stacks, and the tap stub.
Metal heights, thicknesses and sheet resistances come from pdk/<pdk>.json.

Two ports, as in the EMX flow: port 1 = P1-P3, port 2 = P2-P3. From the 2x2
impedance matrix Z at each frequency:
    L1 = Im Z11 / w,  R1 = Re Z11,  Q1 = Im Z11 / Re Z11   (same for port 2)
    K1 = Im Z12 / (w sqrt(L1 L2)),  K2 = Im Z21 / (w sqrt(L1 L2))
With these port directions a series-aiding coil has K < 0 (EMX reported
K = -0.38..-0.52 for the generic65 version). For SPICE with L1 from P1 to P3 and
L2 from P3 to P2, use K_spice = -K1.

Limits (state them with results): no substrate, no dielectric, no capacitance
(FastHenry is magneto-quasi-static); via arrays are modelled as solid square
posts; corners are centerline joints. Inter-winding capacitance needs FasterCap
or openEMS.
"""
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS_DIR = os.path.join(ROOT, "runs")
MESH = {"coarse": (1, 1), "normal": (5, 3), "fine": (9, 5)}


def _core(pdk):
    os.environ["VIADUCT_PDK"] = pdk
    import importlib.util
    spec = importlib.util.spec_from_file_location("viaduct_tcoil_core_em",
                                                  os.path.join(ROOT, "devices", "tcoil", "tcoil_core.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- geometry -> FastHenry input -------------------------------------------------

def _on_segment(p, a, b, tol=1e-6):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
    if abs(cross) > tol * max(1.0, math.hypot(x2 - x1, y2 - y1)):
        return False
    dot = (x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)
    return -tol <= dot <= (x2 - x1) ** 2 + (y2 - y1) ** 2 + tol


def build_model(core, params):
    """Paths with via/port points inserted as vertices; returns (paths, vias, ports, profile)."""
    model = core.em_model(core.Parameters(**params))
    paths = [dict(p, points=[tuple(map(float, q)) for q in p["points"]]) for p in model["paths"]]
    needed = [(v["x"], v["y"], v["top"]) for v in model["vias"]] + \
             [(v["x"], v["y"], v["bottom"]) for v in model["vias"]] + \
             [(x, y, m) for x, y, m in model["ports"].values()]
    for x, y, metal in needed:
        pt = (float(x), float(y))
        found = False
        for p in paths:
            if p["metal"] != metal:
                continue
            pts = p["points"]
            if any(math.hypot(pt[0] - q[0], pt[1] - q[1]) < 1e-6 for q in pts):
                found = True
                break
            for i in range(len(pts) - 1):
                if _on_segment(pt, pts[i], pts[i + 1]):
                    pts.insert(i + 1, pt)
                    found = True
                    break
            if found:
                break
        if not found:
            raise ValueError("EM model: point %s on %s is on no conductor path" % (pt, metal))
    return paths, model["vias"], model["ports"], model


def write_inp(path, core, paths, vias, ports, freq_hz, mesh, externals=None, freqs=None):
    """externals: [((x, y, metal), (x, y, metal), name), ...]; default: P1-P3 and P2-P3.
    freqs: (fmin, fmax, ndec) instead of the single freq_hz."""
    prof = core.PROFILE["metals"]
    nw, nh = MESH[mesh]
    nodes = {}
    lines = ["* Viaduct T-coil FastHenry model (units um; sigma in 1/(um*ohm))", ".units um"]

    def z_of(m):
        return prof[m]["z_um"] + prof[m]["thickness_um"] / 2

    def sigma(m):
        return 1.0 / (prof[m]["sheet_ohm"] * prof[m]["thickness_um"] * 1e-6) * 1e-6

    def node(x, y, m):
        key = (round(x, 6), round(y, 6), m)
        if key not in nodes:
            name = "N%d" % (len(nodes) + 1)
            nodes[key] = name
            lines.append("%s x=%.6f y=%.6f z=%.6f" % (name, x, y, z_of(m)))
        return nodes[key]

    seg = 0
    elements = []
    for p in paths:
        m = p["metal"]
        for a, b in zip(p["points"], p["points"][1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-9:
                continue
            seg += 1
            elements.append("E%d %s %s w=%.6f h=%.6f sigma=%.6g nwinc=%d nhinc=%d" % (
                seg, node(a[0], a[1], m), node(b[0], b[1], m), p["width"], prof[m]["thickness_um"],
                sigma(m), nw, nh))
    for v in vias:
        seg += 1
        size = v["size"] * 0.5      # via array ~ half-filled solid post
        top, bot = v["top"], v["bottom"]
        elements.append("E%d %s %s w=%.6f h=%.6f sigma=%.6g wx=1 wy=0 wz=0" % (
            seg, node(v["x"], v["y"], top), node(v["x"], v["y"], bot), size, size, sigma(bot)))
    lines += elements
    if externals is None:
        externals = [(ports["P1"], ports["P3"], "P1_P3"), (ports["P2"], ports["P3"], "P2_P3")]
    for a, b, name in externals:
        lines.append(".external %s %s %s" % (node(*a), node(*b), name))
    fmin, fmax, ndec = freqs or (freq_hz, freq_hz, 1)
    lines += [".freq fmin=%g fmax=%g ndec=%g" % (fmin, fmax, ndec), ".end"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return {"nodes": len(nodes), "segments": seg}


def parse_zc(path):
    """Zc.mat -> list of (freq, [[Z11, Z12], [Z21, Z22]])."""
    out = []
    with open(path) as f:
        text = f.read().splitlines()
    i = 0
    num = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
    while i < len(text):
        m = re.search(r"frequency\s*=\s*(%s)\s+(\d+)\s*x" % num, text[i])
        if m:
            f, n = float(m.group(1)), int(m.group(2))
            rows = []
            for line in text[i + 1:i + 1 + n]:
                vals = re.findall(r"(%s)\s*([-+]\s*%s)j" % (num, num), line)
                rows.append([complex(float(a), float(b.replace(" ", ""))) for a, b in vals])
            out.append((f, rows))
            i += 1 + n
        else:
            i += 1
    return out


def analyse(freq, z):
    w = 2 * math.pi * freq
    (z11, z12), (z21, z22) = z
    l1, l2 = z11.imag / w, z22.imag / w
    root = math.sqrt(l1 * l2) if l1 > 0 and l2 > 0 else float("nan")
    k1, k2 = z12.imag / w / root, z21.imag / w / root
    return {"frequency_hz": freq, "L1_nH": l1 * 1e9, "L2_nH": l2 * 1e9, "R1_ohm": z11.real, "R2_ohm": z22.real,
            "Q1": z11.imag / z11.real, "Q2": z22.imag / z22.real, "K1": k1, "K2": k2,
            "M_nH": z12.imag / w * 1e9,
            "L_series_P1_P2_nH": (z11 + z22 - z12 - z21).imag / w * 1e9}


def _solve(run_dir, core, paths, vias, ports, freq, mesh):
    sub = os.path.join(run_dir, "f_%g" % freq)
    os.makedirs(sub, exist_ok=True)
    stats = write_inp(os.path.join(sub, "tcoil.inp"), core, paths, vias, ports, freq, mesh)
    fh = shutil.which("fasthenry") or "/foss/tools/bin/fasthenry"
    t0 = time.time()
    proc = subprocess.run([fh, "tcoil.inp"], cwd=sub, capture_output=True, text=True, timeout=1800)
    with open(os.path.join(sub, "fasthenry.log"), "w") as f:
        f.write(proc.stdout + proc.stderr)
    zc = os.path.join(sub, "Zc.mat")
    if proc.returncode != 0 or not os.path.exists(zc):
        return {"frequency_hz": freq, "error": (proc.stdout + proc.stderr)[-800:]}, stats
    rows = parse_zc(zc)
    res = analyse(*rows[0])
    res["seconds"] = round(time.time() - t0, 2)
    return res, stats


def plot_model(run_dir, core, params, paths, vias, ports):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 7))
    layout = core.build(core.Parameters(**params))
    for (layer, dt), pts in layout["polygons"]:
        if dt == 20:
            xs, ys = zip(*(pts + [pts[0]]))
            ax.fill(xs, ys, color="#bbbbbb", alpha=.35, lw=0)
    colors = {"met5": "#d62728", "met4": "#1f77b4", "met3": "#2ca02c", "met2": "#9467bd", "met1": "#8c564b"}
    for p in paths:
        xs, ys = zip(*p["points"])
        ax.plot(xs, ys, "-o", ms=2, lw=1.2, color=colors.get(p["metal"], "k"), alpha=.8)
    for v in vias:
        ax.plot(v["x"], v["y"], "s", ms=6, mfc="none", color="k")
    for n, (x, y, _) in ports.items():
        ax.annotate(n, (x, y), color="k", fontsize=11, weight="bold")
    ax.set_aspect("equal")
    ax.set_title("FastHenry model over layout (grey); met5 red, met4 blue, bridges green/purple/brown")
    fig.tight_layout()
    path = os.path.join(run_dir, "model.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def _new_run(prefix):
    run_id = time.strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    run_dir = os.path.join(RUNS_DIR, "%s_%s" % (prefix, run_id))
    os.makedirs(run_dir)
    return run_id, run_dir


def run(params, freqs_hz=(1e9, 5e9, 10e9, 20e9), pdk="sky130A", mesh="normal", ref_freq_hz=10e9):
    core = _core(pdk)
    params = {k: v for k, v in (params or {}).items() if k in core.Parameters.__dataclass_fields__}
    run_id, run_dir = _new_run("em")
    paths, vias, ports, model = build_model(core, params)
    with ThreadPoolExecutor(max_workers=max(1, min(len(freqs_hz), os.cpu_count() or 2))) as ex:
        solved = list(ex.map(lambda f: _solve(run_dir, core, paths, vias, ports, f, mesh), freqs_hz))
    results = [r for r, _ in solved]
    stats = solved[0][1]
    ok = [r for r in results if "error" not in r]
    image = plot_model(run_dir, core, params, paths, vias, ports)
    out = {"run_id": run_id, "run_dir": run_dir, "engine": "fasthenry", "pdk": pdk, "mesh": mesh,
           "status": "COMPLETE" if len(ok) == len(results) else "FAILED",
           "parameters": model["parameters"], "bbox_um": model["bbox"],
           "actualTurnSpacing": model["actualTurnSpacing"], "model": stats,
           "ports": "port1 = P1-P3, port2 = P2-P3; K<0 is series-aiding with these directions; K_spice = -K1",
           "results": results, "images": [image],
           "limits": "quasi-static: no substrate, dielectric or capacitance; via arrays as solid posts"}
    if ok:
        ref = min(ok, key=lambda r: abs(math.log(r["frequency_hz"] / ref_freq_hz)))
        out["reference"] = ref
        out["annotation"] = {"L1": "%.4f nH" % ref["L1_nH"], "L2": "%.4f nH" % ref["L2_nH"],
                             "Q1": "%.2f" % ref["Q1"], "Q2": "%.2f" % ref["Q2"],
                             "K1": "%.4f" % ref["K1"], "K2": "%.4f" % ref["K2"]}
        out["annotation_note"] = "FastHenry quasi-static at %.3g GHz, run %s" % (ref["frequency_hz"] / 1e9, run_id)
        out["spice_model"] = {"L1_H": ref["L1_nH"] * 1e-9, "R1_ohm": ref["R1_ohm"],
                              "L2_H": ref["L2_nH"] * 1e-9, "R2_ohm": ref["R2_ohm"], "K": -ref["K1"],
                              "at_hz": ref["frequency_hz"],
                              "netlist": "L1 P1 P3, L2 P3 P2 (series R each); K L1 L2 = K"}
    with open(os.path.join(run_dir, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out


def convergence(params, freq_hz=10e9, pdk="sky130A"):
    """Same coil at coarse/normal/fine mesh; percent change of L1, L2, K1, R1 between the last two."""
    runs = {m: run(params, [freq_hz], pdk, m) for m in ("coarse", "normal", "fine")}
    if any(r["status"] != "COMPLETE" for r in runs.values()):
        return {"status": "FAILED", "runs": {m: r["run_id"] for m, r in runs.items()}}
    vals = {m: r["results"][0] for m, r in runs.items()}

    def pct(key):
        a, b = vals["normal"][key], vals["fine"][key]
        return round(abs(b - a) / abs(b) * 100, 3)
    change = {k: pct(k) for k in ("L1_nH", "L2_nH", "K1", "R1_ohm", "R2_ohm")}
    return {"status": "COMPLETE", "frequency_hz": freq_hz,
            "values": {m: {k: v[k] for k in ("L1_nH", "L2_nH", "K1", "R1_ohm", "R2_ohm", "Q1", "seconds")}
                       for m, v in vals.items()},
            "percent_change_normal_to_fine": change,
            "converged_2pct_LK": all(change[k] <= 2.0 for k in ("L1_nH", "L2_nH", "K1")),
            "runs": {m: r["run_id"] for m, r in runs.items()}}


if __name__ == "__main__":
    print(json.dumps(run(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}), indent=2))
