#!/usr/bin/env python3
"""Server-only meaningful handshake/decoder regression; ADC in TB is a fixture."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import flow2_integration_common as common
from scripts import run_flow2_acquisition_layout as acq


def run(root, *, tag="wrapper_rtl_20261020_01", execute=False, timeout_s=300):
    root=Path(root).resolve();common.tag_ok(tag)
    report={"status":"PREPARED", "scope":"RTL transaction regression; testbench ADC is not analog evidence"}
    if not execute:return report
    if sys.platform!="linux":raise RuntimeError("native regression runs on Linux server only")
    tool=shutil.which("verilator")
    if not tool:raise FileNotFoundError("server Verilator missing")
    paths=[root/"rtl/automx_cim_readout_seq.sv",root/"tests/rtl/tb_flow2_readout_seq.sv"]
    identity={"sources":[acq._item(root,p) for p in paths],"tool":acq.stage5._tool_version("verilator",tool)}
    store=common.Store(root,tag,identity)
    try:
        cmd=[tool,"--binary","--timing","-Wno-fatal","--top-module","tb_flow2_readout_seq",
             "--Mdir",str(store.build/"compile/obj"),"-o","sim_wrapper_seq",*[str(p) for p in paths]]
        r,_=store.step("compile",cmd,executor=lambda work:acq.stage5._run(cmd,work,timeout_s))
        if r.returncode:raise RuntimeError("RTL compilation failed; inspect compile.log")
        binary=store.build/"compile/obj/sim_wrapper_seq"
        cmd=[str(binary)]
        r,_=store.step("simulate",cmd,executor=lambda work:acq.stage5._run(cmd,work,timeout_s))
        required=["RAW_CALIBRATION_BACKPRESSURE_PASS","ALL_39_SIGNED_LEVELS_PASS","TIMEOUT_PASS","STALE_EOC_PASS",
                  "SERIAL_CALIBRATION_NEIGHBORS_PASS"]
        if r.returncode or any("AUTOMX_WRAPPER_RTL="+v not in r.stdout for v in required):
            raise RuntimeError("RTL scenario failed; inspect simulate.log")
        report.update(status="PASS_WRAPPER_RTL_TRANSACTIONS",scenarios=required,inputs=identity)
    except Exception as error:
        report.update(status="BLOCKED_WRAPPER_RTL",error=f"{type(error).__name__}: {error}")
    finally:
        common.save_summary(store.folder/"summary.json",report)
        common.bundle(root,tag,identity["sources"])
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--tag",default="wrapper_rtl_20261020_01");p.add_argument("--run",action="store_true")
    a=p.parse_args();r=run(a.root,tag=a.tag,execute=a.run);print(json.dumps(r,indent=2))
    if a.run and r["status"]!="PASS_WRAPPER_RTL_TRANSACTIONS":raise SystemExit(1)
