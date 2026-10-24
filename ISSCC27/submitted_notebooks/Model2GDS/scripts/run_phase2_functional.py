#!/usr/bin/env python3
"""Record one immutable 2/4/8 functional attempt; no synthesis or physical tools."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model.golden import gemm
from model.systolic_generic import ARRAY_SIZES, simulate
from scripts.generate_phase2_wrappers import render_wrapper
from scripts.phase1_common import capture, seal, sha256, write_new

PHASE1_COMMIT = "ae309e3183608a52efb3b7feb4813c4942b03637"
ORACLES = {
    "vectors.json": "results/raw/phase1/REG_001/vectors.json",
    "vectors.txt": "results/raw/phase1/REG_001/vectors.txt",
    "reference.json": "results/raw/phase1/REG_001/reference.json",
    "rtl_results.jsonl": "results/raw/phase1/REG_001/rtl_results.jsonl",
}
SOURCES = (
    "model/__init__.py", "model/arithmetic.py", "model/golden.py", "model/systolic.py",
    "model/systolic_generic.py", "rtl/gemm_pe.sv", "rtl/systolic_array.sv",
    "verification/phase2_sim_main.cpp", "scripts/phase1_common.py",
    "scripts/collect_phase1_verification.py", "scripts/generate_phase2_wrappers.py",
    "scripts/run_phase2_functional.py", "scripts/collect_phase2_functional.py",
    "tests/test_phase2_functional.py", "docs/PHASE1_MICROARCHITECTURE.md",
    "docs/PHASE2_FUNCTIONAL_CONTRACT.md", "PROJECT_FREEZE.json",
)


def compile_argv(root, run, size, verilator):
    directory = run / f"S{size}"
    return [verilator, "--cc", "--exe", "--build", "-j", "2", "-Wall", "-Wno-PINCONNECTEMPTY",
            "--top-module", "phase2_sim_top", "--Mdir", str(directory / "tmp/obj_dir"),
            "-CFLAGS", f"-std=c++17 -DARRAY_SIZE={size}", str(root / "rtl/gemm_pe.sv"),
            str(root / "rtl/systolic_array.sv"), str(directory / "phase2_sim_top.sv"),
            str(root / "verification/phase2_sim_main.cpp")]


def _copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(source.read_bytes())


def collect_run(root, run_id):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_]+", run_id):
        raise ValueError("run ID must contain only letters, digits and underscores")
    run = root / "results/raw/phase2/functional" / run_id
    run.mkdir(parents=True, exist_ok=False)
    stage = "setup"
    size = None
    try:
        verilator = shutil.which("verilator")
        write_new(run / "invocation.json", {
            "argv": [sys.executable, *sys.argv], "cwd": str(root),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "verilator_executable": verilator, "python_version": sys.version,
            "platform": sys.platform, "path": os.environ.get("PATH", ""),
        })
        for name, argv in [("git_head", ["git", "rev-parse", "HEAD"]),
                           ("git_status", ["git", "status", "--porcelain=v1"]),
                           ("git_diff", ["git", "diff", "--no-ext-diff", "--binary"])]:
            if capture(root, run, name, argv)["returncode"]:
                raise RuntimeError(name + " failed")
        sources = []
        for relative in SOURCES:
            source, target = root / relative, run / "snapshots" / relative
            _copy(source, target)
            sources.append({"path": relative, "snapshot": target.relative_to(run).as_posix(),
                            "sha256": sha256(target), "bytes": target.stat().st_size})
        write_new(run / "source_manifest.json", {"files": sources})
        inputs = []
        for filename, relative in ORACLES.items():
            target = run / "phase1_oracles" / filename
            _copy(root / relative, target)
            inputs.append({"original_path": relative, "snapshot": target.relative_to(run).as_posix(),
                           "sha256": sha256(target), "bytes": target.stat().st_size})
        write_new(run / "oracle_manifest.json", {"phase1_commit": PHASE1_COMMIT, "files": inputs})
        cases = json.loads((run / "phase1_oracles/vectors.json").read_text())["cases"]
        old_reference = {x["case_id"]: x for x in json.loads(
            (run / "phase1_oracles/reference.json").read_text())["cases"]}
        write_new(run / "manifest.json", {
            "schema_version": 1, "run_id": run_id, "array_sizes": list(ARRAY_SIZES),
            "phase1_commit": PHASE1_COMMIT, "case_count_per_array": len(cases),
            "case_ids": [case["case_id"] for case in cases],
            "contract_sha256": sha256(root / "docs/PHASE2_FUNCTIONAL_CONTRACT.md"),
            "purpose": "Parameterized functional qualification only; no ranking or physical result",
        })
        stage = "tool_diagnosis"
        if not verilator:
            raise FileNotFoundError("host Verilator not found")
        for name, argv in [("verilator_version", [verilator, "--version"]),
                           ("verilator_configuration", [verilator, "-V"]),
                           ("compiler_version", ["g++", "--version"]),
                           ("python_version", [sys.executable, "--version"])]:
            if capture(root, run, name, argv)["returncode"]:
                raise RuntimeError(name + " failed")
        for size in ARRAY_SIZES:
            directory = run / f"S{size}"
            directory.mkdir()
            stage = "reference_generation"
            references = []
            for case in cases:
                golden = gemm(case["A"], case["B"])
                if golden != old_reference[case["case_id"]]["golden"]:
                    raise AssertionError("Golden differs from immutable Phase 1: " + case["case_id"])
                references.append({"case_id": case["case_id"], "golden": golden,
                                   "model": simulate(case["A"], case["B"], size)})
            write_new(directory / "reference.json", {"array_size": size, "cases": references})
            wrapper = directory / "phase2_sim_top.sv"
            with wrapper.open("xb") as stream:
                stream.write(render_wrapper(size, physical=False).encode("utf-8"))
            stage = "compile"
            (directory / "tmp/obj_dir").mkdir(parents=True)
            if capture(root, directory, "compile", compile_argv(root, run, size, verilator))["returncode"]:
                raise RuntimeError("Verilator compile failed; attribution requires preserved diagnostics")
            binary = directory / "simulator/phase2_sim"
            _copy(directory / "tmp/obj_dir/Vphase2_sim_top", binary)
            shutil.copymode(directory / "tmp/obj_dir/Vphase2_sim_top", binary)
            stage = "simulation"
            command = [binary, run / "phase1_oracles/vectors.txt",
                       directory / "rtl_results.jsonl", directory / "array_tests.json"]
            if capture(root, directory, "execute", command)["returncode"]:
                raise RuntimeError("RTL harness failed; attribution requires preserved diagnostics")
        stage = "source_identity"
        for source in sources:
            if sha256(root / source["path"]) != source["sha256"]:
                raise RuntimeError("Source changed during functional collection: " + source["path"])
        write_new(run / "outcome.json", {"status": "COLLECTED", "stage": stage,
                                         "failure_classification": None})
        code = 0
    except Exception as exc:
        classification = ("TOOLCHAIN_OR_ENVIRONMENT_FAILURE" if isinstance(exc, OSError)
                          or stage in ("setup", "tool_diagnosis") else "UNKNOWN_FAILURE")
        write_new(run / "outcome.json", {"status": "FAIL", "stage": stage, "array_size": size,
                                         "error": str(exc), "traceback": traceback.format_exc(),
                                         "failure_classification": classification,
                                         "interpretation": "Engineering attempt only; not a research result"})
        print(traceback.format_exc(), file=sys.stderr)
        code = 1
    seal(run)
    print(json.dumps({"run": run.relative_to(root).as_posix(), "returncode": code}))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    return collect_run(ROOT, args.run_id)


if __name__ == "__main__":
    sys.exit(main())
