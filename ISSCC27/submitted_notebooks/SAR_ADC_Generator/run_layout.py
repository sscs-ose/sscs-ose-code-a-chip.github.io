#!/usr/bin/env python3
"""Layout stage: generate blocks with gLayout and verify them (DRC, LVS, PNG).

Run with the gLayout environment:  python run_layout.py cdac --bits 4
(sizes come from build/<N>bit/design.json written by run_flow.py)
"""

import argparse
import json
import time
from pathlib import Path

from sargen.layout import verify


def do_cdac(bits, out):
    from sargen.layout import cdac
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    side = design["cu"]["side"]
    t0 = time.time()
    comp, info = cdac.build_cdac(bits, side, name=f"cdac{bits}b")
    gds = out / f"{comp.name}.gds"
    comp.write_gds(gds)
    info["gen_s"] = time.time() - t0
    ref = out / f"{comp.name}_ref.spice"
    ref.write_text(cdac.reference_netlist(bits, side, cell=comp.name))
    print(f"generated {gds} in {info['gen_s']:.1f} s: {info['rows']}x{info['cols']} units, "
          f"{info['width']:.1f} x {info['height']:.1f} um")
    for row in info["grid"]:
        print("   ", " ".join(f"{g:>2}" for g in row))
    return gds, ref, comp.name, info


def do_comparator(bits, out):
    from sargen import SarSpec
    from sargen import netlist as nl
    from sargen.layout import strongarm
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    t0 = time.time()
    comp, info = strongarm.build_strongarm(design["cmp"])
    gds = out / "strongarm.gds"
    comp.write_gds(gds)
    info["gen_s"] = time.time() - t0
    ref = out / "strongarm_ref.spice"
    from sargen.pdk import NFET, PFET, mos
    sub = nl.strongarm_subckt(design["cmp"]).replace(   # layout dummies (shorted, symmetric) for LVS
        ".ends strongarm", "\n".join(mos(n, d, g, s_, *(("vss", NFET) if k == "n" else ("vdd", PFET)), w, l)
                                     for n, d, g, s_, w, l, k in info["dummies"]) + "\n.ends strongarm")
    ref.write_text(sub + "\n")
    print(f"generated {gds} in {info['gen_s']:.1f} s: {info['width']:.2f} x {info['height']:.2f} um, "
          f"fingers {info['fingers']}")
    return gds, ref, "strongarm", info


def do_switches(bits, out):
    from sargen.layout import cell
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    t0 = time.time()
    nrow, prow, pins = cell.switch_devices(design, bits)
    comp, info = cell.build_cell("switches", nrow, prow, pins)
    gds = out / "switches.gds"
    comp.write_gds(gds)
    info["gen_s"] = time.time() - t0
    ref = out / "switches_ref.spice"
    ref.write_text(cell.reference_netlist("switches", nrow, prow, pins))
    print(f"generated {gds} in {info['gen_s']:.1f} s: {info['width']:.1f} x {info['height']:.1f} um")
    return gds, ref, "switches", info


def do_cdacsw(bits, out):
    from sargen.layout import tilearray
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    t0 = time.time()
    comp, info, ref_txt = tilearray.build_array(design, bits, name=f"cdacsw{bits}b")
    gds = out / f"{comp.name}.gds"
    comp.write_gds(gds)
    info["gen_s"] = time.time() - t0
    ref = out / f"{comp.name}_ref.spice"
    ref.write_text(ref_txt)
    print(f"generated {gds} in {info['gen_s']:.1f} s: tile {info['tile']} um, {info['ctrl_rails']} control rails, "
          f"block {info['width']:.1f} x {info['height']:.1f} um")
    return gds, ref, comp.name, info


