#!/usr/bin/env python3
"""Gate-level sim of the post-layout netlist with iverilog; dumps VCD of the dut (scope tb.dut).
Usage: gl_sim.py <top> <run_dir> <stim_prefix> <out.vcd> <workdir>
Checks y/busy/valid against the RTL VCD at every edge (functional equivalence of the netlist)."""
import re
import subprocess
import sys
import json
from pathlib import Path

top, run, pre, outvcd, wd = sys.argv[1:6]
run, wd = Path(run), Path(wd)
wd.mkdir(parents=True, exist_ok=True)
w = dict(kv.split("=") for kv in Path(pre + ".info").read_text().split())
W = {k: int(v) for k, v in w.items() if k != "edges"}
E = int(w["edges"])
import os
IN = os.environ.get("GL_IN", "rst load_en load_addr load_row start x_in").split()
tot = sum(W[n] for n in IN)
slices, hi = [], tot
for n in IN:
    hi -= W[n]
    slices.append("    %s = vec[%d +: %d];" % (n, hi, W[n]))
pdk = json.loads((run / "resolved.json").read_text())["PDK_ROOT"]
vdir = Path(pdk) / "sky130A/libs.ref/sky130_fd_sc_hd/verilog"
import re as _re
PER = int(_re.search(r"clock_period_ns:\s*(\d+)", (Path(__file__).resolve().parents[1] / "spec/spec.yaml").read_text()).group(1))
PER = int(__import__("os").environ.get("GL_PERIOD", PER))   # clock period of the layout, ns
IN_DEF = chr(10).join("  reg [%d-1:0] %s = 0;" % (W[n], n) for n in IN)
CONN = ", ".join(".%s(%s)" % (n, n) for n in IN)
tb = """`timescale 1ns/1ps
module tb;
  reg clk = 0;
%(indef)s
  wire busy, valid; wire [%(y)d-1:0] y;
  %(top)s dut(.clk(clk), %(conn)s, .busy(busy), .valid(valid), .y(y));
  reg [%(tot)d-1:0] mem [0:%(E)d-1];
  reg [%(tot)d-1:0] vec;
  integer n, f;
  task drive; input integer k; begin
    vec = mem[k];
%(sl)s
  end endtask
  initial begin
    $readmemh("%(hex)s", mem);
    f = $fopen("%(out)s", "w");
    $dumpfile("%(vcd)s"); $dumpvars(0, dut);
    drive(0);
    for (n = 0; n < %(E)d; n = n + 1) begin
      #%(h)d clk = 1;
      #%(h1)d $fdisplay(f, "%%b %%b %%b", y, busy, valid);
      #1  clk = 0; if (n + 1 < %(E)d) drive(n + 1);
    end
    $fclose(f); $finish;
  end
endmodule
""" % dict(h=PER // 2, h1=PER // 2 - 1, indef=IN_DEF, conn=CONN, y=W["y"], top=top, tot=tot, E=E,
           sl=chr(10).join(slices), hex=str(Path(pre + ".hex").resolve()), out=str(wd / "gl_out.txt"),
           vcd=str(Path(outvcd).resolve()))
# clk toggles 10ns half period; drive() happens right after the falling edge
(wd / "tb.v").write_text(tb)
nl = run / "final/nl" / (top + ".nl.v")
cmd = ["iverilog", "-g2005", "-DFUNCTIONAL", "-DUNIT_DELAY=#" + __import__("os").environ.get("GL_UD", "0"), "-o", str(wd / "sim.vvp"), str(wd / "tb.v"),
       str(nl), str(vdir / "primitives.v"), str(vdir / "sky130_fd_sc_hd.v")]
subprocess.check_call(cmd)
subprocess.check_call(["vvp", "-n", str(wd / "sim.vvp")])
got = [l.split() for l in (wd / "gl_out.txt").read_text().splitlines()]
exp = [l.split() for l in Path(pre + ".exp").read_text().splitlines()]
n = min(len(got), len(exp))
bad = 0
first = None
for k in range(1, n):   # edge 0 is before reset
    ey, eb, ev = exp[k]
    g = got[k]
    ok = True
    if "x" not in eb + ev and g[1:] != [eb, ev]:
        ok = False
    if "x" not in ey and "x" not in ev and g[0] != ey:
        ok = False
    if not ok:
        bad += 1
        first = first or k
print("compared %d edges, mismatches %d (first at %s)" % (n, bad, first))
sys.exit(1 if bad else 0)
