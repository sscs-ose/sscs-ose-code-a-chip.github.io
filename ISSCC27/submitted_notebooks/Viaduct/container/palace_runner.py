"""Viaduct Palace runner: full-wave FEM cross-check of the T-coil (gds2palace + AWS Palace).

What is simulated
  The VIADUCT T-coil (tcoil_core.build) plus a measurement fixture: a met1 ground
  frame around the coil and met1 fingers running under P1, P2 and the tap P3, with a
  vertical lumped port at each terminal (met1 -> met4 at P1/P2, met1 -> met5 at P3). Every EM port needs a ground
  reference, and the frame/finger inductance (tens of pH) is part of what any such
  setup measures. Therefore the comparison is made on the identical structure:
  FastHenry is run on the same coil + frame + fingers with the same three ports.

Outputs (runs/palace_<id>/)
  stackup.xml, tcoil_em.gds, the gds2palace model directory (mesh, config.json),
  Palace output, the .s3p, metrics.json with, per frequency, the 3-port Z and the
  two-port with P3 shorted to the frame (L1, L2, R, Q, K: P1-P3 and P2-P3 through the
  fixture's return path), for Palace and for FastHenry on the same structure.

Assumptions (state them with results)
  SKY130 BEOL heights, thicknesses and sheet resistances from the Magic tech file;
  one SiO2 (er = pdk dielectric_er) from substrate to 1 um above met5, a 0.6 um
  passivation (er 7), air above; p-substrate 150 um thick, resistivity
  SUBSTRATE_OHM_CM (assumed, not from the PDK); via arrays merged into blocks.
"""
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fasthenry_runner as fh  # noqa: E402

SUBSTRATE_OHM_CM = 10.0
SUBSTRATE_UM = 150.0
COMPARE_FREQS = (1e9, 5e9, 10e9, 20e9, 30e9, 40e9, 50e9)     # FastHenry points compared with Palace
EM_LAYERS = {"met1": 1, "via1": 2, "met2": 3, "via2": 4, "met3": 5, "via3": 6, "met4": 7, "via4": 8, "met5": 9}
PORT_LAYERS = {"P1": 201, "P2": 202, "P3": 203}
VIA_Z = {"via1": ("met1", "met2"), "via2": ("met2", "met3"), "via3": ("met3", "met4"), "via4": ("met4", "met5")}


# ---- stackup ------------------------------------------------------------------------------

def write_stackup(core, path, substrate_ohm_cm=SUBSTRATE_OHM_CM):
    prof = core.PROFILE
    m = prof["metals"]
    er = prof.get("dielectric_er", 4.1)
    top = m["met5"]["z_um"] + m["met5"]["thickness_um"]
    mats = ['<Material Name="%s" Type="Conductor" Conductivity="%.6g" />' % (
        n, 1.0 / (v["sheet_ohm"] * v["thickness_um"] * 1e-6)) for n, v in m.items()]
    mats += ['<Material Name="%s" Type="Conductor" Conductivity="2.0e6" />' % v for v in VIA_Z]
    mats += ['<Material Name="SiO2" Type="Dielectric" Permittivity="%g" DielectricLossTangent="0.0" />' % er,
             '<Material Name="Passive" Type="Dielectric" Permittivity="7.0" DielectricLossTangent="0.0" />',
             '<Material Name="AIR" Type="Dielectric" Permittivity="1.0" DielectricLossTangent="0.0" />',
             '<Material Name="Substrate" Type="Semiconductor" Permittivity="11.9" DielectricLossTangent="0" '
             'Conductivity="%g" />' % (100.0 / substrate_ohm_cm)]
    layers = []
    for n, v in m.items():
        layers.append('<Layer Name="%s" Type="conductor" Zmin="%.4f" Zmax="%.4f" Material="%s" Layer="%d" />' % (
            n, v["z_um"], v["z_um"] + v["thickness_um"], n, EM_LAYERS[n]))
    for n, (lo, hi) in VIA_Z.items():
        layers.append('<Layer Name="%s" Type="via" Zmin="%.4f" Zmax="%.4f" Material="%s" Layer="%d" />' % (
            n, m[lo]["z_um"] + m[lo]["thickness_um"], m[hi]["z_um"], n, EM_LAYERS[n]))
    xml = """<?xml version='1.0' encoding='UTF-8'?>
<Stackup schemaVersion="2.0">
  <!-- Viaduct: SKY130 BEOL for gds2palace. Metal z/thickness/sheet R from the Magic tech file;
       homogeneous oxide er=%g; substrate %g ohm*cm (assumed). Layer numbers are Viaduct EM layers. -->
  <Materials>
    %s
  </Materials>
  <ELayers LengthUnit="um">
    <Dielectrics>
      <Dielectric Name="AIR" Material="AIR" Thickness="100.0" />
      <Dielectric Name="Passive" Material="Passive" Thickness="0.6" />
      <Dielectric Name="SiO2" Material="SiO2" Thickness="%.4f" />
      <Dielectric Name="Substrate" Material="Substrate" Thickness="%.1f" />
    </Dielectrics>
    <Layers>
      <Substrate Offset="%.1f" />
      %s
    </Layers>
  </ELayers>
</Stackup>
""" % (er, substrate_ohm_cm, "\n    ".join(mats), top + 1.0, SUBSTRATE_UM, SUBSTRATE_UM, "\n      ".join(layers))
    with open(path, "w") as f:
        f.write(xml)


