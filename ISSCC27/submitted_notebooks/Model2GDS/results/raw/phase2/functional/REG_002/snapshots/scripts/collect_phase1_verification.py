#!/usr/bin/env python3
"""Derive Phase 1 verification status from preserved, hash-checked raw evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase1_common import canonical_bytes, sha256

DIRECTED_IDS = {'D_ZERO', 'D_POSITIVE', 'D_NEGATIVE', 'D_MIXED', 'D_MIN', 'D_MAX', 'D_EXTREMA',
                'D_K1', 'D_UNDERFILLED_1X1', 'D_UNDERFILLED_1X2', 'D_UNDERFILLED_2X1',
                'D_RAGGED', 'D_WRAP_POSITIVE'}
PE_TESTS = {'pe_signed_extrema', 'pe_synchronous_reset_priority', 'pe_clear_priority',
            'pe_bubbles_and_one_sided_valid', 'pe_registered_propagation', 'pe_one_sided_last',
            'pe_sticky_result_valid', 'pe_positive_overflow_wrap', 'pe_negative_overflow_wrap',
            'array_registered_wavefront_with_bubble', 'array_reset_flushes_pipeline_and_mask',
            'array_masked_completion_and_clear'}


def expected_commands(cwd, run_relative, verilator, python):
    """Exact recorded command identity, independent of the replay host's mount."""
    base = cwd.replace('\\', '/').rstrip('/')
    run = base + '/' + run_relative
    return {
        'compile': [verilator, '--cc', '--exe', '--build', '-j', '2', '-Wall', '-Wno-PINCONNECTEMPTY',
                    '--top-module', 'phase1_sim_top', '--Mdir', run + '/tmp/obj_dir',
                    '-CFLAGS', '-std=c++17', base + '/rtl/gemm_pe.sv',
                    base + '/rtl/systolic_array_2x2.sv', base + '/verification/phase1_sim_top.sv',
                    base + '/verification/phase1_sim_main.cpp'],
        'execute': [run + '/simulator/phase1_sim', run + '/vectors.txt',
                    run + '/rtl_results.jsonl', run + '/pe_results.json'],
        'verilator_version': [verilator, '--version'], 'verilator_configuration': [verilator, '-V'],
        'compiler_version': ['g++', '--version'], 'python_version': [python, '--version'],
        'git_head': ['git', 'rev-parse', 'HEAD'],
        'git_status': ['git', 'status', '--porcelain=v1'],
        'git_diff': ['git', 'diff', '--no-ext-diff', '--binary'],
    }


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def decode(text):
    return json.loads(text, object_pairs_hook=_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON: " + x)))


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def contained(base, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("invalid evidence path")
    path = (base / relative).resolve()
    if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.is_relative_to(base.resolve()):
        raise ValueError("evidence path escapes its root")
    return path


def matrix(value, rows, cols):
    return (isinstance(value, list) and len(value) == rows and
            all(isinstance(row, list) and len(row) == cols and
                all(type(x) is int and -(2**31) <= x < 2**31 for x in row) for row in value))


def compare_case(vector, reference, rtl):
    """Compare full matrices and observed cycles, never trust a success string."""
    case_id = vector["case_id"]
    dims = [vector[k] for k in ("M", "N", "K")]
    if not all(integer(x, 1) for x in dims):
        raise ValueError(case_id + ": invalid dimensions")
    m, n, k = dims
    if vector["array_size"] != 2 or type(vector["array_size"]) is not int:
        raise ValueError(case_id + ": unauthorized array size")
    model = reference["model"]
    if reference["case_id"] != case_id or rtl["case_id"] != case_id:
        raise ValueError("case identity mismatch")
    for record in (model, rtl):
        if any(type(record[x]) is not int for x in ("M", "N", "K", "array_size")):
            raise ValueError(case_id + ": noninteger dimensions")
        if [record[x] for x in ("M", "N", "K")] != dims or record["array_size"] != 2:
            raise ValueError(case_id + ": model/RTL configuration mismatch")
        if not integer(record["cycles"], 1):
            raise ValueError(case_id + ": invalid cycle count")
    for key, rows, cols in [("A", m, k), ("B", k, n)]:
        if not matrix(vector[key], rows, cols) or any(x < -128 or x > 127 for row in vector[key] for x in row):
            raise ValueError(case_id + ": invalid signed INT8 input")
    if not all(matrix(value, m, n) for value in (reference["golden"], model["C"], rtl["C"])):
        raise ValueError(case_id + ": malformed INT32 result matrix")
    tile_geometry = [{"row": row, "col": col, "rows": min(2, m-row), "cols": min(2, n-col)}
                     for row in range(0, m, 2) for col in range(0, n, 2)]
    for record in (model, rtl):
        if not isinstance(record["tiles"], list) or len(record["tiles"]) != len(tile_geometry):
            raise ValueError(case_id + ": missing/extra tiles")
        for tile, geometry in zip(record["tiles"], tile_geometry):
            if any(type(tile[x]) is not int or tile[x] != geometry[x] for x in geometry):
                raise ValueError(case_id + ": tile geometry mismatch")
            if not integer(tile["cycles"], 1):
                raise ValueError(case_id + ": invalid tile cycle count")
        if sum(tile["cycles"] for tile in record["tiles"]) != record["cycles"]:
            raise ValueError(case_id + ": tile/workload cycle sum mismatch")
    numerical = reference["golden"] == rtl["C"]
    model_numerical = reference["golden"] == model["C"]
    cycles = model["cycles"] == rtl["cycles"] and model["tiles"] == rtl["tiles"]
    return {"case_id": case_id, "category": vector["category"], "M": m, "N": n, "K": k,
            "array_size": 2, "seed": vector["seed"], "generation": vector["generation"],
            "input_sha256": hashlib.sha256(canonical_bytes({"A": vector["A"], "B": vector["B"]})).hexdigest(),
            "golden_sha256": hashlib.sha256(canonical_bytes(reference["golden"])).hexdigest(),
            "rtl_result_sha256": hashlib.sha256(canonical_bytes(rtl["C"])).hexdigest(),
            "numerical_match": numerical, "model_numerical_match": model_numerical,
            "model_cycles": model["cycles"], "rtl_cycles": rtl["cycles"],
            "cycle_match": cycles, "cycle_unit": "rising_clock_edges_including_tile_clear",
            "tiles": model["tiles"], "pass": numerical and model_numerical and cycles}


def keyed(records, label):
    if not isinstance(records, list) or not records:
        raise ValueError(label + ": missing case records")
    result = {}
    for item in records:
        name = item["case_id"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_]+", name) or name in result:
            raise ValueError(label + ": invalid or duplicate case ID")
        result[name] = item
    return result


def collect(root, run):
    root, run = Path(root).resolve(), Path(run).resolve()
    result = {"schema_version": 1, "status": "FAIL", "pass": False,
              "run_id": run.name, "array_size": 2, "errors": [], "cases": [],
              "summary": {}, "raw_sources": [],
              "parser": {"path": "scripts/collect_phase1_verification.py", "sha256": sha256(__file__)}}
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    def read(relative):
        path = contained(run, relative)
        return decode(path.read_text(encoding="utf-8"))
    try:
        require(run.is_relative_to(root / "results/raw/phase1"), "selected run outside Phase 1")
        seal_data = read("seal.json")
        sealed = {}
        for entry in seal_data["files"]:
            path = contained(run, entry["path"])
            require(entry["path"] not in sealed, "duplicate seal entry")
            require(path.is_file() and path.stat().st_size == entry["bytes"] and
                    sha256(path) == entry["sha256"], "sealed evidence missing/changed: " + entry["path"])
            sealed[entry["path"]] = entry
            result["raw_sources"].append({"path": path.relative_to(root).as_posix(),
                                           "sha256": entry["sha256"], "bytes": entry["bytes"]})
        def must_seal(relative):
            require(relative in sealed, "required evidence not sealed: " + relative)
        required = ["manifest.json", "source_manifest.json", "vectors.json", "vectors.txt",
                    "reference.json", "rtl_results.jsonl", "pe_results.json", "outcome.json",
                    "invocation.json", "simulator/phase1_sim"]
        for relative in required:
            must_seal(relative)
        require(read("outcome.json")["status"] == "COLLECTED", "selected attempt failed")
        manifest = read("manifest.json")
        require(manifest["run_id"] == run.name and manifest["array_size"] == 2,
                "manifest configuration/run mismatch")
        require(manifest["master_seed"] == 20260927 and manifest["random_case_count"] == 128,
                "manifest does not match frozen verification plan")
        require(manifest["vectors_sha256"] == sha256(run / "vectors.json") and
                manifest["vectors_text_sha256"] == sha256(run / "vectors.txt"), "vector identity mismatch")
        source_paths = set()
        for source in read("source_manifest.json")["files"]:
            must_seal(source["snapshot"])
            snapshot = contained(run, source["snapshot"])
            require(source["path"] not in source_paths, "duplicate source snapshot")
            source_paths.add(source["path"])
            require(sha256(snapshot) == source["sha256"] and snapshot.stat().st_size == source["bytes"],
                    "source snapshot identity mismatch")
            # Reproduction must use the same arithmetic, model, generator, RTL and contract.
            if source["path"].startswith(("model/", "rtl/", "verification/", "tests/")) or source["path"] == "docs/PHASE1_MICROARCHITECTURE.md":
                require(sha256(contained(root, source["path"])) == source["sha256"],
                        "implementation changed since selected run: " + source["path"])
        for path in ["model/arithmetic.py", "model/golden.py", "model/systolic.py", "model/vectors.py", "rtl/gemm_pe.sv",
                     "rtl/systolic_array_2x2.sv", "verification/phase1_sim_top.sv",
                     "verification/phase1_sim_main.cpp", "scripts/run_phase1.py", "scripts/phase1_common.py",
                     "docs/PHASE1_MICROARCHITECTURE.md", "PROJECT_FREEZE.json"]:
            require(path in source_paths, "required source snapshot missing: " + path)
        require(manifest["contract_sha256"] == sha256(root / "docs/PHASE1_MICROARCHITECTURE.md"),
                "cycle contract differs from regression contract")
        invocation = read("invocation.json")
        expected = expected_commands(invocation["cwd"], run.relative_to(root).as_posix(),
                                     invocation["verilator_executable"], invocation["argv"][0])
        for name in ["compile", "execute", "verilator_version", "verilator_configuration",
                     "compiler_version", "python_version", "git_head", "git_status", "git_diff"]:
            must_seal(name + ".command.json")
            command = read(name + ".command.json")
            require(type(command["returncode"]) is int and command["returncode"] == 0,
                    name + ": failed command")
            require(isinstance(command["argv"], list) and command["argv"] and
                    all(isinstance(x, str) and x for x in command["argv"]), name + ": missing command argv")
            require(command["argv"] == expected[name] and command["cwd"] == invocation["cwd"],
                    name + ": command does not identify the selected sources/artifacts")
            for stream in ("stdout", "stderr"):
                logfile = contained(root, command[stream])
                require(logfile.is_relative_to(run), name + ": log outside run")
                must_seal(logfile.relative_to(run).as_posix())
                require(sha256(logfile) == command[stream + "_sha256"], name + ": log hash mismatch")
        version = (run / "verilator_version.stdout.log").read_text().strip()
        require(re.match(r"Verilator \d+\.\d+", version) is not None, "missing actual Verilator version")
        result["simulator"] = {"version": version, "executable": read("invocation.json")["verilator_executable"]}
        vectors = read("vectors.json")["cases"]
        vector_map = keyed(vectors, "vectors")
        reference_map = keyed(read("reference.json")["cases"], "reference")
        rtl_map = keyed([decode(line) for line in (run / "rtl_results.jsonl").read_text().splitlines() if line.strip()], "RTL")
        require(set(vector_map) == set(reference_map) == set(rtl_map), "missing/extra end-to-end case evidence")
        require(len(vectors) == manifest["case_count"], "case count differs from manifest")
        expected_tokens = [str(len(vectors))]
        for case in vectors:
            expected_tokens += ["CASE", case["case_id"], *(str(case[x]) for x in ("M", "N", "K"))]
            for key in ("A", "B"):
                expected_tokens.extend(str(x) for row in case[key] for x in row)
        require((run / "vectors.txt").read_text().split() == expected_tokens,
                "harness text vectors differ from JSON reference inputs")
        for vector in vectors:
            record = compare_case(vector, reference_map[vector["case_id"]], rtl_map[vector["case_id"]])
            record["raw_sources"] = [(run / name).relative_to(root).as_posix()
                                     for name in ("vectors.json", "reference.json", "rtl_results.jsonl")]
            result["cases"].append(record)
            if not record["pass"]:
                result["errors"].append("numerical/model/RTL disagreement: " + record["case_id"])
        categories = {category: [v for v in vectors if v["category"] == category]
                      for category in ("directed", "randomized", "frozen_workload_sanity")}
        require(sum(map(len, categories.values())) == len(vectors), "unknown case category")
        require({v["case_id"] for v in categories["randomized"]} == {f'R{i:03d}' for i in range(128)} and
                {v["case_id"] for v in categories["directed"]} == DIRECTED_IDS,
                "verification case coverage missing")
        require(all(1 <= v["M"] <= 6 and 1 <= v["N"] <= 6 and 1 <= v["K"] <= 16 and
                    integer(v["seed"]) for v in categories["randomized"]), "random suite dimensions/seed invalid")
        frozen = decode((root / "PROJECT_FREEZE.json").read_text())["workloads"]
        require([[v[x] for x in ("M", "N", "K")] for v in categories["frozen_workload_sanity"]] == frozen == manifest["workload_dimensions"],
                "six frozen workload sanity set changed/missing")
        pe = read("pe_results.json")["tests"]
        require(isinstance(pe, list) and {x["name"] for x in pe} == PE_TESTS, "directed PE/array tests missing")
        require(len({x["name"] for x in pe}) == len(pe), "duplicate directed test")
        require(all(x["passed"] is True and integer(x["checks"], 1) for x in pe), "directed RTL check failed/malformed")
        result["directed_rtl_tests"] = pe
        result["summary"] = {
            "end_to_end_cases": len(vectors),
            "category_counts": {key: len(value) for key, value in categories.items()},
            "numerical_passed": sum(x["numerical_match"] for x in result["cases"]),
            "cycle_passed": sum(x["cycle_match"] for x in result["cases"]),
            "model_numerical_passed": sum(x["model_numerical_match"] for x in result["cases"]),
            "end_to_end_passed": sum(x["pass"] for x in result["cases"]),
            "directed_rtl_tests": len(pe), "directed_rtl_checks": sum(x["checks"] for x in pe),
            "master_seed": manifest["master_seed"],
        }
        selection_path = root / "results/raw/phase1/selection.json"
        selection = decode(selection_path.read_text())
        require(selection["run_id"] == run.name, "selection differs from collected run")
        test_command = contained(root, selection["pytest_command"])
        require(test_command.is_relative_to(root / "results/raw/phase1/validation"), "test evidence outside validation")
        tests = decode(test_command.read_text())
        require(type(tests["returncode"]) is int and tests["returncode"] == 0, "pytest did not exit successfully")
        require(tests["argv"][1:] == ["-m", "pytest", "-q"], "pytest evidence is not the complete suite")
        test_log = contained(root, tests["log"])
        require(test_log.is_relative_to(root / "results/raw/phase1/validation") and
                sha256(test_log) == tests["log_sha256"], "pytest log identity mismatch")
        matches = re.findall(r"^(\d+) passed in [^\r\n]+$", test_log.read_text(), re.MULTILINE)
        require(len(matches) == 1, "missing/unambiguous full pytest result")
        result["pytest"] = {"passed": int(matches[0]), "result": re.search(r"^\d+ passed in [^\r\n]+$", test_log.read_text(), re.MULTILINE).group(),
                            "command": test_command.relative_to(root).as_posix(),
                            "command_sha256": sha256(test_command), "log": test_log.relative_to(root).as_posix(),
                            "log_sha256": sha256(test_log)}
        result["pass"] = not result["errors"]
        result["status"] = "PASS" if result["pass"] else "FAIL"
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        result["errors"].append(str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    run_id = args.run_id or decode((root / "results/raw/phase1/selection.json").read_text())["run_id"]
    result = collect(root, contained(root / "results/raw/phase1", run_id))
    payload = canonical_bytes(result)
    if args.output:
        # A structured derivative may be regenerated explicitly; raw evidence never is.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "errors": result["errors"]}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
