"""Layout of the 5T OTA (examples/ota5t_xschem.py sizes) in KLayout, then DRC and LVS.

    python examples/ota5t_layout.py

Devices are the SKY130 PDK's own `skywater130` PCells (nfet / pfet, nf = 2, L = 1 um), placed
and wired through Viaduct's KLayout tap. Floorplan, two columns by three rows:

    M3 pfet (flipped, gates down)   M4 pfet (flipped)      VDD rail (met2) on top
    M1 nfet                         M2 nfet                tail rail (met2) under the pair
    M6 nfet                         M5 nfet                GND rail (met2) at the bottom

Sources of a device are joined by a met2 strap, its drain leaves through one via; gates are
joined by met1. M3 and M6 are diode-connected with a met1 jumper, the bulk taps of M3-M6 are
tied to their sources in li. M1/M2 taps reach GND through the p-substrate only.

DRC uses Viaduct's runner (SKY130 KLayout deck); LVS runs the PDK's KLayout LVS deck against
a subcircuit with the same devices, with the switches this deck needs for an xschem-style
netlist (convert_subckts, top_lvl_pins, combine, W/L in metres).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from viaduct import Viaduct, ViaductError  # noqa: E402

RUNS = "/foss/designs/viaduct/runs"
LVS_DECK = "/foss/pdks/sky130A/libs.tech/klayout/lvs/sky130.lvs"
# W per finger (nf = 2) and total W, um; L = 1 um. Must match ota5t_xschem.py defaults.
SIZES = {"M1": ("nfet", 10.0), "M2": ("nfet", 10.0), "M3": ("pfet", 8.0), "M4": ("pfet", 8.0),
         "M5": ("nfet", 8.0), "M6": ("nfet", 8.0)}

CODE = r'''
import pya
cv = pya.CellView.active()
ly, top = cv.layout(), cv.cell
L = lambda l, d: ly.layer(l, d)
LI, M1, M2 = L(67, 20), L(68, 20), L(69, 20)
M1LBL, M2LBL = L(68, 5), L(69, 5)
SIZES = %(sizes)s

def box(layer, x1, y1, x2, y2):
    top.shapes(layer).insert(pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))

def label(layer, text, x, y):
    top.shapes(layer).insert(pya.DText(text, x, y))

VIA12 = ly.create_cell("vias_gen", "skywater130", {"l": 0.26, "w": 0.5, "start_layer": "metal1", "end_layer": "metal2"})

def via12(xc, y1):
    """met1-met2 via, 0.26 x 0.5, centred on a vertical met1 strip at x = xc, from y1 up."""
    top.insert(pya.DCellInstArray(VIA12.cell_index(), pya.DTrans(pya.DVector(xc - 0.13, y1))))

# nf = 2 device, local x: source strips at 0.15 and 2.75, drain strip at 1.45, gate pads 0.295..2.605
XS, XD, GATE = (0.15, 2.75), 1.45, (0.295, 2.605)

def dev(name, x, y0, flip=False):
    """Place a device. Not flipped: diffusion y0..y0+w, gate pads above.
    Flipped: y0 is the top of the diffusion (y0-w..y0), gate pads below."""
    kind, w = SIZES[name]
    pc = ly.create_cell(kind, "skywater130", {"w": w, "l": 1.0, "nf": 2, "bulk": "bulk tie", "gate_con_pos": "top"})
    top.insert(pya.DCellInstArray(pc.cell_index(), pya.DTrans(pya.DTrans.M0 if flip else pya.DTrans.R0, pya.DVector(x, y0))))
    bot, tp = (y0, y0 + w) if not flip else (y0 - w, y0)
    gate = (tp + 0.25, tp + 1.18) if not flip else (bot - 1.18, bot - 0.25)
    return {"x": x, "bot": bot, "top": tp, "gate": gate, "kind": kind}

d = {"M6": dev("M6", 0.0, 0.0), "M5": dev("M5", 8.0, 0.0),
     "M1": dev("M1", 0.0, 16.0), "M2": dev("M2", 8.0, 16.0),
     "M3": dev("M3", 0.0, 44.0, True), "M4": dev("M4", 8.0, 44.0, True)}

for g in d.values():                                   # gate straps
    box(M1, g["x"] + GATE[0], g["gate"][0], g["x"] + GATE[1], g["gate"][1])

def src_strap(g, y1):
    for xs in XS:
        via12(g["x"] + xs, y1)
    box(M2, g["x"] + XS[0] - 0.13, y1, g["x"] + XS[1] + 0.13, y1 + 0.5)

for n in ("M1", "M2", "M5", "M6"):                     # NMOS: sources low, drain via high
    src_strap(d[n], d[n]["bot"] + 0.6)
    via12(d[n]["x"] + XD, d[n]["top"] - 1.1)
for n in ("M3", "M4"):                                 # PMOS (flipped): drain via low, sources high
    src_strap(d[n], d[n]["top"] - 1.1)
    via12(d[n]["x"] + XD, d[n]["bot"] + 0.6)

box(M2, 0.02, d["M6"]["bot"] + 0.6, 10.88, d["M6"]["bot"] + 1.1)    # GND rail
box(M2, 0.02, d["M1"]["bot"] + 0.6, 10.88, d["M1"]["bot"] + 1.1)    # tail rail
box(M2, 0.02, d["M3"]["top"] - 1.1, 10.88, d["M3"]["top"] - 0.6)    # VDD rail

g = d["M6"]; box(M1, g["x"] + XD - 0.115, g["top"] - 0.3, g["x"] + XD + 0.115, g["gate"][0] + 0.1)   # M6 diode
g = d["M3"]; box(M1, g["x"] + XD - 0.115, g["gate"][1] - 0.1, g["x"] + XD + 0.115, g["bot"] + 0.3)  # M3 diode

box(M1, d["M6"]["x"] + GATE[1] - 0.1, d["M6"]["gate"][0], d["M5"]["x"] + GATE[0] + 0.1, d["M6"]["gate"][0] + 0.23)  # NB
box(M1, d["M3"]["x"] + GATE[1] - 0.1, d["M3"]["gate"][1] - 0.23, d["M4"]["x"] + GATE[0] + 0.1, d["M3"]["gate"][1])  # mirror

xc = lambda n: d[n]["x"] + XD
box(M2, xc("M1") - 0.13, d["M1"]["top"] - 1.1, xc("M1") + 0.13, d["M3"]["bot"] + 1.1)   # net1: M1.D - M3.D
box(M2, xc("M2") - 0.13, d["M2"]["top"] - 1.1, xc("M2") + 0.13, d["M4"]["bot"] + 1.1)   # OUT:  M2.D - M4.D
box(M2, xc("M5") - 0.13, d["M5"]["top"] - 1.1, xc("M5") + 0.13, d["M2"]["bot"] + 1.1)   # tail: M5.D - rail

for n in ("M3", "M4", "M5", "M6"):                     # bulk tap -> own source, in li
    g = d[n]
    ym = (g["bot"] + g["top"]) / 2
    box(LI, g["x"] + 2.665, ym - 0.5, g["x"] + (3.18 if g["kind"] == "pfet" else 3.21), ym + 0.5)

label(M1LBL, "INP", d["M1"]["x"] + 1.45, sum(d["M1"]["gate"]) / 2)
label(M1LBL, "INN", d["M2"]["x"] + 1.45, sum(d["M2"]["gate"]) / 2)
label(M1LBL, "NB", d["M6"]["x"] + 0.8, sum(d["M6"]["gate"]) / 2)
label(M2LBL, "OUT", xc("M2"), (d["M2"]["top"] + d["M4"]["bot"]) / 2)
label(M2LBL, "VDD", 5.4, d["M3"]["top"] - 0.85)
label(M2LBL, "GND", 5.4, d["M6"]["bot"] + 0.85)
v = pya.LayoutView.current()
v.add_missing_layers(); v.max_hier(); v.zoom_fit()
b = top.dbbox()
result = {"cell": top.name, "instances": top.child_instances(), "width_um": round(b.width(), 3), "height_um": round(b.height(), 3)}
'''

LVS_NETLIST = """* 5T OTA core + bias diode, as in examples/ota5t_xschem.py (L = 1 um)
.subckt OTA5T VDD GND INP INN OUT NB
XM1 net1 INP TAIL GND sky130_fd_pr__nfet_01v8 L=1u W={M1}u
XM2 OUT INN TAIL GND sky130_fd_pr__nfet_01v8 L=1u W={M2}u
XM3 net1 net1 VDD VDD sky130_fd_pr__pfet_01v8 L=1u W={M3}u
XM4 OUT net1 VDD VDD sky130_fd_pr__pfet_01v8 L=1u W={M4}u
XM5 TAIL NB GND GND sky130_fd_pr__nfet_01v8 L=1u W={M5}u
XM6 NB NB GND GND sky130_fd_pr__nfet_01v8 L=1u W={M6}u
.ends
"""


def build(vd, cell="OTA5T"):
    """Draw the layout in the open KLayout session; returns its size and a screenshot path."""
    k = vd.klayout
    k.new_layout(cell).check()
    info = k.eval(CODE % {"sizes": repr(SIZES)}).check().result
    shot = k.screenshot("%s/ota5t_layout.png" % RUNS, width=900, height=1300).check().result
    info["screenshot"] = shot["local_path"]
    return info


def lvs(vd, gds):
    """PDK KLayout LVS of `gds` (container path) against the OTA subcircuit; returns a summary."""
    run_dir = "%s/lvs_%s" % (RUNS, time.strftime("%Y%m%d_%H%M%S"))
    total = {n: 2 * w for n, (_, w) in SIZES.items()}
    Path(vd.transport.to_local(run_dir)).mkdir(parents=True, exist_ok=True)
    Path(vd.transport.to_local(run_dir + "/OTA5T.spice")).write_text(
        LVS_NETLIST.format(**{n: "%g" % w for n, w in total.items()}), encoding="utf-8", newline="\n")
    # absolute paths: the deck resolves relative ones against the directory of the GDS
    cmd = ("cd {d} && klayout -b -r {deck} -rd input={gds} -rd report={d}/OTA5T.lvsdb -rd schematic={d}/OTA5T.spice "
           "-rd target_netlist={d}/extracted.cir -rd thr=4 -rd run_mode=flat -rd spice_net_names=true "
           "-rd combine=true -rd top_lvl_pins=true -rd convert_subckts=true > lvs.log 2>&1").format(d=run_dir, deck=LVS_DECK, gds=gds)
    vd.transport.shell(cmd, timeout=900)
    log = Path(vd.transport.to_local(run_dir + "/lvs.log")).read_text(errors="replace")
    extracted = Path(vd.transport.to_local(run_dir + "/extracted.cir")).read_text(errors="replace")
    pins = re.search(r"^\.SUBCKT OTA5T (.*)$", extracted, re.M)
    return {"match": "Congratulations! Netlists match." in log, "run_dir": run_dir,
            "devices_extracted": sum(1 for l in extracted.splitlines() if re.match(r"X?M\$", l)),
            "pins": pins.group(1).split() if pins else [],
            "extracted_netlist": extracted.strip().splitlines()}


def main():
    vd = Viaduct.from_env()
    info = build(vd)
    drc = vd.verify.drc(live=False).check().result
    rep = lvs(vd, drc["gds"])
    print(json.dumps({"layout": info, "drc": {k: drc[k] for k in ("run_id", "rules_checked", "violations")},
                      "lvs": {k: rep[k] for k in ("match", "devices_extracted", "pins", "run_dir")}}, indent=2))
    if drc["violations"] or not rep["match"]:
        raise ViaductError("layout not clean: DRC %d violations, LVS match %s" % (drc["violations"], rep["match"]))


if __name__ == "__main__":
    main()