# ---- fixture: ground frame, fingers, port positions ----------------------------------------

def fixture(core, params, gap=15.0, frame_w=6.0):
    """Frame and fingers on met1 (as centerline paths) and the three port positions."""
    model = core.em_model(core.Parameters(**params))
    (x0, y0), (x1, y1) = model["bbox"]
    ports = model["ports"]
    w = model["parameters"]["metalWidth"]
    c = gap + frame_w / 2                      # frame centerline offset from the coil bbox
    fx0, fy0, fx1, fy1 = x0 - c, y0 - c, x1 + c, y1 + c
    (p1x, p1y, _), (p2x, p2y, _), (p3x, p3y, _) = ports["P1"], ports["P2"], ports["P3"]
    # Finger roots are frame nodes: FastHenry only connects conductors at shared nodes.
    paths = [dict(name="frame", metal="met1", width=frame_w,
                  points=[(fx0, fy0), (p1x, fy0), (p2x, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1), (fx0, p3y),
                          (fx0, fy0)])]
    tap = next(p for p in model["paths"] if p["name"] == "tap")
    paths += [dict(name="finger.P1", metal="met1", width=w, points=[(p1x, fy0), (p1x, p1y)]),
              dict(name="finger.P2", metal="met1", width=w, points=[(p2x, fy0), (p2x, p2y)]),
              dict(name="finger.P3", metal="met1", width=tap["width"], points=[(fx0, p3y), (p3x, p3y)])]
    # The leads exist on both parallel planes (met5 and met4), so a vertical port at P1/P2
    # ends on the lower plane (met1 -> met4); a met1 -> met5 sheet would cut through the met4
    # lead. The tap stub is met5 only (no met4 under the port line), so P3 is met1 -> met5.
    lower = model["parameters"]["lowerMetal"]
    upper = model["parameters"]["upperMetal"]
    externals = [((p1x, p1y, lower), (p1x, p1y, "met1"), "P1"),
                 ((p2x, p2y, lower), (p2x, p2y, "met1"), "P2"),
                 ((p3x, p3y, upper), (p3x, p3y, "met1"), "P3")]
    return paths, externals, model, (fx0, fy0, fx1, fy1), frame_w


def write_em_gds(core, params, path):
    """Layout polygons remapped to EM layer numbers, plus frame, fingers and port lines."""
    import klayout.db as db
    paths, externals, model, frame, frame_w = fixture(core, params)
    data = core.build(core.Parameters(**params))
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TCOIL_EM")
    gds_to_em = {tuple(core.METALS[n]): EM_LAYERS[n] for n in core.METALS}
    gds_to_em.update({tuple(core.VIAS[n]): EM_LAYERS[n] for n in core.VIAS})
    for (layer, dt), pts in data["polygons"]:
        em = gds_to_em.get((layer, dt))
        if em is None:
            continue                            # pin / label datatypes are not geometry
        top.shapes(ly.layer(em, 0)).insert(db.DPolygon([db.DPoint(x, y) for x, y in pts]))
    m1 = ly.layer(EM_LAYERS["met1"], 0)
    for p in paths:
        for (ax, ay), (bx, by) in zip(p["points"], p["points"][1:]):
            hw = p["width"] / 2
            box = db.DBox(min(ax, bx) - hw, min(ay, by) - hw, max(ax, bx) + hw, max(ay, by) + hw)
            top.shapes(m1).insert(box)
    # Port lines (zero-width boxes): gds2palace puts a vertical sheet on the box centre line.
    for (x, y, _), _, name in externals:
        if name in ("P1", "P2"):
            w = model["parameters"]["metalWidth"]
            box = db.DBox(x - w / 2, y + 1.0, x + w / 2, y + 1.0)
        else:
            tap_w = next(p["width"] for p in paths if p["name"] == "finger.P3")
            box = db.DBox(x - 0.4, y - tap_w / 2, x - 0.4, y + tap_w / 2)
        top.shapes(ly.layer(PORT_LAYERS[name], 0)).insert(box)
    # merge per layer (gds2palace meshes overlapping shapes poorly)
    for li in ly.layer_indexes():
        reg = db.Region(top.shapes(li))
        if ly.get_info(li).layer < 200:
            reg.merge()
            top.shapes(li).clear()
            top.shapes(li).insert(reg)
    ly.write(path)
    return paths, externals, model


