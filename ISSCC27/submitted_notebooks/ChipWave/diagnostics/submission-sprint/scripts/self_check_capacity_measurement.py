"""Qualify new workload windows with actual RTL waves, without physical/model calls."""
import json
from pathlib import Path

from capacity_integration_physical import ROOT, verified_integration
from check_capacity_waveforms import check as check_waveforms
from measure_capacity_integration import activity_bench, workload_replay
from study_protocol import write_json


def check():
    output = ROOT/"checks/integration-measurement-preflight"
    if output.exists():
        raise ValueError("Previous actual waveform preflight retained")
    output.mkdir()
    rows = []
    for task in ("A1", "A2", "B1", "B2"):
        source, _ = verified_integration(task)
        bench = (source/"verification/tb_cpu_npu.sv").read_text()
        try:
            activity_bench(bench.replace("    #2.631;", "    #99;"))
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected clock revision accepted")
        summary = workload_replay(task, output/task, sorted((source/"rtl").rglob("*.sv")))
        assert not summary["gate_level"] and not summary["power_complete"]
        assert all(r["useful_work"] > 0 and r["latency_seconds"] > 0 for r in summary["rows"])
        original = (output/task/"summary.json").read_text()
        damaged = json.loads(original)
        damaged["rows"][0]["vcd_sha256"] = "0"*64
        try:
            write_json(output/task/"summary.json", damaged)
            try:
                check_waveforms(output/task)
            except AssertionError:
                pass
            else:
                raise AssertionError("Unbound activity file accepted")
        finally:
            (output/task/"summary.json").write_text(original)
        rows.append(dict(task=task, passed=True, workloads=len(summary["rows"]),
                         measured_clock_ns=summary["clock_period_ns"]))
        print(json.dumps(rows[-1]), flush=True)
    result = dict(passed=True, model_calls=0, physical_attempts=0, rows=rows,
        scope="RTL functional workload replay and actual VCD window/clock checks; not post-route power",
        rejected=["unexpected clock template", "activity hash substitution"])
    write_json(ROOT/"checks/integration-measurement.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(check()))
