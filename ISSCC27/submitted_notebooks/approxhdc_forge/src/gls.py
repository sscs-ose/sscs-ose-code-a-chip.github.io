"""Gate-level simulation and activity-annotated power of a finished flow run.

    python gls.py <flow design dir> check      # netlist vs. Python model (random + real samples)
    python gls.py <flow design dir> power      # VCD windows -> OpenSTA power, energy per sample

The post-layout netlist `final/nl/hdc_chip.nl.v` is simulated with the sky130_fd_sc_hd
functional cell models (zero delay) by Icarus Verilog 14 (OSS CAD Suite). The testbench is
plain Verilog driven by a generated stimulus file, so no cocotb or simulator plugin is needed.
Its outputs (prediction, learned flag per sample) are compared with hdc_model.py.

Power: the clock runs at the flow's period (20 ns). Switching activity is dumped only inside a
measurement window (dumping starts when the window opens), then OpenSTA, inside the LibreLane
image, reads the VCD together with the extracted parasitics and reports power at the typical
corner. Energy per sample = average window power x window duration / samples.
"""
import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import asdict

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tb"))

PDK_ROOT = pathlib.Path(os.environ.get("PDK_ROOT", pathlib.Path.home() / ".ciel"))
IMAGE = "ghcr.io/librelane/librelane:3.0.14"
OSS = pathlib.Path.home() / "tools" / "oss-cad-suite" / "bin"
CLK_NS, IOW = 20, 32
N_POWER_SAMPLES = int(os.environ.get("N_POWER_SAMPLES", 4))      # windows per measurement phase, spread over the users
N_POWER_USERS = int(os.environ.get("N_POWER_USERS", 1))          # how many unseen users the windows come from
POWER_TAG = os.environ.get("POWER_TAG", "")                      # suffix for the output json, to keep different protocols apart


def pdk_file(pattern):
    return next(PDK_ROOT.glob(f"ciel/sky130/versions/*/sky130A/{pattern}"))


def netlist_ports(nl):
    text = nl.read_text(errors="replace")[:4000]
    return {n: (k, int(m) + 1 if m else 1)
            for k, m, n in re.findall(r"^\s*(input|output)\s*(?:\[(\d+):0\])?\s*(\w+);", text, re.M)}


TB = """`timescale 1ns/1ps
module gls_tb;
  reg clk = 0;
  always #{half} clk = ~clk;
  reg rst = 0, start = 0, learn = 0, upd_err = 0, feat_we = 0, ld_shift = 0, load_we = 0;
  reg [{lf}:0] feat_addr = 0;
  reg [{lq}:0] feat_data = 0;
  reg [2:0] label = 0;
  reg [{iow}:0] ld_data = 0;
  wire busy, done, learned;
  wire [2:0] pred;
  hdc_chip dut (.clk(clk), .rst(rst), .start(start), .learn(learn), .upd_err(upd_err),
    .label(label), .feat_we(feat_we), .feat_addr(feat_addr), .feat_data(feat_data),
    .ld_shift(ld_shift), .ld_data(ld_data), .load_we(load_we), .busy(busy), .done(done),
    .pred(pred), .learned(learned));
  task tick; begin @(posedge clk); #1; end endtask
  task feat_write(input integer a, input integer v);
    begin feat_we = 1; feat_addr = a; feat_data = v; tick; feat_we = 0; end endtask
  task ld_chunk(input [{iow}:0] d);
    begin ld_shift = 1; ld_data = d; tick; ld_shift = 0; end endtask
  task ld_commit; begin load_we = 1; tick; load_we = 0; end endtask
  task run(input integer idx, input integer lab, input integer lrn, input integer ue);
    begin
      label = lab; learn = lrn; upd_err = ue; start = 1; tick; start = 0;
      @(posedge done); #1;
      $display("RES %0d %0d %0d", idx, pred, learned);
      tick;
    end endtask
  task window_begin(input integer phase);
    begin
      if (phase == 1) begin $dumpfile("gls_infer.vcd"); end
      else begin $dumpfile("gls_learn.vcd"); end
      $dumpvars(0, dut);
      $display("WINDOW_START %0t", $time);
    end endtask
  task window_end; begin $display("WINDOW_END %0t", $time); $dumpflush; end endtask
  initial begin
    #{timeout} $display("TIMEOUT at %0t (busy=%b done=%b)", $time, busy, done);
    $finish;
  end
  initial begin
    rst = 1; tick; tick; rst = 0; tick;
    while (busy !== 1'b0) tick;
    $display("READY at %0t (busy=%b)", $time, busy);
    `include "stim.vh"
    $finish;
  end
endmodule
"""