TEST_RAILS = (["phisb", "phigb", "phig", "phis"], ["pg_0", "ng_0", "pg_1", "ng_1"])   # (sample, drive), bottom to top
TEST_GATES = [dict(en="phig", enb="phigb", pg="pg_0", ng="ng_0"), dict(en="phis", enb="phisb", pg="pg_1", ng="ng_1"),
              dict(en="phig", enb="phigb", pg="pg_1", ng="ng_1"), dict(en="phis", enb="phisb", pg="pg_0", ng="ng_0")]


def do_unit(bits, out, rows=0, cols=0):
    from sargen.layout import unitcell
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    t0 = time.time()
    if rows:
        comp, plan, ref_txt = unitcell.build_abut_test(design, TEST_RAILS, TEST_GATES, cols=cols, rows=rows,
                                                       name=f"cdac_unit_{rows}x{cols}")
    else:
        comp, plan, ref_txt = unitcell.build_unit_cell(design, TEST_RAILS, TEST_GATES[0])
    gds = out / f"{comp.name}.gds"
    comp.write_gds(gds)
    ref = out / f"{comp.name}_ref.spice"
    ref.write_text(ref_txt)
    info = dict(cell_w=plan.W, cell_h=plan.H, gen_s=time.time() - t0)
    bb = comp.bbox
    info.update(width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]))
    print(f"generated {gds}: unit cell {plan.W:.2f} x {plan.H:.2f} um ({plan.W * plan.H:.1f} um^2), "
          f"block {info['width']:.2f} x {info['height']:.2f} um")
    return gds, ref, comp.name, info


def do_topsw(bits, out):
    from sargen.layout import topswitch
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    t0 = time.time()
    comp, info, ref_txt = topswitch.build_top_switch(design)
    gds = out / f"{comp.name}.gds"
    comp.write_gds(gds)
    info["gen_s"] = time.time() - t0
    ref = out / f"{comp.name}_ref.spice"
    ref.write_text(ref_txt)
    print(f"generated {gds} in {info['gen_s']:.1f} s: {info['width']:.2f} x {info['height']:.2f} um, "
          f"{info['flavor']}, fingers {info['fingers']}")
    return gds, ref, comp.name, info


def do_sarlogic(bits, out):
    import shutil
    from sargen.layout import sarlogic
    from sargen.pdk import STDCELL_SPICE
    t0 = time.time()
    g = sarlogic.harden(bits, out / "sarlogic")
    gds = out / "sar_logic.gds"
    shutil.copy(g, gds)
    v, ins, outs = sarlogic.sar_logic_verilog(bits)
    ref = out / "sar_logic_ref.spice"
    nl_v = sorted((g.parent.parent / "nl").glob("*.nl.v"))
    ref.write_text(sarlogic.reference_spice(bits, STDCELL_SPICE, physical_netlist=nl_v[0] if nl_v else None))
    m = json.loads((g.parent.parent / "metrics.json").read_text())
    info = dict(gen_s=time.time() - t0, die_um2=m["design__die__area"], util=m["design__instance__utilization"],
                librelane_drc=(m["magic__drc_error__count"], m["klayout__drc_error__count"]),
                librelane_lvs=m["design__lvs_error__count"], antenna=m["antenna__violating__nets"])
    bb = __import__("gdstk").read_gds(gds).top_level()[0].bounding_box()
    info.update(width=float(bb[1][0] - bb[0][0]), height=float(bb[1][1] - bb[0][1]))
    print(f"generated {gds} in {info['gen_s']:.0f} s: {info['width']:.1f} x {info['height']:.1f} um, "
          f"utilization {info['util']:.2f}, LibreLane DRC {info['librelane_drc']} LVS {info['librelane_lvs']}")
    return gds, ref, "sar_logic", info


def do_core(bits, out):
    from sargen.layout import core
    t0 = time.time()
    comp, info = core.build_core(bits, out)
    gds = out / f"{comp.name}.gds"
    comp.write_gds(gds)
    ref = out / f"{comp.name}_ref.spice"
    ref.write_text(core.reference(bits, out))
    info["gen_s"] = time.time() - t0
    print(f"generated {gds} in {info['gen_s']:.1f} s: {info['width']:.1f} x {info['height']:.1f} um")
    return gds, ref, comp.name, info