# ---- two-port from the grounded 3-port --------------------------------------------------------

def two_port_p3_shorted(freq, y):
    """3-port Y (P1, P2, P3 to the frame) -> two-port P1/P2 with P3 shorted to the frame:
    Y' = Y[0:2, 0:2], Z' = inv(Y'). Same physics as driving P1-P3 and P2-P3, with the return
    current through the frame and fingers (the fixture is part of the measured loop in any
    grounded EM setup). Using Y avoids the ill-conditioned grounded 3-port Z of a floating coil."""
    import numpy as np
    zz = np.linalg.inv(np.asarray(y, dtype=complex)[:2, :2])
    return fh.analyse(freq, zz.tolist())


# ---- run ----------------------------------------------------------------------------------------

def run(params=None, pdk="sky130A", fstart=1e9, fstop=50e9, fstep=1e9, refined_cellsize=2.5, order=2,
        np=8, substrate_ohm_cm=SUBSTRATE_OHM_CM, timeout=6 * 3600, run=None, compare_freqs=COMPARE_FREQS):
    core = fh._core(pdk)
    params = {k: v for k, v in (params or {}).items() if k in core.Parameters.__dataclass_fields__}
    run_id, run_dir = run or fh._new_run("palace")
    out = {"run_id": run_id, "run_dir": run_dir, "engine": "palace", "pdk": pdk, "substrate_ohm_cm": substrate_ohm_cm,
           "fixture": "met1 ground frame (gap 15 um, width 6 um) and fingers under P1, P2, P3; vertical lumped "
                      "ports met1->met4 (P1, P2) and met1->met5 (P3); FastHenry run on the identical structure",
           "settings": dict(fstart=fstart, fstop=fstop, fstep=fstep, refined_cellsize=refined_cellsize, order=order, np=np)}
    t0 = time.time()
    write_stackup(core, os.path.join(run_dir, "stackup.xml"), substrate_ohm_cm)
    paths_fx, externals, model = write_em_gds(core, params, os.path.join(run_dir, "tcoil_em.gds"))
    out["parameters"] = model["parameters"]

    # 1) gds2palace model (mesh + config.json); runs in a child process so gmsh state stays clean
    script = os.path.join(run_dir, "make_model.py")
    with open(script, "w") as f:
        f.write(MODEL_SCRIPT % dict(fstart=fstart, fstop=fstop, fstep=fstep, cell=refined_cellsize, order=order,
                                    lower=model["parameters"]["lowerMetal"], upper=model["parameters"]["upperMetal"]))
    p = subprocess.run(["bash", "-lc", "cd %s && python3 make_model.py" % run_dir], capture_output=True, text=True,
                       timeout=3600)
    with open(os.path.join(run_dir, "make_model.log"), "w") as f:
        f.write(p.stdout + p.stderr)
    configs = sorted(glob.glob(os.path.join(run_dir, "**", "config.json"), recursive=True))
    if p.returncode != 0 or not configs:
        out.update(status="FAILED", stage="model", log_tail=(p.stdout + p.stderr).splitlines()[-25:])
        return _save(out)
    sim_dir = os.path.dirname(configs[0])
    out["sim_dir"] = sim_dir
    out["model_seconds"] = round(time.time() - t0, 1)

    # 2) Palace + Touchstone
    t1 = time.time()
    # `palace -np N` (Palace's own wrapper) runs mpirun once; the image's run_palace wraps
    # mpirun around that wrapper again, which Open MPI rejects as a recursive call.
    p = subprocess.run(["bash", "-lc", "cd %s && palace -np %d config.json > palace.log 2>&1; combine_snp > combine.log 2>&1"
                        % (sim_dir, np)], capture_output=True, text=True, timeout=timeout)
    out["palace_seconds"] = round(time.time() - t1, 1)
    return postprocess(out, core, params, paths_fx, externals, sim_dir, compare_freqs, t0)