def stim_lines(cfg, chunks_per_word, words, samples, window=None):
    """Verilog statements: preload ring words, then run samples. `samples` is a list of
    (features, label, learn, upd_err); window = phase id (1 infer, 2 learn) or None."""
    L = []
    for w in words:
        for c in range(chunks_per_word):
            L.append(f"ld_chunk({IOW + 1}'h{(w >> (c * IOW)) & ((1 << IOW) - 1):x});")
        L.append("ld_commit;")
    if window:
        L.append(f"window_begin({window});")
    for i, (x, lab, lrn, ue) in enumerate(samples):
        L += [f"feat_write({f}, {int(v)});" for f, v in enumerate(x)]
        L.append(f"run({i}, {lab}, {lrn}, {ue});")
    if window:
        L.append("window_end;")
    return "\n".join(L) + "\n"


def parse_res(out):
    res = [tuple(int(v) for v in m.groups()) for m in re.finditer(r"RES (\d+) (\d+) (\d+)", out)]
    t0 = re.search(r"WINDOW_START (\d+)", out)
    t1 = re.search(r"WINDOW_END (\d+)", out)
    return res, (int(t0.group(1)), int(t1.group(1))) if t0 and t1 else None


FF_MODEL = """
module sky130_fd_sc_hd__dfxtp_{n} (Q, CLK, D, VPWR, VGND, VPB, VNB);
  output Q; input CLK, D, VPWR, VGND, VPB, VNB;
  reg q = 1'b{init};
  always @(posedge CLK) q <= #1 D;
  assign Q = q;
endmodule
"""


def cell_models(init):
    """sky130 functional cell library with the dfxtp flops replaced by behavioral models that
    power up to `init`. The library's UDP flops start at X, and X-pessimism in the synthesized
    clear logic keeps some accumulator bits X forever (a simulation artifact: silicon powers up
    to 0 or 1). Running with init=0 and init=1 shows the netlist works from either state."""
    out = ROOT / "sim_build" / f"sky130_models_init{init}.v"
    if not out.exists():
        text = pdk_file("libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v").read_text()
        text = re.sub(r"module sky130_fd_sc_hd__dfxtp_[124]\s*\(.*?endmodule", "", text, flags=re.S)
        out.write_text(text + "".join(FF_MODEL.format(n=n, init=init) for n in (1, 2, 4)))
    return out


def simulate(design_dir, tag, stim, init=None):
    """Compile the netlist + testbench with Icarus 14 and run it; returns stdout, sim dir."""
    init = int(os.environ.get("GLS_INIT", 0)) if init is None else init
    run = design_dir / "runs" / "run" / "final"
    nl = run / "nl" / "hdc_chip.nl.v"
    bdir = (ROOT / "sim_build" / f"gls_{design_dir.name}_{tag}_i{init}").resolve()
    bdir.mkdir(parents=True, exist_ok=True)
    ports = netlist_ports(nl)
    (bdir / "gls_tb.v").write_text(TB.format(
        half=CLK_NS // 2, timeout=int(os.environ.get("GLS_TIMEOUT_NS", 5_000_000)),
        lf=ports["feat_addr"][1] - 1, lq=ports["feat_data"][1] - 1, iow=IOW - 1))
    (bdir / "stim.vh").write_text(stim)
    prims = pdk_file("libs.ref/sky130_fd_sc_hd/verilog/primitives.v")
    subprocess.run([str(OSS / "iverilog"), "-g2012", "-DFUNCTIONAL", "-DUNIT_DELAY=#1",
                    "-s", "gls_tb", "-I", str(bdir), "-o", str(bdir / "sim.vvp"),
                    str(prims), str(cell_models(init)), str(nl), str(bdir / "gls_tb.v")], check=True,
                   capture_output=True, text=True)
    out = subprocess.run([str(OSS / "vvp"), "-n", str(bdir / "sim.vvp")], cwd=bdir, check=True,
                         capture_output=True, text=True).stdout
    return out, bdir


