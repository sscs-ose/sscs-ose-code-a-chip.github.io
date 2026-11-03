"""Source-bound post-route workload replay and model power for the new tasks."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from capacity_integration_physical import CASE, PERIOD_PS, verified_integration
from check_capacity_waveforms import check as check_waveforms
from study_protocol import digest, write_json

sys.path.append(str(CASE/"scripts"))
from export_study_sta_views import export
from run_postroute_workloads import power, source_views


def activity_bench(bench):
    replacements = (
        ("    #2.631;", "    #5.263;"),
        ("    #5.263;\n    imem_rdata", "    #1;\n    imem_rdata"),
        ("    clk = 0;\n    #2.632;", "    #4.263;\n    clk = 0;"),
        ("    step(); step();\n    rst_n = 1;",
         '    step(); step(); step();\n    rst_n = 1;\n'
         '    $display("ACTIVITY_START_PS=%0t", $realtime);'),
        ("  string image_file;", "  string vcd_file;\n  string image_file;"),
        ("    trace_fd = 0;", '    if (!$value$plusargs("VCD=%s", vcd_file)) $fatal(1,"VCD required");\n'
         '    $dumpfile(vcd_file);\n    $dumpvars(0, dut);\n    trace_fd = 0;'),
        ('    $display("CPU_ELF_PASS', '    $display("ACTIVITY_END_PS=%0t", $realtime);\n'
         '    $display("CPU_ELF_PASS'),
    )
    for old, new in replacements:
        if bench.count(old) != 1:
            raise ValueError("Unexpected testbench revision: "+old)
        bench = bench.replace(old, new)
    return bench


def workload_replay(task_name, output, sources, *, views=None, models=None):
    source, frozen = verified_integration(task_name)
    if output.exists():
        raise ValueError("Prior measurement retained")
    output.mkdir(parents=True)
    commands = []

    def execute(name, argv, timeout):
        start = time.monotonic()
        with (output/(name+".log")).open("w") as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        commands.append(dict(name=name, argv=argv, exit_code=result.returncode,
                             elapsed_seconds=time.monotonic()-start))
        write_json(output/"commands.json", commands)
        if result.returncode:
            raise RuntimeError("Workload command failed: "+name)

    bench = output/"gate_tb.sv"
    bench.write_text(activity_bench((source/"verification/tb_cpu_npu.sv").read_text()))
    obj = output/"obj"
    execute("compile", ["verilator", "--binary", "--timing", "--assert", "--trace",
        "--trace-underscore", "--trace-depth", "3", "-Wno-fatal", "-j", "2",
        "--top-module", "tb_cpu_elf", "--Mdir", str(obj),
        *([str(models)] if models else []), *map(str, sources), str(bench)], 900)
    rows = []
    for name in ("short", "mixed", "long"):
        folder = output/name
        shutil.copytree(source/"workloads"/name, folder)
        meta = json.loads((folder/"workload.json").read_text())
        vcd = folder/"activity-full.vcd"
        trace = folder/"trace.jsonl"
        execute(name, [str(obj/"Vtb_cpu_elf"), f"+IMAGE={folder/'memory.hex'}",
            f"+TRACE={trace}", f"+VCD={vcd}", "+SEED=20261021", "+MAX_CYCLES=200000"], 300)
        log = (output/(name+".log")).read_text()
        result = re.search(r"CPU_ELF_PASS cycles=(\d+) commits=(\d+) traps=(\d+)", log)
        if not result or int(result[3]) != 0:
            raise ValueError("Firmware/oracle/trap check failed: "+name)
        start = int(re.search(r"ACTIVITY_START_PS=(\d+)", log)[1])
        end = int(re.search(r"ACTIVITY_END_PS=(\d+)", log)[1])
        if end <= start:
            raise ValueError("Invalid workload measurement window")
        useful = meta["useful_macs" if task_name.startswith("A") else "useful_transactions"]
        rows.append(dict(workload=name, passed=True, cycles=int(result[1]),
            activity_start_ps=start, activity_end_ps=end, activity_duration_ps=end-start,
            latency_seconds=(end-start)*1e-12, useful_work=useful,
            useful_work_unit="signed_int8_mac" if task_name.startswith("A") else "memory_transaction",
            throughput_per_second=useful/((end-start)*1e-12),
            vcd=str(vcd.relative_to(output)), vcd_sha256=digest(vcd),
            memory_sha256=digest(folder/"memory.hex"), workload_sha256=digest(folder/"workload.json"),
            checks="Frozen self-checking firmware and independent memory/checksum monitor"))
    summary = dict(complete=True, passed=True, task=task_name, rows=rows,
        clock_period_ns=PERIOD_PS/1000, clock_duty_percent=50,
        reset_low_ns=3*PERIOD_PS/1000, reset_release_phase_ns=PERIOD_PS/2000,
        integration_sha256=frozen["source_sha256"], adapted_bench_sha256=digest(bench),
        gate_level=views is not None, power_complete=False)
    if views is not None:
        summary.update(snapshot_id=views["snapshot"]["snapshot_id"],
            source_evidence=os.path.relpath(views["source"], output),
            source_view_sha256=views["hashes"], liberty_sha256=views["snapshot"]["liberty_sha256"],
            netlist_sha256=digest(views["paths"]["netlist"]), cell_models_sha256=digest(models))
    write_json(output/"summary.json", summary)
    write_json(output/"waveform-audit.json", check_waveforms(output))
    return summary


def measure(run, task_name):
    if (run/"workloads").exists() or (run/"postroute/qualification.json").exists():
        raise ValueError("Existing post-route measurement retained")
    export(run)
    views = source_views(run/"evidence")
    if views["period_ps"] != PERIOD_PS:
        raise ValueError("Candidate clock differs from frozen 95 MHz period")
    library = CASE/"toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
    models = run/"postroute/cell_models.v"
    models.parent.mkdir()
    with (models.parent/"models.log").open("w") as log:
        result = subprocess.run(["yosys", "-Q", "-T", "-p",
            f"read_liberty -ignore_miss_func {library}; write_verilog -noattr {models}"],
            stdout=log, stderr=subprocess.STDOUT, timeout=120)
    if result.returncode:
        raise RuntimeError("Liberty cell model extraction failed")
    workload_replay(task_name, run/"workloads", [views["paths"]["netlist"]], views=views, models=models)
    power(run/"workloads")
    summary = json.loads((run/"workloads/summary.json").read_text())
    for row in summary["rows"]:
        row["energy_per_useful_work_j"] = row["estimated_energy_j"]/row["useful_work"]
    summary["power_scope"] = (
        "Liberty-model power from actual post-route netlist activity and extracted SPEF; "
        "no SDF/glitch or silicon measurement. Window runs from reset release until "
        "all required CPU and accelerator work completes.")
    write_json(run/"workloads/summary.json", summary)
    record = dict(passed=summary["passed"] and summary["measurement_qualified"],
        waveform_audit_passed=True, source_view_sha256=views["hashes"],
        summary="workloads/summary.json", clock_period_ns=PERIOD_PS/1000,
        scope=summary["power_scope"])
    write_json(run/"postroute/qualification.json", record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--task", required=True, choices=("A1", "A2", "B1", "B2"))
    args = parser.parse_args()
    print(json.dumps(measure(args.run.resolve(), args.task)))
