#!/usr/bin/env python3
"""Frozen public development smoke checks; full acceptance is separate."""
from pathlib import Path
import argparse, json, subprocess, time

def run(command, cwd, timeout):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    print(result.stdout, end="")
    print(result.stderr, end="")
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(map(str, command)))
    return result.stdout

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("kind", choices=["npu","cpu","integration"])
    args=parser.parse_args()
    root=Path.cwd()
    build=root/"build"/args.kind
    build.mkdir(parents=True,exist_ok=True)
    sources=sorted((root/"rtl"/"cpu").glob("*.sv"))+sorted((root/"rtl"/"npu").glob("*.sv"))
    if args.kind=="npu":
        sources=sorted((root/"rtl"/"npu").glob("*.sv"))
        run(["iverilog","-g2012","-s","npu_smoke_tb","-o",str(build/"sim"),*map(str,sources),"tb/npu_smoke_tb.sv"],root,120)
        output=run(["vvp",str(build/"sim")],root,120)
        if "NPU_SMOKE_PASS" not in output: raise RuntimeError("No explicit NPU verdict")
    elif args.kind=="cpu":
        run(["verilator","--binary","--timing","--assert","-Wno-fatal","-j","2",
             "--top-module","tb_T09","--Mdir",str(build/"obj"),*map(str,sources),"tb/public_cpu_tb.sv"],root,240)
        output=run([str(build/"obj"/"Vtb_T09")],root,60)
        if "PUBLIC_PASS T09" not in output: raise RuntimeError("No explicit CPU verdict")
        print("CPU_SMOKE_PASS")
    else:
        sources+=sorted((root/"rtl"/"integration").glob("*.sv"))
        run(["verilator","--lint-only","--timing","-Wno-fatal","--top-module","nebula_cpu_npu_top",*map(str,sources)],root,120)
        print("INTEGRATION_SMOKE_PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
