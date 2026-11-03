"""SAR logic hardened with LibreLane (OpenROAD flow) from the same sky130_fd_sc_hd cells as the netlist.

The structural Verilog below is generated from the bit count exactly like netlist.sar_logic_cells(): per bit a
reset DFF (b_i = qp at latch_i, cleared while sampling), an OR (ctrl_i = trial_i | b_i) and the plate
drivers pg_i = NAND(ctrl_i, phisb), ng_i = NOR(ctrl_i, phig) sized for 2^i units, plus the comparator clock
gate.  LibreLane places it with tap cells (latch-up) and decaps, routes on met1..met4 only and builds the
power grid on met4 (no met5: TinyTapeout), then runs its own DRC / LVS.
"""

import json
import shutil
import subprocess
from pathlib import Path


CORE_MARGIN = 2.0       # um, core-to-die spacing (pins only: the block sits inside the analog tile, no ring)


def sar_logic_verilog(bits, name="sar_logic"):
    from ..netlist import _cell
    ins = ["clkt", "en", "qp", "phisb", "phig"] + [f"trial_{i}" for i in range(bits)] + [f"latch_{i}" for i in range(bits)]
    outs = ["clk"] + [f"bo_{i}" for i in range(bits)] + [f"pg_{i}" for i in range(bits)] + [f"ng_{i}" for i in range(bits)]
    v = [f"module {name} ({', '.join(ins + outs)});"]
    v += [f"  input {n};" for n in ins] + [f"  output {n};" for n in outs]
    v += [f"  wire ctrl_{i};" for i in range(bits)]
    v.append("  sky130_fd_sc_hd__and2_4 xclk (.A(clkt), .B(en), .X(clk));")
    for i in range(bits):
        m = 2 ** i
        v += [f"  sky130_fd_sc_hd__dfrtp_1 xff{i} (.CLK(latch_{i}), .D(qp), .RESET_B(phisb), .Q(bo_{i}));",
              f"  sky130_fd_sc_hd__or2_1 xor{i} (.A(trial_{i}), .B(bo_{i}), .X(ctrl_{i}));",
              f"  {_cell('nand2', m)} xpg{i} (.A(ctrl_{i}), .B(phisb), .Y(pg_{i}));",
              f"  {_cell('nor2', m)} xng{i} (.A(ctrl_{i}), .B(phig), .Y(ng_{i}));"]
    v.append("endmodule")
    return "\n".join(v) + "\n", ins, outs


def _cell_area(verilog):
    """Total area (um^2) of the standard cells instantiated in the structural Verilog (from the hd LEF)."""
    import re
    lef = Path("/foss/pdks/sky130A/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef").read_text()
    sizes = {m.group(1): float(m.group(2)) * float(m.group(3))
             for m in re.finditer(r"MACRO (\S+).*?SIZE ([\d.]+) BY ([\d.]+)", lef, re.S)}
    return sum(sizes[c] for c in re.findall(r"^\s+(sky130_fd_sc_hd__\S+)", verilog, re.M))


