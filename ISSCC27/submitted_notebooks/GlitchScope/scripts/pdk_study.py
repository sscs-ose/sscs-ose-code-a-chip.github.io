"""Same circuit, six open technologies: the c6288-class 16x16 NOR array multiplier built
from each library's own INV / NOR2 / AND2 cells, analysed with M0 / M1 / M2.

    python scripts/pdk_study.py <dir with prepared .lib files> [n_vectors] [n_bits]

Writes data/pdk/trend.json.  Input transition per library = the FO4 output slew of its
unit inverter (iterated to a fixed point), so every node is driven at its own natural
edge rate.  M2 uses a library's SPICE pulse calibration when one is bundled
(glitchscope/data/<lib prefix>/m2_model.json); otherwise M2 is reported as unavailable.
"""
import importlib.util, json, random, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file, LibertyDelayProvider
from glitchscope.liberty_power import liberty_units
from glitchscope.pdk import pick_cells
from glitchscope.verilog import read_verilog
from glitchscope.model import Cell
from glitchscope.m2model import M2Model, calibration_for
from glitchscope.analyze import EnergyModel, analyze
from glitchscope.sim import PulseSimulator

LIBDIR = Path(sys.argv[1]); NV = int(sys.argv[2]) if len(sys.argv) > 2 else 24
NB = int(sys.argv[3]) if len(sys.argv) > 3 else 16
NODES = [("gf180mcu_7t_3v3", "GF180MCU", 180), ("sky130hd_1v8", "SKY130 HD", 130),
         ("ihp_sg13g2_1v2", "IHP SG13G2", 130), ("nangate45_1v1", "Nangate45", 45),
         ("asap7_rvt_0v7", "ASAP7", 7), ("gt2n_w31_svt_0v7", "GT2N", 2)]
spec = importlib.util.spec_from_file_location("gen", ROOT / "bench/gen_arraymul.py")
gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
OUT = ROOT / "data/pdk/trend.json"; OUT.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(OUT.read_text()) if OUT.exists() else {}


def fo4_slew_fs(lib, dp, inv):
    c = lib.cells[inv.name]
    cin = c.pin_capacitance.get(inv.inputs[0], 1.0)
    cell = Cell("x", "LIB:" + next(p.function for p in c.pins.values() if p.direction == "output"),
                {inv.inputs[0]: "a"}, "y", 0, 0, inv.name, inv.output)
    slew = 20_000
    for _ in range(20):
        r = dp.delay(cell, 1, input_slew_fs=slew, load_ff=4 * cin, related_pin=inv.inputs[0],
                     pin_values={inv.inputs[0]: 0}, input_transition=(1, 0))
        f = dp.delay(cell, 0, input_slew_fs=slew, load_ff=4 * cin, related_pin=inv.inputs[0],
                     pin_values={inv.inputs[0]: 1}, input_transition=(0, 1))
        new = int((r.output_slew_fs + f.output_slew_fs) / 2)
        if abs(new - slew) < 100:
            break
        slew = new
    return new, int((r.delay_fs + f.delay_fs) / 2), cin


for key, label, node in NODES:
    if key in data and data[key].get("vectors") == NV and data[key].get("bits") == NB:
        print(f"{label}: cached"); continue
    path = LIBDIR / f"{key}.lib"
    t0 = time.time()
    lib = parse_liberty_file(path); u = liberty_units(path)
    cells = pick_cells(lib, wanted=("inv", "nor2", "and2"))
    text, ncell = gen.generate(NB, cells=cells)
    vpath = ROOT / f"build_pdk/{key}_arraymul{NB}.v"; vpath.parent.mkdir(exist_ok=True); vpath.write_text(text)
    net = read_verilog(vpath, lib=lib)
    dp = LibertyDelayProvider(lib)
    slew, fo4, cin = fo4_slew_fs(lib, dp, cells["inv"])
    cal = calibration_for(lib.name)
    em = EnergyModel(path, net, m2_json=cal, spice_scale=bool(cal))
    rnd = random.Random(7)
    vecs = [{p: rnd.randint(0, 1) for p in net.primary_inputs} for _ in range(NV)]
    row = dict(label=label, node_nm=node, library=lib.name, vdd=u["vdd"], cells=ncell, vectors=NV, bits=NB,
               picked={k: v.name for k, v in cells.items()}, input_slew_ps=slew / 1000, fo4_ps=fo4 / 1000,
               inv_cin_ff=cin, calibration=str(cal.relative_to(ROOT)) if cal else None, models={})
    for m in ("M0", "M1", "M2"):
        if m == "M2" and not cal:
            continue
        t = time.time()
        sim = PulseSimulator(net, dp, m, r_filter=M2Model(cal), default_input_slew_fs=slew)
        r = analyze(sim, em, vecs)
        row["models"][m] = dict(totals=r["totals"], counts=r["counts"], seconds=time.time() - t)
        print(f"  {label:10s} {m}: glitch {100 * r['totals']['glitch_fraction']:5.1f} %  "
              f"E/vec {r['totals']['E_total_fJ'] / NV / 1e3:8.2f} pJ  {time.time() - t:5.0f}s", flush=True)
    row["seconds"] = time.time() - t0
    data[key] = row
    OUT.write_text(json.dumps(data, indent=1))
print("done")
