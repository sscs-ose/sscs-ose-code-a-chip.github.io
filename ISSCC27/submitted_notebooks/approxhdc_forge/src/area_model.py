"""Pre-layout area estimate from Yosys + ABC synthesis on the sky130_fd_sc_hd liberty.

This is a Day-1 stand-in for the real LibreLane runs (flow_runs.csv replaces it later):
cell area only, no routing, utilization or clock tree. Every block below is synthesized
for real; only the storage array is counted analytically (bits x enable-flop area),
because thousands of identical flops tell synthesis nothing new.

Blocks (see DESIGN.md section 3):
  enc   : rematerialized ID/level/tie hashes + bind + P bundling accumulators + majority
  sim   : per-class similarity slice: XOR, approximate group popcount, distance accumulator
  upd   : per-lane saturating counter update, binarize; one unit per class (learning only)
  mask  : stochastic-update mask hashes, k per 32 bits (learning with k > 0)
  store : C*D prototype bits (learning off) or C*D*w counter bits (learning on)
"""
import csv
import math
import os
import pathlib
import re
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "results" / "block_area.csv"
LIB = next(pathlib.Path.home().glob(
    ".ciel/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/"
    "sky130_fd_sc_hd__tt_025C_1v80.lib"), None)
YOSYS = os.environ.get("YOSYS", "yosys")

MIX32_V = """
function [31:0] xs(input [31:0] x);
  reg [31:0] t;
  begin t = x ^ (x << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
endfunction
function [31:0] mix32(input [31:0] x);
  begin mix32 = xs(xs(xs(x) + 32'h9E3779B9) + 32'h7F4A7C15); end
endfunction
"""


def _group_fn(variant, knob):
    if variant == "trunc":
        return f"(c >> {knob})"
    if variant == "satcomp":
        m = (1 << knob) - 1
        return f"((c > {m}) ? {m} : c)"
    return "c"  # exact and sampled share the same hardware (sampled just skips slices)


def verilog_sim(P, D, variant, knob):
    aw = int(math.log2(D)) + 1
    return f"""
module top(input clk, input clr, input en, input [{P-1}:0] q, input [{P-1}:0] p,
           output reg [{aw-1}:0] dist);
  wire [{P-1}:0] x = q ^ p;
  function [3:0] g(input [7:0] b);
    reg [3:0] c; integer i;
    begin c = 0; for (i = 0; i < 8; i = i + 1) c = c + b[i]; g = {_group_fn(variant, knob)}; end
  endfunction
  reg [{aw-1}:0] s; integer k;
  always @* begin s = 0; for (k = 0; k < {P // 8}; k = k + 1) s = s + g(x[8*k +: 8]); end
  always @(posedge clk) if (clr) dist <= 0; else if (en) dist <= dist + s;
endmodule
"""


def verilog_enc(P, F, Q):
    lq, lf, aw = max(1, math.ceil(math.log2(Q))), 10, math.ceil(math.log2(F + 1))
    thr = "\n".join(f"      {q}: thr = 12'd{q * 2048 // (Q - 1)};" for q in range(Q))
    nw = P // 32
    return f"""
module top(input clk, input clr, input en, input [3:0] seed, input [15:0] slice,
           input [{lf-1}:0] f, input [{lq-1}:0] lvl, output [{P-1}:0] qbits);
{MIX32_V}
  reg [11:0] thr;
  always @* case (lvl)
{thr}
      default: thr = 12'd0;
  endcase
  genvar w, b;
  generate for (w = 0; w < {nw}; w = w + 1) begin : g_w
    wire [15:0] word = slice * {nw} + w;
    wire [31:0] hid = mix32({{seed, 2'd0, f, word}});
    wire [31:0] hl0 = mix32({{seed, 2'd2, 10'd0, word}});
    wire [31:0] ht  = mix32({{seed, 2'd1, 10'd0, word}});
    for (b = 0; b < 32; b = b + 1) begin : g_b
      wire [11:0] j = word * 32 + b;
      wire [11:0] r = {{j[0],j[1],j[2],j[3],j[4],j[5],j[6],j[7],j[8],j[9],j[10],j[11]}};
      wire lbit = hl0[b] ^ (r < thr);
      reg [{aw-1}:0] acc;
      always @(posedge clk) if (clr) acc <= 0; else if (en) acc <= acc + (hid[b] ^ lbit);
      assign qbits[32*w+b] = (2*acc > {F}) ? 1'b1 : (2*acc < {F}) ? 1'b0 : ht[b];
    end
  end endgenerate
endmodule
"""


def verilog_upd(P, w):
    lo, hi = -(1 << (w - 1)), (1 << (w - 1)) - 1
    return f"""
module top(input [{P*w-1}:0] cin, input [{P-1}:0] q, input [{P-1}:0] m, input [{P-1}:0] t,
           input sub, output [{P*w-1}:0] cout, output [{P-1}:0] proto);
  genvar i;
  generate for (i = 0; i < {P}; i = i + 1) begin : g
    wire signed [{w-1}:0] c = cin[{w}*i +: {w}];
    wire signed [{w}:0] d = (q[i] ^ sub) ? c + 1 : c - 1;
    wire signed [{w-1}:0] s = (d > {hi}) ? {hi} : (d < {lo}) ? {lo} : d[{w-1}:0];
    assign cout[{w}*i +: {w}] = m[i] ? s : c;
    assign proto[i] = (c > 0) | ((c == 0) & t[i]);
  end endgenerate
endmodule
"""