def do_cdacu(bits, out):
    from sargen.layout import unitcell
    design = json.loads(Path(f"build/{bits}bit/design.json").read_text())
    t0 = time.time()
    comp, info, ref_txt = unitcell.build_unit_array(design, bits)
    gds = out / f"{comp.name}.gds"
    comp.write_gds(gds)
    info["gen_s"] = time.time() - t0
    ref = out / f"{comp.name}_ref.spice"
    ref.write_text(ref_txt)
    print(f"generated {gds} in {info['gen_s']:.1f} s: cell {info['cell'][0]:.2f} x {info['cell'][1]:.2f} um, "
          f"{info['ctrl_rails']} control rails per row, block {info['width']:.1f} x {info['height']:.1f} um")
    for row, b, t in zip(info["grid"], info["rails_bot"], info["rails_top"]):
        print("   ", " ".join(f"{g!s:>2}" for g in row), "  below:", ",".join(b), " above:", ",".join(t))
    return gds, ref, comp.name, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("block", choices=["cdac", "comparator", "switches", "cdacsw", "unitcell", "unitabut", "cdacu", "topsw", "sarlogic", "core", "lod"],
                    help="lod: per-finger length of diffusion of the drawn devices -> layout/lod.json (and lod_before.json, "
                         "the layout before the matching rework), for studies/lod_matching.py and lod_system.py")
    ap.add_argument("--bits", type=int, default=4)
    ap.add_argument("--rows", type=int, default=2, help="unitabut: rows of abutted unit cells")
    ap.add_argument("--cols", type=int, default=3, help="unitabut: columns (alternate columns mirrored)")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--pex", action="store_true", help="also extract parasitic C to layout/pex/<cell>_pex.spice")
    a = ap.parse_args()
    out = Path(f"build/{a.bits}bit/layout")
    out.mkdir(parents=True, exist_ok=True)
    if a.block == "lod":
        from sargen.layout import lod
        design = json.loads(Path(f"build/{a.bits}bit/design.json").read_text())
        lod.write(design, out / "lod.json")
        lod.write(design, out / "lod_before.json", matched=False)
        print(f"wrote {out / 'lod.json'}, {out / 'lod_before.json'}")
        return
    gds, ref, cell, info = {"cdac": do_cdac, "comparator": do_comparator, "switches": do_switches,
                            "cdacsw": do_cdacsw, "unitcell": do_unit,
                            "unitabut": lambda b, o: do_unit(b, o, a.rows, a.cols),
                            "cdacu": do_cdacu, "topsw": do_topsw,
                            "sarlogic": do_sarlogic, "core": do_core}[a.block](a.bits, out)
    if not a.no_verify:
        t = time.time()
        info["drc_klayout"] = verify.drc_klayout(gds, out / "drc")
        info["drc_magic"] = verify.drc_magic(gds, cell, out / "drc")
        info["lvs"] = verify.lvs(gds, cell, ref, cell, out / "lvs")
        verify.render_png(gds, out / f"{cell}.png")
        print(f"DRC klayout {info['drc_klayout']['total']} {info['drc_klayout']['rules']}")
        print(f"DRC magic   {info['drc_magic']['total']} {info['drc_magic']['rules']}")
        print(f"LVS {'MATCH' if info['lvs']['match'] else 'FAIL'} devices {info['lvs']['devices']} "
              f"{info['lvs']['summary']}  ({time.time() - t:.0f} s)")
    if a.pex:
        info["pex"] = str(verify.extract(gds, cell, out / "pex", parasitics=True))
        print(f"PEX {info['pex']}")
    (out / f"{cell}.json").write_text(json.dumps(info, indent=1, default=str))


if __name__ == "__main__":
    main()
