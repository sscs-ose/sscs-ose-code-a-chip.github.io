#!/usr/bin/env python3
"""Parse sealed Phase 2 functional evidence, including Phase 1 compatibility."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model.golden import gemm
from model.systolic_generic import ARRAY_SIZES, simulate
from scripts.collect_phase1_verification import decode, contained, integer, keyed, matrix, DIRECTED_IDS
from scripts.generate_phase2_wrappers import render_wrapper
from scripts.phase1_common import canonical_bytes, sha256
from scripts.run_phase2_functional import ORACLES, PHASE1_COMMIT, SOURCES

# Exact names are the fixed directed-array checks in the independently written harness.
ARRAY_TEST_NAMES = {"array_synchronous_reset_priority", "array_registered_wavefront_bubble",
                    "array_masked_completion_clear", "array_last_requires_both"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_commands(cwd, run_relative, size, verilator, python):
    base = cwd.replace("\\", "/").rstrip("/")
    run = base + "/" + run_relative
    directory = run + f"/S{size}"
    return {
        "compile": [verilator, "--cc", "--exe", "--build", "-j", "2", "-Wall", "-Wno-PINCONNECTEMPTY",
                    "--top-module", "phase2_sim_top", "--Mdir", directory + "/tmp/obj_dir",
                    "-CFLAGS", f"-std=c++17 -DARRAY_SIZE={size}", base + "/rtl/gemm_pe.sv",
                    base + "/rtl/systolic_array.sv", directory + "/phase2_sim_top.sv",
                    base + "/verification/phase2_sim_main.cpp"],
        "execute": [directory + "/simulator/phase2_sim", run + "/phase1_oracles/vectors.txt",
                    directory + "/rtl_results.jsonl", directory + "/array_tests.json"],
        "verilator_version": [verilator, "--version"], "verilator_configuration": [verilator, "-V"],
        "compiler_version": ["g++", "--version"], "python_version": [python, "--version"],
        "git_head": ["git", "rev-parse", "HEAD"], "git_status": ["git", "status", "--porcelain=v1"],
        "git_diff": ["git", "diff", "--no-ext-diff", "--binary"],
    }


def compare_case(vector, reference, rtl, size, old_reference, old_rtl):
    require(type(size) is int and size in ARRAY_SIZES, "unauthorized array size")
    case_id = vector["case_id"]
    m, n, k = (vector[key] for key in ("M", "N", "K"))
    require(all(integer(x, 1) for x in (m, n, k)), case_id + ": invalid dimensions")
    require(type(vector["array_size"]) is int and vector["array_size"] == 2,
            case_id + ": source inputs are not the unchanged Phase 1 vectors")
    for key, rows, cols in (("A", m, k), ("B", k, n)):
        require(matrix(vector[key], rows, cols) and
                all(-128 <= x <= 127 for row in vector[key] for x in row), case_id + ": invalid INT8 input")
    require(reference["case_id"] == rtl["case_id"] == old_reference["case_id"] == old_rtl["case_id"] == case_id,
            "case identity mismatch")
    model = reference["model"]
    geometry = [{"row": row, "col": col, "rows": min(size, m-row), "cols": min(size, n-col)}
                for row in range(0, m, size) for col in range(0, n, size)]
    for record in (model, rtl):
        require(all(type(record[key]) is int for key in ("M", "N", "K", "array_size")) and
                [record[key] for key in ("M", "N", "K", "array_size")] == [m, n, k, size],
                case_id + ": result configuration mismatch")
        require(integer(record["cycles"], 1), case_id + ": invalid cycles")
        require(isinstance(record["tiles"], list) and len(record["tiles"]) == len(geometry),
                case_id + ": tile count mismatch")
        for tile, expected in zip(record["tiles"], geometry):
            require(all(type(tile[key]) is int and tile[key] == expected[key] for key in expected),
                    case_id + ": tile geometry mismatch")
            require(integer(tile["cycles"], 1), case_id + ": invalid tile cycles")
        require(sum(tile["cycles"] for tile in record["tiles"]) == record["cycles"],
                case_id + ": tile/workload cycle sum differs")
    require(all(matrix(value, m, n) for value in (reference["golden"], model["C"], rtl["C"],
                                                 old_reference["golden"])), case_id + ": malformed INT32 matrix")
    numeric = reference["golden"] == model["C"] == rtl["C"] == old_reference["golden"]
    cycles = model["cycles"] == rtl["cycles"] and model["tiles"] == rtl["tiles"]
    compatibility = (all(rtl[key] == old_rtl[key] for key in
                         ("M", "N", "K", "array_size", "C", "cycles", "tiles")) if size == 2 else None)
    return {"case_id": case_id, "category": vector["category"], "seed": vector["seed"],
            "generation": vector["generation"], "M": m, "N": n, "K": k, "array_size": size,
            "input_sha256": hashlib.sha256(canonical_bytes({"A": vector["A"], "B": vector["B"]})).hexdigest(),
            "rtl_result_sha256": hashlib.sha256(canonical_bytes(rtl["C"])).hexdigest(),
            "numerical_match": numeric, "model_cycles": model["cycles"], "rtl_cycles": rtl["cycles"],
            "cycle_match": cycles, "tiles": rtl["tiles"], "phase1_compatibility": compatibility,
            "cycle_unit": "rising_clock_edges_including_tile_clear",
            "pass": numeric and cycles and compatibility is not False}


def collect(root, run):
    root, run = Path(root).resolve(), Path(run).resolve()
    result = {"schema_version": 1, "run_id": run.name, "status": "FAIL", "pass": False,
              "array_sizes": list(ARRAY_SIZES), "errors": [], "configurations": [], "raw_sources": [],
              "parser": {"path": "scripts/collect_phase2_functional.py", "sha256": sha256(__file__)}}
    try:
        require(run.parent == root / "results/raw/phase2/functional" and
                re.fullmatch(r"[A-Za-z0-9_]+", run.name), "invalid selected functional run")
        seal_data = decode((run / "seal.json").read_text(encoding="utf-8"))
        sealed = {}
        for entry in seal_data["files"]:
            relative = entry["path"]
            path = contained(run, relative)
            require(relative not in sealed and integer(entry["bytes"]) and
                    isinstance(entry["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]),
                    "malformed/duplicate seal entry")
            require(path.is_file() and not path.is_symlink() and path.stat().st_size == entry["bytes"] and
                    sha256(path) == entry["sha256"], "sealed evidence missing/changed: " + relative)
            sealed[relative] = entry
            result["raw_sources"].append({"path": path.relative_to(root).as_posix(),
                                           "sha256": entry["sha256"], "bytes": entry["bytes"]})
        actual = {path.relative_to(run).as_posix() for path in run.rglob("*") if path.is_file()
                  and "tmp" not in path.relative_to(run).parts and path.name != "seal.json"}
        require(actual == set(sealed), "unsealed/missing run payload")

        def checked(relative):
            require(relative in sealed, "required evidence not sealed: " + relative)
            return contained(run, relative)

        def read(relative):
            return decode(checked(relative).read_text(encoding="utf-8"))

        require(read("outcome.json")["status"] == "COLLECTED", "recorded functional attempt failed")
        manifest = read("manifest.json")
        require(manifest["run_id"] == run.name and manifest["array_sizes"] == list(ARRAY_SIZES) and
                manifest["phase1_commit"] == PHASE1_COMMIT, "run/configuration/baseline mismatch")
        source_paths = set()
        for source in read("source_manifest.json")["files"]:
            require(source["path"] not in source_paths, "duplicate source path")
            source_paths.add(source["path"])
            snapshot = checked(source["snapshot"])
            require(snapshot.stat().st_size == source["bytes"] and sha256(snapshot) == source["sha256"],
                    "snapshot identity mismatch: " + source["path"])
            require(sha256(contained(root, source["path"])) == source["sha256"],
                    "source changed since functional run: " + source["path"])
        require(set(SOURCES) <= source_paths, "required functional source snapshot missing")
        require(manifest["contract_sha256"] == sha256(root / "docs/PHASE2_FUNCTIONAL_CONTRACT.md"),
                "functional contract changed")
        oracle_manifest = read("oracle_manifest.json")
        require(oracle_manifest["phase1_commit"] == PHASE1_COMMIT, "wrong Phase 1 oracle milestone")
        oracle_paths = set()
        for entry in oracle_manifest["files"]:
            require(entry["original_path"] not in oracle_paths, "duplicate oracle path")
            oracle_paths.add(entry["original_path"])
            require(entry["original_path"] in ORACLES.values(), "unexpected oracle source")
            filename = next(key for key, value in ORACLES.items() if value == entry["original_path"])
            require(entry["snapshot"] == "phase1_oracles/" + filename, "oracle snapshot path mismatch")
            path = checked(entry["snapshot"])
            require(path.stat().st_size == entry["bytes"] and sha256(path) == entry["sha256"] and
                    sha256(contained(root, entry["original_path"])) == entry["sha256"], "oracle bytes changed")
            original = subprocess.run(["git", "-C", str(root), "cat-file", "blob",
                                       PHASE1_COMMIT + ":" + entry["original_path"]], capture_output=True)
            require(original.returncode == 0 and hashlib.sha256(original.stdout).hexdigest() == entry["sha256"],
                    "oracle does not match immutable Phase 1 Git blob")
        require(oracle_paths == set(ORACLES.values()), "missing Phase 1 input/result oracle")
        invocation = read("invocation.json")
        expected = expected_commands(invocation["cwd"], run.relative_to(root).as_posix(), 2,
                                     invocation["verilator_executable"], invocation["argv"][0])

        def command(relative, name, arguments):
            record = read(relative + name + ".command.json")
            require(type(record["returncode"]) is int and record["returncode"] == 0, "failed command: " + relative + name)
            require(isinstance(record["argv"], list) and all(isinstance(x, str) and x for x in record["argv"])
                    and record["argv"] == arguments and record["cwd"] == invocation["cwd"],
                    "command identity mismatch: " + relative + name)
            for stream in ("stdout", "stderr"):
                path = contained(root, record[stream])
                require(path == run / (relative + name + "." + stream + ".log"), "command log path mismatch")
                require(sha256(checked(path.relative_to(run).as_posix())) == record[stream + "_sha256"],
                        "command log changed")

        for name in ("git_head", "git_status", "git_diff", "verilator_version", "verilator_configuration",
                     "compiler_version", "python_version"):
            command("", name, expected[name])
        version = checked("verilator_version.stdout.log").read_text().strip()
        require(re.match(r"Verilator \d+\.\d+", version), "missing observed simulator version")
        result["simulator"] = {"version": version, "executable": invocation["verilator_executable"]}
        vectors = read("phase1_oracles/vectors.json")["cases"]
        vector_map = keyed(vectors, "vectors")
        old_reference = keyed(read("phase1_oracles/reference.json")["cases"], "Phase 1 reference")
        old_rtl = keyed([decode(line) for line in checked("phase1_oracles/rtl_results.jsonl").read_text().splitlines()
                         if line.strip()], "Phase 1 RTL")
        require(set(vector_map) == set(old_reference) == set(old_rtl), "Phase 1 case membership mismatch")
        require(manifest["case_count_per_array"] == len(vectors) == 147 and
                manifest["case_ids"] == [case["case_id"] for case in vectors], "functional case plan differs")
        categories = {key: [case for case in vectors if case["category"] == key]
                      for key in ("directed", "randomized", "frozen_workload_sanity")}
        require({x["case_id"] for x in categories["directed"]} == DIRECTED_IDS and
                {x["case_id"] for x in categories["randomized"]} == {f"R{i:03d}" for i in range(128)} and
                [x["case_id"] for x in categories["frozen_workload_sanity"]] == [f"W{i}" for i in range(1, 7)],
                "required functional coverage missing")
        golden = {case["case_id"]: gemm(case["A"], case["B"]) for case in vectors}
        require(all(golden[key] == old_reference[key]["golden"] for key in golden),
                "numerical reference regeneration differs from Phase 1")
        for size in ARRAY_SIZES:
            prefix = f"S{size}/"
            reference_data = read(prefix + "reference.json")
            require(type(reference_data["array_size"]) is int and reference_data["array_size"] == size,
                    "reference configuration mismatch")
            references = keyed(reference_data["cases"], "references")
            rtl = keyed([decode(line) for line in checked(prefix + "rtl_results.jsonl").read_text().splitlines()
                         if line.strip()], "RTL")
            require(set(vector_map) == set(references) == set(rtl), "missing/extra functional case evidence")
            require(checked(prefix + "phase2_sim_top.sv").read_bytes() == render_wrapper(size, False).encode(),
                    "generated wrapper identity mismatch")
            checked(prefix + "simulator/phase2_sim")
            commands = expected_commands(invocation["cwd"], run.relative_to(root).as_posix(), size,
                                         invocation["verilator_executable"], invocation["argv"][0])
            for name in ("compile", "execute"):
                command(prefix, name, commands[name])
            directed = read(prefix + "array_tests.json")
            require(type(directed["array_size"]) is int and directed["array_size"] == size,
                    "directed test configuration mismatch")
            tests = directed["tests"]
            require(ARRAY_TEST_NAMES and isinstance(tests, list) and len(tests) == len(ARRAY_TEST_NAMES) and
                    {x["name"] for x in tests} == ARRAY_TEST_NAMES and
                    all(x["passed"] is True and integer(x["checks"], 1) for x in tests), "directed array checks failed/missing")
            records = []
            for vector in vectors:
                name = vector["case_id"]
                regenerated = simulate(vector["A"], vector["B"], size)
                require(canonical_bytes(regenerated) == canonical_bytes(references[name]["model"]) and
                        references[name]["golden"] == golden[name], "reference regeneration mismatch: " + name)
                record = compare_case(vector, references[name], rtl[name], size, old_reference[name], old_rtl[name])
                record["raw_sources"] = [(run / relative).relative_to(root).as_posix() for relative in
                                         ("phase1_oracles/vectors.json", prefix + "reference.json", prefix + "rtl_results.jsonl")]
                records.append(record)
                if not record["pass"]:
                    result["errors"].append(f"S{size}/{name}: numerical/cycle/Phase 1 disagreement")
            result["configurations"].append({"array_size": size, "cases": records, "directed_array_tests": tests,
                                             "summary": {"case_count": len(records),
                                                         "category_counts": {key: len(value) for key, value in categories.items()},
                                                         "numerical_passed": sum(x["numerical_match"] for x in records),
                                                         "cycle_passed": sum(x["cycle_match"] for x in records),
                                                         "passed": sum(x["pass"] for x in records),
                                                         "phase1_compatibility_passed": sum(x["phase1_compatibility"] is True for x in records) if size == 2 else None}})
        result["pass"] = not result["errors"]
        result["status"] = "PASS" if result["pass"] else "FAIL"
    except (ValueError, KeyError, TypeError, OSError, IndexError, AssertionError) as error:
        result["errors"].append(str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    selection = root / "results/raw/phase2/functional_selection.json"
    run_id = args.run_id or decode(selection.read_text())["run_id"]
    result = collect(root, contained(root / "results/raw/phase2/functional", run_id))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_bytes(result))
    print(canonical_bytes({"status": result["status"], "errors": result["errors"],
                           "configurations": [{"array_size": x["array_size"], "summary": x["summary"]}
                                              for x in result["configurations"]]}).decode(), end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