# ----------------------------------------------------------------------- model side
def setup_model(design_dir):
    cfg = json.loads((design_dir / "hdc_config.json").read_text())
    os.environ["HDC_CFG"] = json.dumps(cfg)
    import test_hdc as T   # builds CFG, IM, SIM from HDC_CFG
    return T


def preload_words(T, L):
    """Ring words (as test_hdc.to_words) for a model learner's state."""
    return T.to_words(T.model_state(L))


def trained_learner(T, d, n_epochs=1):
    cfg = T.CFG
    Qtr = T.H.encode(d["train"][0], T.IM)
    wt = cfg.w if cfg.learn else 16
    mode = "bundle" if cfg.learn == 1 else "error"
    L0 = T.H.train(Qtr, d["train"][1], cfg.D, wt, mode, T.IM.T, T.SIM, cfg.k if cfg.learn else 0,
                   cfg.seed, error_epochs=n_epochs)
    L = T.new_learner()
    T.set_state(L, L0.cnt.copy() if cfg.learn else L0.proto.copy())
    return L


def expected(T, L, samples):
    """Model results (pred, learned) for the same stimulus; advances L like the chip."""
    out = []
    for x, lab, lrn, ue in samples:
        q, qp = T.encode(x)
        if lrn and T.CFG.learn:
            L.mode = "error" if (ue and T.CFG.learn == 2) else "bundle"
            pred = L.step(q, qp, lab)
            out.append((pred, int(L.mode == "bundle" or pred != lab)))
        else:
            out.append((int(T.H.classify(qp, L.protop, T.SIM)), 0))
    return out


def chunks_per_word(T):
    return math.ceil(T.CFG.C * T.CFG.P * (T.CFG.w if T.CFG.learn else 1) / IOW)


def cmd_check(d):
    T = setup_model(d)
    cfg = T.CFG
    rng = np.random.default_rng(7)
    data = T.data.load(cfg.F, cfg.Q)
    xr, yr, _ = data["test"]
    # 1) random state + random features: inference, then learning (as test_chip)
    L = T.new_learner()
    st = T.random_state(rng)
    T.set_state(L, st)
    samples = []
    for n in range(24):
        learn = int(cfg.learn > 0 and n >= 12)
        upd = int(cfg.learn == 2 and n >= 18)
        samples.append((rng.integers(0, cfg.Q, cfg.F), int(rng.integers(cfg.C)), learn, upd))
    exp = expected(T, L, samples)
    out, _ = simulate(d, "check_rand", stim_lines(cfg, chunks_per_word(T), T.to_words(st), samples))
    got = [r[1:] for r in parse_res(out)[0]]
    bad = [i for i, (g, e) in enumerate(zip(got, exp)) if g != e]
    print(f"random   : {len(got)}/{len(samples)} samples simulated, mismatches {len(bad)} {bad[:5]}")
    # 2) real windows, offline-trained state, then a short learning stream
    L = trained_learner(T, data)
    idx = np.linspace(0, len(yr) - 1, 12).astype(int)
    real = [(xr[i], int(yr[i]), int(cfg.learn > 0 and k >= 6), int(cfg.learn == 2 and k >= 6))
            for k, i in enumerate(idx)]
    words = preload_words(T, L)
    exp2 = expected(T, L, real)
    out, _ = simulate(d, "check_real", stim_lines(cfg, chunks_per_word(T), words, real))
    got2 = [r[1:] for r in parse_res(out)[0]]
    bad2 = [i for i, (g, e) in enumerate(zip(got2, exp2)) if g != e]
    print(f"real data: {len(got2)}/{len(real)} samples simulated, mismatches {len(bad2)} {bad2[:5]}")
    ok = not bad and not bad2 and len(got) == len(samples) and len(got2) == len(real)
    print("GATE-LEVEL MATCH" if ok else "GATE-LEVEL MISMATCH")
    return int(not ok)


# ----------------------------------------------------------------------------- power
STA = """read_liberty {lib}
read_verilog {nl}
link_design hdc_chip
read_sdc {sdc}
read_spef {spef}
read_vcd -scope gls_tb/dut {vcd}
report_power -digits 6
report_power -instances [get_cells *] -digits 6 -limit 0
"""


