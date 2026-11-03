"""Parameterized functional contract and conservative evidence rejection tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from model.golden import gemm
from model.systolic_generic import closed_form_cycles, simulate, tiles
from scripts.collect_phase2_functional import collect, compare_case, expected_commands

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "results/raw/phase1/REG_001"


@pytest.fixture(scope="module")
def phase1_oracles():
    vectors = json.loads((ORACLE / "vectors.json").read_text())["cases"]
    references = {x["case_id"]: x for x in json.loads((ORACLE / "reference.json").read_text())["cases"]}
    rtl = {row["case_id"]: row for row in map(json.loads, (ORACLE / "rtl_results.jsonl").read_text().splitlines())}
    return vectors, references, rtl


@pytest.mark.parametrize("size", [2, 4, 8])
def test_all_147_immutable_cases_match_golden_and_secondary_cycle_identity(size, phase1_oracles):
    vectors, references, old_rtl = phase1_oracles
    assert len(vectors) == 147
    for case in vectors:
        result = simulate(case["A"], case["B"], size)
        assert result["C"] == gemm(case["A"], case["B"]) == references[case["case_id"]]["golden"], case["case_id"]
        assert result["cycles"] == closed_form_cycles(case["M"], case["N"], case["K"], size), case["case_id"]
        if size == 2:
            assert result == references[case["case_id"]]["model"], case["case_id"]
            for key in ("M", "N", "K", "array_size", "C", "cycles", "tiles"):
                assert result[key] == old_rtl[case["case_id"]][key], (case["case_id"], key)


@pytest.mark.parametrize("size", [0, 1, 3, 16, -2, True, 4.0, "4"])
def test_other_array_sizes_are_rejected(size):
    for function, arguments in ((tiles, (1, 1, size)), (simulate, ([[1]], [[1]], size)),
                                (closed_form_cycles, (1, 1, 1, size))):
        with pytest.raises(ValueError):
            function(*arguments)


@pytest.mark.parametrize("size", [2, 4, 8])
def test_full_wavefront_propagates_one_pe_per_edge_and_done_same_final_edge(size):
    result = simulate([[i+1] for i in range(size)], [[j+1 for j in range(size)]], size, trace=True)
    assert result["cycles"] == 2 * size
    edges = result["trace"]
    assert edges[0]["phase"] == "clear"
    for edge in edges[1:]:
        for pe in edge["pe"]:
            consumed = edge["data_edge"] >= pe["row"] + pe["col"]
            assert pe["result_valid"] is consumed
            assert pe["acc"] == ((pe["row"]+1)*(pe["col"]+1) if consumed else 0)
    assert [edge["tile_done"] for edge in edges] == [False] * (2*size-1) + [True]


@pytest.mark.parametrize("size", [2, 4, 8])
def test_underfilled_mask_and_ragged_clear_boundaries(size):
    one = simulate([[2]], [[-3]], size, trace=True)
    assert one["cycles"] == 2 and one["C"] == [[-6]]
    assert one["trace"][-1]["active_mask"] == 1
    assert sum(p["result_valid"] for p in one["trace"][-1]["pe"]) == 1
    M, N = size+1, size+3
    schedule = tiles(M, N, size)
    coordinates = [(t["row"]+i, t["col"]+j) for t in schedule
                   for i in range(t["rows"]) for j in range(t["cols"])]
    assert len(coordinates) == len(set(coordinates)) == M*N
    A = [[i-3, 2, -1] for i in range(M)]
    B = [[j-4 for j in range(N)], [2]*N, [-3]*N]
    result = simulate(A, B, size, trace=True)
    assert result["C"] == gemm(A, B)
    assert [edge["cycle"] for edge in result["trace"]] == list(range(1, result["cycles"]+1))
    clear_edges = [edge for edge in result["trace"] if edge["phase"] == "clear"]
    assert len(clear_edges) == len(schedule)
    assert all(p["acc"] == 0 and not p["result_valid"] for e in clear_edges for p in e["pe"])


def test_generic_completion_has_no_golden_or_closed_form_dependency(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("completion must use independent PE state")
    monkeypatch.setattr("model.golden.gemm", forbidden)
    monkeypatch.setattr("model.systolic_generic.closed_form_cycles", forbidden)
    assert simulate([[2, -3]], [[4], [5]], 8)["C"] == [[-7]]


def _case(size=2):
    vector = {"case_id": "D_SAMPLE", "category": "directed", "seed": None, "generation": "test fixture",
              "M": 1, "N": 1, "K": 1, "array_size": 2, "A": [[2]], "B": [[3]]}
    model = {"M": 1, "N": 1, "K": 1, "array_size": size, "C": [[6]], "cycles": 2,
             "tiles": [{"row": 0, "col": 0, "rows": 1, "cols": 1, "cycles": 2}]}
    reference = {"case_id": "D_SAMPLE", "golden": [[6]], "model": deepcopy(model)}
    rtl = {"case_id": "D_SAMPLE", **deepcopy(model)}
    old_rtl = {**deepcopy(rtl), "array_size": 2}
    old_reference = {**deepcopy(reference), "model": {**deepcopy(model), "array_size": 2}}
    return vector, reference, rtl, size, old_reference, old_rtl


@pytest.mark.parametrize("size", [2, 4, 8])
def test_comparison_accepts_complete_matching_raw_case(size):
    record = compare_case(*_case(size))
    assert record["pass"]
    assert record["phase1_compatibility"] is (True if size == 2 else None)


@pytest.mark.parametrize("mutation", ["wrong_output", "wrong_cycles", "wrong_phase1_output"])
def test_numerical_cycle_and_phase1_disagreements_fail(mutation):
    arguments = _case()
    if mutation == "wrong_output":
        arguments[2]["C"] = [[7]]
    elif mutation == "wrong_cycles":
        arguments[2]["cycles"] = 3
        arguments[2]["tiles"][0]["cycles"] = 3
    else:
        arguments[5]["C"] = [[-6]]
    assert not compare_case(*arguments)["pass"]


@pytest.mark.parametrize("mutation", ["missing_tile", "wrong_array", "bool_cycles", "bad_geometry", "bad_input", "bad_shape"])
def test_malformed_case_evidence_is_rejected(mutation):
    arguments = _case()
    if mutation == "missing_tile":
        arguments[2]["tiles"] = []
    elif mutation == "wrong_array":
        arguments[2]["array_size"] = 16
    elif mutation == "bool_cycles":
        arguments[2]["cycles"] = True
    elif mutation == "bad_geometry":
        arguments[2]["tiles"][0]["col"] = 1
    elif mutation == "bad_input":
        arguments[0]["A"] = [[128]]
    else:
        arguments[2]["C"] = [[]]
    with pytest.raises(ValueError):
        compare_case(*arguments)


@pytest.mark.parametrize("mode", ["missing_seal", "changed_file", "unsealed_file", "failed_attempt", "duplicate_seal"])
def test_collector_rejects_missing_failed_or_tampered_run_before_comparison(tmp_path, mode):
    run = tmp_path / "results/raw/phase2/functional/REG_TEST"
    run.mkdir(parents=True)
    outcome = run / "outcome.json"
    payload = json.dumps({"status": "FAIL" if mode == "failed_attempt" else "COLLECTED"}).encode()
    outcome.write_bytes(payload)
    entry = {"path": "outcome.json", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    if mode != "missing_seal":
        (run / "seal.json").write_text(json.dumps({"files": [entry, entry] if mode == "duplicate_seal" else [entry]}))
    if mode == "changed_file":
        outcome.write_text('{"status":"COLLECTED","tampered":true}')
    elif mode == "unsealed_file":
        (run / "unexpected.json").write_text("{}")
    result = collect(tmp_path, run)
    assert result["status"] == "FAIL" and result["pass"] is False and result["errors"]


def test_command_identity_binds_size_sources_vectors_and_outputs():
    expected = expected_commands("/recorded/project", "results/raw/phase2/functional/REG_X", 8,
                                 "/usr/bin/verilator", "/usr/bin/python3")
    assert "-std=c++17 -DARRAY_SIZE=8" in expected["compile"]
    assert expected["compile"][-2].endswith("/S8/phase2_sim_top.sv")
    assert expected["execute"][0].endswith("/S8/simulator/phase2_sim")
    assert expected["execute"][1].endswith("/phase1_oracles/vectors.txt")
    assert expected["execute"][2].endswith("/S8/rtl_results.jsonl")
