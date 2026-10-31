"""Build and locally check task references; physical/integration remain separate."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import capacity_memory
import capacity_dot
from study_protocol import digest, write_json


def simulate(source, bench, out, *, deadline=None):
    from capacity_process import run_group,remaining
    out.mkdir(parents=True, exist_ok=False)
    cmds = [["iverilog", "-g2012", "-s", "benchmark_check_tb", "-o", str(out/"sim"),
             str(source), str(bench)], ["vvp", str(out/"sim")]]
    codes = []
    text = ""
    start = time.monotonic()
    for name, command in zip(("compile", "run"), cmds):
        try:
            result = run_group(command, text=True, capture_output=True, timeout=remaining(deadline,60))
            text = result.stdout + result.stderr
            codes.append(result.returncode)
        except subprocess.TimeoutExpired:
            text = "TIMEOUT"
            codes.append(124)
        (out / (name+".log")).write_text(text)
        if codes[-1]:
            break
    row = dict(compiled=codes[0] == 0, passed=codes == [0, 0] and "BENCHMARK_PASS" in text,
               exit_codes=codes, seconds=time.monotonic()-start,
               source_sha256=digest(source), checker_sha256=digest(bench))
    write_json(out / "result.json", row)
    return row


def run(root, family):
    rows = []
    template = capacity_memory if family == "memory" else capacity_dot
    prefix = "B" if family == "memory" else "A"
    top = "capacity_" + family
    for task, slots in ((prefix+"1", 1), (prefix+"2", 4)):
        folder = root / "tasks" / task
        if folder.exists():
            raise ValueError("Existing task revision is preserved: " + str(folder))
        public, grader = folder / "agent", folder / "grader"
        for name in ("spec", "rtl", "tb"):
            (public/name).mkdir(parents=True)
        (grader/"mutants").mkdir(parents=True)
        (public / "spec/task.md").write_text("# "+task+"\n\n"+template.contract(slots))
        write_json(public/"spec/interface.json", dict(top=top, ports=[
            dict(direction=d, name=n, width=w) for d, n, w in template.PORTS]))
        (public/"tb/development_tb.sv").write_text(template.checker(slots, False))
        source, bench = grader/"reference.sv", grader/"final_tb.sv"
        source.write_text(template.reference(slots))
        bench.write_text(template.checker(slots, True))
        final = simulate(source, bench, folder/"qualification/reference-final")
        dev = simulate(source, public/"tb/development_tb.sv", folder/"qualification/reference-development")
        faults = {}
        for name, code in template.mutants(slots).items():
            path = grader/"mutants"/(name+".sv")
            path.write_text(code)
            row = simulate(path, bench, folder/"qualification/mutants"/name)
            row["detected"] = row["compiled"] and not row["passed"] and row["exit_codes"][-1] not in (0, 124)
            faults[name] = row
        out = folder/"qualification"
        synthesis = subprocess.run(["yosys", "-Q", "-T", "-p",
            f"read_slang --top {top} {source}; proc; memory_map; opt; check -assert; stat"],
            text=True, capture_output=True, timeout=120)
        (out/"synthesis.log").write_text(synthesis.stdout+synthesis.stderr)
        record = dict(task=task, reference_final=final, reference_development=dev,
                      mutants=faults, synthesis_exit_code=synthesis.returncode,
                      local_checks_passed=final["passed"] and dev["passed"] and synthesis.returncode==0
                        and all(r["detected"] for r in faults.values()),
                      qualification_complete=False,
                      pending=["CSIR contract", "additional stability/progress/formal properties",
                               "CPU integration", "reference physical and workload qualification"],
                      source_manifest={str(p.relative_to(folder)):digest(p) for p in folder.glob("grader/**/*.sv")})
        write_json(out/"qualification.json", record)
        rows.append(record)
        print(json.dumps(dict(task=task, local_checks_passed=record["local_checks_passed"],
                              mutants_detected=sum(r["detected"] for r in faults.values()))), flush=True)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("memory", "dot"), required=True)
    args = parser.parse_args()
    rows = run(Path(__file__).resolve().parents[1], args.family)
    if not all(row["local_checks_passed"] for row in rows):
        raise SystemExit(1)