def harden(bits, out, name="sar_logic", die=None):
    """Write Verilog + LibreLane config into out/ and run the Classic flow; returns the final GDS path."""
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    v, ins, outs = sar_logic_verilog(bits, name)
    (out / f"{name}.v").write_text(v)
    # die from the cell area: 60 % placement density plus taps / fill and the core margins
    side = die or round((_cell_area(v) / 0.45) ** 0.5 + 2 * CORE_MARGIN, 1)
    cfg = {
        "DESIGN_NAME": name,
        "VERILOG_FILES": f"dir::{name}.v",
        "CLOCK_PORT": None,                       # asynchronous control signals, no timing closure needed
        "FP_SIZING": "absolute",
        "DIE_AREA": [0, 0, round(side, 2), round(side, 2)],
        "CORE_AREA": [CORE_MARGIN, CORE_MARGIN, round(side - CORE_MARGIN, 2), round(side - CORE_MARGIN, 2)],
        "PL_TARGET_DENSITY_PCT": 60,
        # keep the netlist exactly as generated: the plate drivers are sized for their 2^i units, and the
        # control nets are not clocks (no resizing, buffering or clock tree)
        "DESIGN_REPAIR_BUFFER_INPUT_PORTS": False, "DESIGN_REPAIR_BUFFER_OUTPUT_PORTS": False,
        "RUN_POST_GPL_DESIGN_REPAIR": False, "RUN_POST_GRT_DESIGN_REPAIR": False,
        "RUN_POST_CTS_RESIZER_TIMING": False, "RUN_POST_GRT_RESIZER_TIMING": False, "RUN_CTS": False,
        "RT_MAX_LAYER": "met4",                   # no met5 (TinyTapeout power grid)
        "PDN_MULTILAYER": False,                  # power grid on met4 only
        "FP_PDN_VPITCH": 15, "FP_PDN_HPITCH": 15,
        "FP_PDN_VOFFSET": 5, "FP_PDN_HOFFSET": 5,
        "RUN_LINTER": False,
        "SYNTH_ELABORATE_ONLY": True,             # keep the hand-sized cells as written
    }
    # pins by side, toward what they connect to in the core: plate drivers west (CDAC bit-control trunks),
    # comparator / phase nets south, timing inputs north, bit outputs east
    order = ["#W"] + [f"{p}_{i}" for i in range(bits) for p in ("ng", "pg")] + \
            ["", "#S", "qp", "clk", "phisb", "phig", "", "#N", "clkt", "en", "trial_.*", "latch_.*", "", "#E", "bo_.*"]
    (out / "pins.cfg").write_text("\n".join(order) + "\n")
    cfg["IO_PIN_ORDER_CFG"] = "dir::pins.cfg"
    (out / "config.json").write_text(json.dumps(cfg, indent=1))
    runs = out / "runs"
    if runs.exists():
        shutil.rmtree(runs)
    r = subprocess.run(["librelane", "--manual-pdk", "--pdk-root", "/foss/pdks", "--pdk", "sky130A", "--scl", "sky130_fd_sc_hd",
                        "--run-tag", "sargen", str(out / "config.json")],
                       cwd=out, capture_output=True, text=True, timeout=3600)
    (out / "librelane.log").write_text(r.stdout + r.stderr)
    gds = sorted(runs.glob("sargen/final/gds/*.gds"))
    if not gds:
        raise RuntimeError(f"LibreLane failed, see {out / 'librelane.log'}:\n{(r.stdout + r.stderr)[-3000:]}")
    return gds[0]


def reference_spice(bits, stdcell_spice, name="sar_logic", physical_netlist=None):
    """LVS reference: the same cells as SPICE subcircuit instances (power pins VPWR / VGND as hardened), plus
    the physical-only cells LibreLane added (decaps), read from its final Verilog netlist."""
    from ..netlist import _cell
    _, ins, outs = sar_logic_verilog(bits, name)
    p = "VGND VGND VPWR VPWR"                                          # VGND VNB VPB VPWR
    lines = [f".include {stdcell_spice}", f".subckt {name} {' '.join(ins + outs)} VPWR VGND",
             f"xclk clkt en {p} clk sky130_fd_sc_hd__and2_4"]
    for i in range(bits):
        m = 2 ** i
        lines += [f"xff{i} latch_{i} qp phisb {p} bo_{i} sky130_fd_sc_hd__dfrtp_1",
                  f"xor{i} trial_{i} bo_{i} {p} ctrl_{i} sky130_fd_sc_hd__or2_1",
                  f"xpg{i} ctrl_{i} phisb {p} pg_{i} {_cell('nand2', m)}",
                  f"xng{i} ctrl_{i} phig {p} ng_{i} {_cell('nor2', m)}"]
    if physical_netlist:
        import re
        for k, cell in enumerate(re.findall(r"^\s*(sky130_fd_sc_hd__decap_\d+)\s", Path(physical_netlist).read_text(), re.M)):
            lines.append(f"xdcap{k} {p} {cell}")
    lines.append(f".ends {name}")
    return "\n".join(lines) + "\n"