def postprocess(out, core, params, paths_fx, externals, sim_dir, compare_freqs=COMPARE_FREQS, t0=None):
    """Touchstone -> two-port metrics; FastHenry on the identical structure; summary, plot, metrics.json."""
    snp = sorted(glob.glob(os.path.join(sim_dir, "**", "*.s3p"), recursive=True))
    snp = [s for s in snp if not s.endswith("_dc.s3p")] or snp
    if not snp:
        log_path = os.path.join(sim_dir, "palace.log")
        log = open(log_path, errors="replace").read().splitlines() if os.path.exists(log_path) else []
        out.update(status="FAILED", stage="palace", log_tail=log[-30:])
        return _save(out)
    out["touchstone"] = snp[0]
    import skrf
    net = skrf.Network(snp[0])
    out["palace"] = [dict(two_port_p3_shorted(f, y), frequency_hz=float(f)) for f, y in zip(net.f, net.y)]
    out["fasthenry_same_structure"] = fasthenry_same_structure(core, params, paths_fx, externals, out["run_dir"],
                                                               compare_freqs)
    out["status"] = "COMPLETE"
    if t0:
        out["seconds"] = round(time.time() - t0, 1)
    out["summary"] = summarize(out)
    _plot(out)
    return _save(out)


def reprocess(run_dir, params, pdk="sky130A"):
    """Post-process an existing Palace run directory (e.g. one started by hand)."""
    core = fh._core(pdk)
    paths_fx, externals, model, _, _ = fixture(core, params)
    sim_dir = os.path.dirname(sorted(glob.glob(os.path.join(run_dir, "**", "config.json"), recursive=True))[0])
    out = {"run_id": os.path.basename(run_dir).split("_", 1)[1], "run_dir": run_dir, "engine": "palace", "pdk": pdk,
           "substrate_ohm_cm": SUBSTRATE_OHM_CM, "parameters": model["parameters"], "sim_dir": sim_dir,
           "fixture": "met1 ground frame (gap 15 um, width 6 um) and fingers under P1, P2, P3; vertical lumped "
                      "ports met1->met4 (P1, P2) and met1->met5 (P3); FastHenry run on the identical structure"}
    return postprocess(out, core, params, paths_fx, externals, sim_dir)


def fasthenry_same_structure(core, params, paths_fx, externals, run_dir, freqs):
    """FastHenry on the coil + frame + fingers, P3 shorted to its finger by a via post,
    ports P1 and P2 against their fingers: directly the two-port of two_port_p3_shorted()."""
    paths, vias, ports, _ = fh.build_model(core, params)
    paths = paths + [dict(p, points=list(p["points"])) for p in paths_fx]
    (t3, r3, _), = [e for e in externals if e[2] == "P3"]
    tap_w = next(p["width"] for p in paths_fx if p["name"] == "finger.P3")
    vias = list(vias) + [dict(x=t3[0], y=t3[1], top=t3[2], bottom=r3[2], size=2 * tap_w)]   # solid short
    ports2 = [e for e in externals if e[2] in ("P1", "P2")]
    res = []
    for f in freqs:
        sub = os.path.join(run_dir, "fasthenry", "f_%g" % f)
        os.makedirs(sub, exist_ok=True)
        fh.write_inp(os.path.join(sub, "fixture.inp"), core, paths, vias, ports, f, "normal", externals=ports2)
        exe = shutil.which("fasthenry") or "/foss/tools/bin/fasthenry"
        subprocess.run([exe, "fixture.inp"], cwd=sub, capture_output=True, text=True, timeout=1800)
        (freq, z), = fh.parse_zc(os.path.join(sub, "Zc.mat"))
        res.append(dict(fh.analyse(freq, z), frequency_hz=freq))
    return res


def summarize(out):
    """Palace vs FastHenry (same structure) at the comparison frequencies, plus self-resonance."""
    pal = {round(r["frequency_hz"] / 1e9, 3): r for r in out["palace"]}
    rows = []
    for r in out["fasthenry_same_structure"]:
        fg = round(r["frequency_hz"] / 1e9, 3)
        q = pal.get(fg) or min(out["palace"], key=lambda x: abs(x["frequency_hz"] - r["frequency_hz"]))
        rows.append({"GHz": fg,
                     "L1_nH": [round(q["L1_nH"], 4), round(r["L1_nH"], 4)],
                     "L2_nH": [round(q["L2_nH"], 4), round(r["L2_nH"], 4)],
                     "K1": [round(q["K1"], 4), round(r["K1"], 4)],
                     "Q1": [round(q["Q1"], 2), round(r["Q1"], 2)],
                     "Q2": [round(q["Q2"], 2), round(r["Q2"], 2)]})
    srf = {}
    for key in ("L1_nH", "L2_nH"):
        prev = None
        for r in out["palace"]:
            if prev is not None and prev[key] > 0 >= r[key]:
                srf[key.replace("_nH", "")] = r["frequency_hz"]
                break
            prev = r
    return {"columns": "[Palace, FastHenry same structure]", "rows": rows,
            "self_resonance_hz": srf or "above %g GHz" % (out["palace"][-1]["frequency_hz"] / 1e9)}