def sta_power(d, vcd, tag):
    run = d / "runs" / "run" / "final"
    lib = pdk_file("libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib")
    tcl = vcd.parent / f"power_{tag}.tcl"
    tcl.write_text(STA.format(lib=lib, nl=run / "nl" / "hdc_chip.nl.v", sdc=run / "sdc" / "hdc_chip.sdc",
                              spef=run / "spef" / "nom" / "hdc_chip.nom.spef", vcd=vcd).replace(
        "report_power -instances [get_cells *] -digits 6 -limit 0\n", ""))
    mounts = sorted({str(ROOT), str(PDK_ROOT.resolve())})
    cmd = ["docker", "run", "--rm", "-u", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
    for m in mounts:
        cmd += ["-v", f"{m}:{m}"]
    cmd += [IMAGE, "sta", "-no_init", "-exit", str(tcl)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    (vcd.parent / f"power_{tag}.rpt").write_text(out.stdout + out.stderr)
    m = re.search(r"^Total\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)", out.stdout, re.M)
    groups = {g: [float(v) for v in vals.split()[:4]] for g, vals in
              re.findall(r"^(Sequential|Combinational|Clock|Macro|Pad)\s+(.*)$", out.stdout, re.M)}
    if not m:
        raise RuntimeError("could not parse report_power:\n" + (out.stdout + out.stderr)[-3000:])
    return dict(internal_w=float(m.group(1)), switching_w=float(m.group(2)),
                leakage_w=float(m.group(3)), total_w=float(m.group(4)), groups=groups)


def cmd_power(d):
    T = setup_model(d)
    cfg = T.CFG
    data = T.data.load(cfg.F, cfg.Q)
    xr, yr, sr = data["test"]
    # windows spread over the recordings of the first N_POWER_USERS unseen users
    subjects = sorted(set(sr.tolist()))[:N_POWER_USERS]
    per_user = max(1, N_POWER_SAMPLES // len(subjects))
    pick = np.concatenate([np.flatnonzero(sr == sj)[np.linspace(0, int((sr == sj).sum()) - 1, per_user).astype(int)] for sj in subjects])
    results = {}
    for phase, name in ((1, "infer"), (2, "learn")):
        if phase == 2 and not cfg.learn:
            continue
        L = trained_learner(T, data)
        samples = [(xr[i], int(yr[i]), int(phase == 2), int(cfg.learn == 2)) for i in pick]
        exp = expected(T, L, samples)
        stim = stim_lines(cfg, chunks_per_word(T), preload_words(T, trained_learner(T, data)), samples, phase)
        out, bdir = simulate(d, f"power{POWER_TAG}_{name}", stim)
        res, win = parse_res(out)
        match = [r[1:] for r in res] == exp
        t_ns = (win[1] - win[0]) / 1000.0
        vcd = bdir / f"gls_{name}.vcd"
        t0 = time.time()
        pw = sta_power(d, vcd, name)
        vcd_mb = round(vcd.stat().st_size / 2 ** 20, 1)
        if not os.environ.get("GLS_KEEP_VCD"):
            vcd.unlink()                                   # the dump can be a gigabyte; the numbers are in the json
        n = len(samples)
        updates = sum(e[1] for e in exp)
        results[name] = dict(samples=n, updates=updates, window_ns=t_ns, cycles=round(t_ns / CLK_NS),
                             vcd_mb=vcd_mb, model_match=match,
                             **pw, energy_per_sample_nj=pw["total_w"] * t_ns / n)
        print(f"{name:6s}: {n} samples, {results[name]['cycles']} cycles, match={match}, "
              f"P={pw['total_w'] * 1e3:.2f} mW (int {pw['internal_w'] * 1e3:.2f}, sw "
              f"{pw['switching_w'] * 1e3:.2f}, leak {pw['leakage_w'] * 1e6:.1f} uW), "
              f"E/sample={results[name]['energy_per_sample_nj']:.1f} nJ  [sta {time.time() - t0:.0f}s]",
              flush=True)
    out = ROOT / "results" / f"power{POWER_TAG}_{d.name}.json"
    out.write_text(json.dumps(dict(design=d.name, clock_ns=CLK_NS, corner="nom_tt_025C_1v80",
                                   subjects=[int(x) for x in subjects], windows_per_phase=int(len(pick)), phases=results), indent=2, default=float))
    print("saved", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_dir")
    ap.add_argument("mode", choices=["check", "power"])
    a = ap.parse_args()
    d = pathlib.Path(a.design_dir).resolve()
    t0 = time.time()
    rc = cmd_check(d) if a.mode == "check" else cmd_power(d)
    print(f"({time.time() - t0:.0f}s)")
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
