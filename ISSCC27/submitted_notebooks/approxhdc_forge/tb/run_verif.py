"""Regression: generate RTL for every configuration, simulate with cocotb, record results.

    python tb/run_verif.py                 # full matrix -> results/verification.csv
    python tb/run_verif.py --quick         # 3 small configs, fewer vectors
    python tb/run_verif.py --vcd           # also dump VCDs of real-sample runs -> results/vcd/
    python tb/run_verif.py --sim icarus    # cross-check with Icarus Verilog
"""
import argparse
import csv
import json
import os
import pathlib
import shutil
import sys
import time
from dataclasses import asdict

from cocotb_tools.runner import get_results, get_runner

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rtlgen import RTLConfig, generate_chip, write  # noqa: E402

TOP = "approxhdc_top"
BASE = dict(D=512, P=64, F=64, Q=16, C=6)

MATRIX = (
    # inference-only, every similarity variant
    [dict(variant="exact", knob=0, learn=0)]
    + [dict(variant="trunc", knob=k, learn=0) for k in (1, 2, 3)]
    + [dict(variant="satcomp", knob=k, learn=0) for k in (3, 2, 1)]
    + [dict(variant="sampled", knob=k, learn=0) for k in (6, 4, 2)]
    # learning: modes, counter widths, stochastic updates, approximation in the loop
    + [dict(learn=1, w=4, k=0), dict(learn=2, w=8, k=0), dict(learn=2, w=4, k=3),
       dict(learn=2, w=2, k=4), dict(learn=2, w=3, k=1),
       dict(learn=2, w=8, k=0, variant="trunc", knob=1),
       dict(learn=2, w=4, k=2, variant="satcomp", knob=2),
       dict(learn=2, w=8, k=0, variant="sampled", knob=4)]
    # slice width / dimension corners: P=32, P=128, fully parallel P=D, odd F (no ties), seed
    + [dict(P=32, learn=2, w=4, k=3), dict(P=128, learn=2, w=8, k=0),
       dict(D=256, P=256, learn=2, w=4, k=3), dict(D=256, P=256, learn=0),
       dict(F=33, Q=8, learn=2, w=6, k=2), dict(D=1024, P=64, learn=2, w=8, k=0, seed=5)]
    # clock-gated ring memory: the three final-chip styles, error-driven with stochastic updates,
    # and the single-word ring corner (P = D)
    + [dict(P=32, variant="satcomp", knob=2, learn=1, w=2, k=0, cg=1),
       dict(P=32, variant="satcomp", knob=2, learn=0, cg=1),
       dict(P=64, learn=2, w=4, k=3, cg=1),
       dict(D=256, P=256, learn=2, w=4, k=3, cg=1)]
)
CHIP = [dict(P=32, learn=2, w=4, k=3), dict(D=256, learn=0), dict(D=256, P=32, learn=1, w=3, k=0),
        dict(D=256, P=256, learn=2, w=8, k=0),
        dict(P=32, variant="satcomp", knob=2, learn=1, w=2, k=0, cg=1), dict(D=256, P=64, learn=0, cg=1)]
QUICK = [dict(variant="exact", knob=0, learn=0), dict(learn=2, w=4, k=3),
         dict(D=256, P=256, learn=1, w=4, k=0)]
VCD_CFGS = [dict(learn=0), dict(learn=2, w=8, k=0), dict(learn=2, w=4, k=3)]


def run_one(cfg, sim, n, waves=False, testcase=None, chip=False):
    name = ("chip_" if chip else "") + cfg.name + ("_vcd" if waves else "") + f"_{sim}"
    bdir = ROOT / "sim_build" / name
    bdir.mkdir(parents=True, exist_ok=True)
    top, module = ("hdc_chip", "test_chip") if chip else (TOP, "test_hdc")
    if chip:
        vfile = bdir / f"{cfg.name}_chip.v"
        vfile.write_text(generate_chip(cfg))
    else:
        vfile = write(cfg, bdir / f"{cfg.name}.v", TOP)
    runner = get_runner(sim)
    build_args = ["-Wno-fatal", "-Wno-lint", "-Wno-style", "-O3"] if sim == "verilator" else []
    t0 = time.time()
    runner.build(sources=[vfile], hdl_toplevel=top, build_dir=bdir, build_args=build_args,
                 timescale=("1ns", "1ps"),   # the generated RTL has no `timescale; Icarus would default to 1 s
                 waves=waves, always=True)
    env = {"HDC_CFG": json.dumps(asdict(cfg)), **{k: str(v) for k, v in n.items()},
           "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT / "tb")])}
    xml = runner.test(hdl_toplevel=top, test_module=module, test_dir=bdir,
                      build_dir=bdir, extra_env=env, waves=waves, testcase=testcase)
    ntests, nfail = get_results(xml)
    return name, ntests, nfail, time.time() - t0, bdir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--vcd", action="store_true")
    ap.add_argument("--vcd-only", action="store_true", help="skip the matrix, only dump VCDs")
    ap.add_argument("--sim", default="verilator")
    ap.add_argument("--only", type=int, default=None, help="run only this matrix index")
    ap.add_argument("--chip", action="store_true", help="test the chip top (staged load port)")
    a = ap.parse_args()
    cfgs = CHIP if a.chip else QUICK if a.quick else MATRIX
    if a.only is not None:
        cfgs = [cfgs[a.only]]
    n = dict(N_RAND=40, N_REAL=10, N_STREAM=40) if a.quick else dict(N_RAND=200, N_REAL=50, N_STREAM=150)
    rows = []
    for c in ([] if a.vcd_only else cfgs):
        cfg = RTLConfig(**{**BASE, **c})
        name, nt, nf, dt, _ = run_one(cfg, a.sim, n, chip=a.chip)
        rows.append(dict(config=cfg.name, sim=a.sim, tests=nt, failed=nf, seconds=round(dt, 1),
                         **{k: str(v) for k, v in n.items()}))
        print(f"{'PASS' if nf == 0 else 'FAIL'}  {cfg.name:50s} tests={nt} failed={nf} {dt:.0f}s",
              flush=True)
    if a.vcd or a.vcd_only:
        vdir = ROOT / "results" / "vcd"
        vdir.mkdir(parents=True, exist_ok=True)
        for c in VCD_CFGS:
            cfg = RTLConfig(**{**BASE, **c})
            tc = "test_learning_stream" if cfg.learn else "test_real_inference"
            name, nt, nf, dt, bdir = run_one(cfg, a.sim, dict(N_REAL=50, N_STREAM=50), True, tc)
            dumps = sorted(bdir.glob("*.vcd")) + sorted(bdir.glob("*.fst"))
            for dmp in dumps:
                shutil.copy(dmp, vdir / f"{cfg.name}_{tc}{dmp.suffix}")
            print(f"VCD   {cfg.name:50s} failed={nf} -> {[p.name for p in dumps]}", flush=True)
    out = ROOT / "results" / ("verification_quick.csv" if a.quick else
                              f"verification_{'chip_' if a.chip else ''}{a.sim}.csv")
    if a.only is None and rows:
        with out.open("w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        print(f"\n{sum(r['failed'] == 0 for r in rows)}/{len(rows)} configurations pass -> {out}")
    sys.exit(int(any(r["failed"] for r in rows)))


if __name__ == "__main__":
    main()