def _plot(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pal = out["palace"]
    fhs = out["fasthenry_same_structure"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for ax, keys, ylabel in ((axes[0], ("L1_nH", "L2_nH"), "L (nH)"), (axes[1], ("Q1", "Q2"), "Q"),
                             (axes[2], ("K1",), "K1 (P1-P3 vs P2-P3)")):
        for k in keys:
            ax.plot([r["frequency_hz"] / 1e9 for r in pal], [r[k] for r in pal], label="Palace " + k)
            ax.plot([r["frequency_hz"] / 1e9 for r in fhs], [r[k] for r in fhs], "o", label="FastHenry " + k)
        ax.set_xlabel("GHz")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=.3)
        ax.legend(fontsize=8)
    axes[0].set_ylim(-0.5, 1.0)
    axes[2].set_ylim(-1, 1)
    fig.suptitle("T-coil + fixture: Palace (full-wave FEM, lossy substrate) vs FastHenry (quasi-static), run %s"
                 % out["run_id"])
    fig.tight_layout()
    path = os.path.join(out["run_dir"], "palace_vs_fasthenry.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    out["images"] = [path]


def _save(out):
    with open(os.path.join(out["run_dir"], "metrics.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    return out


MODEL_SCRIPT = r'''# generated by Viaduct palace_runner: gds2palace model for the T-coil EM fixture
import os
from gds2palace import *
sim_path = utilities.create_sim_path(os.getcwd(), "tcoil_em")
settings = {}
settings["GdsFile"] = "tcoil_em.gds"
settings["SubstrateFile"] = "stackup.xml"
settings["preprocess_gds"] = True
settings["merge_polygon_size"] = 1.0
settings["purpose"] = [0]
settings["fstart"] = %(fstart)g
settings["fstop"] = %(fstop)g
settings["fstep"] = %(fstep)g
settings["refined_cellsize"] = %(cell)g
settings["cells_per_wavelength"] = 10.0
settings["meshsize_max"] = 70.0
settings["adaptive_mesh_iterations"] = 0
settings["order"] = %(order)d
settings["boundary"] = ["ABC", "ABC", "ABC", "ABC", "ABC", "ABC"]
settings["margin"] = 30.0
settings["air_around"] = 30.0
settings["no_gui"] = True
settings["no_preview"] = True
simulation_ports = simulation_setup.all_simulation_ports()
for n, layer, top in ((1, 201, "%(lower)s"), (2, 202, "%(lower)s"), (3, 203, "%(upper)s")):
    simulation_ports.add_port(simulation_setup.simulation_port(portnumber=n, voltage=1.0, port_Z0=50.0,
        source_layernum=layer, from_layername="met1", to_layername=top, direction="Z"))
materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate(settings["SubstrateFile"])
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)
allpolygons = gds_reader.read_gds(settings["GdsFile"], layernumbers, purposelist=settings["purpose"],
    metals_list=metals_list, preprocess=settings["preprocess_gds"], merge_polygon_size=settings["merge_polygon_size"],
    gds_boundary_layers=dielectrics_list.get_boundary_layers(), mirror=False, offset_x=0, offset_y=0,
    layernumber_offset=0)
settings.update(simulation_ports=simulation_ports, materials_list=materials_list, dielectrics_list=dielectrics_list,
                metals_list=metals_list, layernumbers=layernumbers, allpolygons=allpolygons, sim_path=sim_path,
                model_basename="tcoil_em", unit=1e-6)
config_name, data_dir = simulation_setup.create_palace(simulation_ports.all_active_excitations(), settings)
print("CONFIG", config_name, "DATA", data_dir)
'''


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", default="{}")
    ap.add_argument("--cell", type=float, default=2.5)
    ap.add_argument("--order", type=int, default=2)
    ap.add_argument("--np", type=int, default=8)
    ap.add_argument("--fstop", type=float, default=50e9)
    ap.add_argument("--model-only", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(json.loads(a.params), refined_cellsize=a.cell, order=a.order, np=a.np, fstop=a.fstop),
                     indent=2, default=str)[:4000])