def verilog_mask(P, k):
    return f"""
module top(input [3:0] seed, input [9:0] u, input [15:0] slice, output [{P-1}:0] m);
{MIX32_V}
  genvar w;
  generate for (w = 0; w < {P // 32}; w = w + 1) begin : g
    wire [15:0] word = (slice * {P // 32} + w) * 4;
    assign m[32*w +: 32] = {" & ".join(f"mix32({{seed, 2'd3, u, word + 16'd{i}}})" for i in range(k))};
  end endgenerate
endmodule
"""


def synth_area(verilog):
    """Synthesize to sky130_fd_sc_hd cells; return total cell area in um^2."""
    with tempfile.TemporaryDirectory() as d:
        v = pathlib.Path(d) / "top.v"
        v.write_text(verilog)
        rpt = pathlib.Path(d) / "stat.txt"
        script = (f"read_verilog -sv {v}; synth -flatten -top top; "
                  f"dfflibmap -liberty {LIB}; abc -liberty {LIB}; opt_clean; "
                  f"tee -q -o {rpt} stat -liberty {LIB}")
        subprocess.run([YOSYS, "-q", "-p", script], capture_output=True, text=True, check=True)
        out = rpt.read_text()
    return float(re.findall(r"Chip area for (?:top )?module '\\top':\s*([\d.]+)", out)[-1])


def lib_cell_area(cell):
    txt = LIB.read_text()
    i = txt.index(f'cell ("{cell}")')
    return float(re.search(r"area\s*:\s*([\d.]+)", txt[i:]).group(1))


# ------------------------------------------------------------------------ block cache
def _key(block, **kw):
    return block + ":" + ",".join(f"{k}={kw[k]}" for k in sorted(kw))


def _job(args):
    block, kw = args
    src = {"sim": verilog_sim, "enc": verilog_enc, "upd": verilog_upd, "mask": verilog_mask}
    return _key(block, **kw), synth_area(src[block](**kw))


def _load_cache():
    if not CACHE.exists():
        return {}
    with CACHE.open() as fh:
        return {r["key"]: float(r["area_um2"]) for r in csv.DictReader(fh)}


def ensure_blocks(jobs, workers=None):
    """Synthesize any (block, params) not yet in the cache, in parallel."""
    cache = _load_cache()
    todo = [j for j in jobs if _key(j[0], **j[1]) not in cache]
    todo = list({_key(b, **kw): (b, kw) for b, kw in todo}.values())
    if todo:
        with ProcessPoolExecutor(workers or max(1, os.cpu_count() - 2)) as ex:
            for k, a in ex.map(_job, todo):
                cache[k] = a
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["key", "area_um2"])
            for k in sorted(cache):
                wr.writerow([k, f"{cache[k]:.2f}"])
    return cache


def design_jobs(D, P, F, Q, variant, knob, learn, w, k):
    hw_v, hw_k = ("exact", 0) if variant == "sampled" else (variant, knob)
    jobs = [("enc", dict(P=P, F=F, Q=Q)), ("sim", dict(P=P, D=D, variant=hw_v, knob=hw_k))]
    if learn:
        jobs.append(("upd", dict(P=P, w=w)))
        if k:
            jobs.append(("mask", dict(P=P, k=k)))
    return jobs


def design_area(D, P, F=64, Q=16, C=6, variant="exact", knob=0, learn=False, w=8, k=0,
                cache=None):
    """Estimated cell area (um^2) of a whole design point, broken down by block."""
    cache = cache if cache is not None else ensure_blocks(
        design_jobs(D, P, F, Q, variant, knob, learn, w, k))
    jobs = design_jobs(D, P, F, Q, variant, knob, learn, w, k)
    a = {"enc": cache[_key(*jobs[0][:1], **jobs[0][1])],
         "sim": C * cache[_key(jobs[1][0], **jobs[1][1])]}
    if learn:
        a["upd"] = C * cache[_key(jobs[2][0], **jobs[2][1])]   # one update unit per class ring
        a["mask"] = cache[_key(jobs[3][0], **jobs[3][1])] if k else 0.0
    a["store"] = C * D * (w if learn else 1) * lib_cell_area("sky130_fd_sc_hd__edfxtp_1")
    a["total"] = sum(a.values())
    return a


if __name__ == "__main__":
    import time
    t = time.time()
    for P in (64, 1024):
        for v, kn in (("exact", 0), ("trunc", 2), ("satcomp", 2)):
            print(P, v, kn, {k: round(x) for k, x in design_area(1024, P, variant=v, knob=kn,
                                                                learn=True, w=4, k=3).items()})
    print(f"{time.time() - t:.1f}s")
