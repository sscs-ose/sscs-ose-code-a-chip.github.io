"""Viaduct FasterCap runner: parasitic capacitances of the T-coil.

The coil (same em_model() geometry as FastHenry: winding segments and via posts as
boxes) is cut at the tap into two conductors:
    A = P1 .. P3  (outer left half, 'high' crossover, inner turn from its right end to the tap)
    B = P3 .. P2  (rest of the inner turn, 'low' crossover, outer right half)
plus the substrate as a grounded plane at z = 0. From the Maxwell matrix:
    C_AB   = -M[A][B]  : distributed bridging capacitance between the two halves
                         (adds to an explicit C_B across the coil)
    C_A0, C_B0 = -M[.][G] : capacitance of each half to the substrate
Lumped use (pi split): X gets C_A0/2, the tap C_A0/2 + C_B0/2, Y gets C_B0/2.

Limits: one homogeneous dielectric (pdk "dielectric_er"), substrate treated as a
perfect ground plane (real Si is resistive: this overestimates the coupling of
the coil to the substrate), boxes overlap at path joints. Estimates, not signoff.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fasthenry_runner as fh  # noqa: E402

UM = 1e-6


def box_panels(name, x1, y1, x2, y2, width, z0, z1):
    """Six quadrilaterals of a box along (x1,y1)-(x2,y2), in metres."""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    c = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
    b = [(x, y, z0) for x, y in c]
    t = [(x, y, z1) for x, y in c]
    faces = [b, t[::-1]] + [[b[i], b[(i + 1) % 4], t[(i + 1) % 4], t[i]] for i in range(4)]
    return ["Q %s %s" % (name, " ".join("%.9g %.9g %.9g" % (x * UM, y * UM, z * UM) for x, y, z in f))
            for f in faces]


def split_groups(core, params):
    paths, vias, ports, model = fh.build_model(core, params)
    tap = (ports["P3"][0], ports["P3"][1])
    tap_root = None
    for p in paths:
        if p["name"] == "tap":
            tap_root = p["points"][0]          # where the tap stub meets the inner turn
    groups = {"A": [], "B": []}
    for p in paths:
        kind = p["name"].split(".")[0]
        if kind in ("left", "high", "tap"):
            groups["A"].append(p)
        elif kind in ("right", "low"):
            groups["B"].append(p)
        elif kind == "inner":
            pts = p["points"]
            i = next(k for k, q in enumerate(pts) if math.hypot(q[0] - tap_root[0], q[1] - tap_root[1]) < 1e-6)
            # Cut a real gap at the tap: two conductors may not share faces or volume
            # (FasterCap crashes on that). B stops w/2 + 0.5 um before the tap, A starts
            # at it (A also owns the tap stub and the tap's via).
            b_pts = list(pts[:i + 1])
            (px, py_), (qx, qy) = b_pts[-2], b_pts[-1]
            seg = math.hypot(qx - px, qy - py_)
            cut = min(p["width"] / 2 + 0.5, seg * 0.5)
            b_pts[-1] = (qx - (qx - px) / seg * cut, qy - (qy - py_) / seg * cut)
            groups["B"].append(dict(p, points=b_pts))           # bridge end .. just before the tap
            groups["A"].append(dict(p, points=pts[i:]))         # tap .. 'high' end
    vgroups = {"A": [], "B": []}
    for v in vias:
        pt = (v["x"], v["y"])
        on_a = any(fh._on_segment(pt, a, b) for p in groups["A"] if p["metal"] in (v["top"], v["bottom"])
                   for a, b in zip(p["points"], p["points"][1:]))
        vgroups["A" if on_a else "B"].append(v)
    return groups, vgroups, model, tap


def write_inputs(run_dir, core, groups, vgroups, bbox, er):
    prof = core.PROFILE["metals"]
    for g in ("A", "B"):
        lines = ["0 coil half %s" % g]
        for p in groups[g]:
            m = prof[p["metal"]]
            for a, b in zip(p["points"], p["points"][1:]):
                if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-9:
                    continue
                lines += box_panels(g, a[0], a[1], b[0], b[1], p["width"], m["z_um"], m["z_um"] + m["thickness_um"])
        # One post per via location: nested posts of a via stack would have coincident
        # faces, which makes the panel matrix singular (FasterCap segfaults).
        posts = {}
        for v in vgroups[g]:
            lo, hi = prof[v["bottom"]], prof[v["top"]]
            key = (round(v["x"], 6), round(v["y"], 6))
            z0, z1 = lo["z_um"] + lo["thickness_um"], hi["z_um"]
            old = posts.get(key, (z0, z1, v["size"] * 0.5))
            posts[key] = (min(old[0], z0), max(old[1], z1), old[2])
        for (x, y), (z0, z1, s) in posts.items():
            lines += box_panels(g, x - s / 2, y, x + s / 2, y, s, z0, z1)
        with open(os.path.join(run_dir, "coil_%s.txt" % g), "w") as f:
            f.write("\n".join(lines) + "\n")
    (x0, y0), (x1, y1) = bbox
    margin = 60.0
    gx0, gy0, gx1, gy1 = (x0 - margin) * UM, (y0 - margin) * UM, (x1 + margin) * UM, (y1 + margin) * UM
    with open(os.path.join(run_dir, "ground.txt"), "w") as f:
        f.write("0 substrate as ground plane\nQ G %.9g %.9g 0 %.9g %.9g 0 %.9g %.9g 0 %.9g %.9g 0\n" % (
            gx0, gy0, gx1, gy0, gx1, gy1, gx0, gy1))
    with open(os.path.join(run_dir, "coil.lst"), "w") as f:
        f.write("* Viaduct T-coil parasitic capacitance; metres; homogeneous er=%g\n" % er)
        for name in ("coil_A.txt", "coil_B.txt", "ground.txt"):
            f.write("C %s %g 0 0 0\n" % (name, er))


def parse_matrix(text):
    blocks = re.findall(r"Capacitance matrix is:\s*\nDimension (\d+) x \d+\s*\n((?:.*\n){1,10})", text)
    if not blocks:
        return None, None
    n, body = blocks[-1]
    names, rows = [], []
    for line in body.splitlines()[:int(n)]:
        parts = line.split()
        names.append(parts[0])
        rows.append([float(v) for v in parts[1:]])
    return names, rows


def run(params, pdk="sky130A", accuracy=0.01, run=None):
    core = fh._core(pdk)
    params = {k: v for k, v in (params or {}).items() if k in core.Parameters.__dataclass_fields__}
    run_id, run_dir = run or fh._new_run("cap")
    er = core.PROFILE.get("dielectric_er", 4.1)
    groups, vgroups, model, tap = split_groups(core, params)
    write_inputs(run_dir, core, groups, vgroups, model["bbox"], er)
    exe = shutil.which("FasterCap") or "/foss/tools/bin/FasterCap"
    t0 = time.time()
    proc = subprocess.run([exe, "-b", "coil.lst", "-a%g" % accuracy], cwd=run_dir, capture_output=True,
                          text=True, timeout=3600)
    with open(os.path.join(run_dir, "fastercap.log"), "w") as f:
        f.write(proc.stdout + proc.stderr)
    names, m = parse_matrix(proc.stdout)
    out = {"run_id": run_id, "run_dir": run_dir, "engine": "fastercap", "pdk": pdk, "dielectric_er": er,
           "parameters": model["parameters"], "accuracy": accuracy, "seconds": round(time.time() - t0, 2),
           "conductors": "A = P1..P3, B = P3..P2, G = substrate plane",
           "limits": "homogeneous dielectric; substrate as perfect ground plane (overestimates C to substrate); "
                     "boxes overlap at joints"}
    if m is None or len(m) != 3:
        out["status"] = "FAILED"
        out["log_tail"] = (proc.stdout + proc.stderr).splitlines()[-15:]
    else:
        a, b, g = 0, 1, 2
        out.update(status="COMPLETE", matrix_F=m, names=names,
                   C_AB_fF=-m[a][b] * 1e15, C_A_gnd_fF=-m[a][g] * 1e15, C_B_gnd_fF=-m[b][g] * 1e15)
        out["spice_parasitics"] = {"CB_par_F": -m[a][b], "C_X_F": -m[a][g] / 2,
                                   "C_T_F": (-m[a][g] - m[b][g]) / 2, "C_Y_F": -m[b][g] / 2,
                                   "note": "pi split of each half's ground C; X=P1 side, Y=P2 side"}
    with open(os.path.join(run_dir, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out


if __name__ == "__main__":
    print(json.dumps(run(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}), indent=2))
