"""Deterministic functional verification inputs, separate from research results."""

import hashlib
import json
from pathlib import Path
import random

from model.arithmetic import validate_matrices

MASTER_SEED = 20260927
RANDOM_CASE_COUNT = 128


def _seed(case_id: str) -> int:
    """Stable per-case seed, independent of generation order or global RNG."""
    digest = hashlib.sha256(f"model2gds-phase1:{MASTER_SEED}:{case_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _case(case_id, category, A, B, generation, seed=None):
    M, N, K = validate_matrices(A, B)
    return {"case_id": case_id, "category": category, "M": M, "N": N, "K": K,
            "array_size": 2, "seed": seed, "generation": generation, "A": A, "B": B}


def _random_matrices(rng, M, N, K):
    return ([[rng.randint(-128, 127) for _ in range(K)] for _ in range(M)],
            [[rng.randint(-128, 127) for _ in range(N)] for _ in range(K)])


def build_cases(freeze_path: str | Path) -> list[dict]:
    """Build directed, 128 random, and six frozen-workload sanity inputs.

    No expected output or cycle metric is embedded in these records. Frozen
    dimensions are read from the unchanged project file, never selected based
    on observed results. Each generated case carries its own seed and method.
    """
    directed = [
        ("D_ZERO", [[0, 0, 0], [0, 0, 0]], [[0, 0], [0, 0], [0, 0]], "all-zero 2x2 outputs, K=3"),
        ("D_POSITIVE", [[1, 2], [3, 4]], [[5, 6], [7, 8]], "positive operands, complete 2x2"),
        ("D_NEGATIVE", [[-1, -2], [-3, -4]], [[-5, -6], [-7, -8]], "negative operands on both inputs"),
        ("D_MIXED", [[-3, 2, -1], [4, -5, 6]], [[7, -8], [-9, 10], [11, -12]], "mixed signs and cancellation"),
        ("D_MIN", [[-128, -128], [-128, -128]], [[-128, -128], [-128, -128]], "INT8 minimum on both inputs"),
        ("D_MAX", [[127, 127], [127, 127]], [[127, 127], [127, 127]], "INT8 maximum on both inputs"),
        ("D_EXTREMA", [[-128, 127], [127, -128]], [[127, -128], [-128, 127]], "mixed signed INT8 extrema"),
        ("D_K1", [[-128], [127]], [[-1, 1]], "K=1 on all four active PEs"),
        ("D_UNDERFILLED_1X1", [[-2, 3, -4]], [[5], [-6], [7]], "one active PE, K=3"),
        ("D_UNDERFILLED_1X2", [[1, -2, 3, -4]], [[-5, 6], [7, -8], [-9, 10], [11, -12]], "one active row, K=4"),
        ("D_UNDERFILLED_2X1", [[1, 2, 3, 4], [-1, -2, -3, -4]], [[-5], [6], [-7], [8]], "one active column, K=4"),
        ("D_RAGGED", [[1, -2, 3], [-4, 5, -6], [7, -8, 9]],
         [[1, -2, 3, -4, 5], [-6, 7, -8, 9, -10], [11, -12, 13, -14, 15]],
         "3x5 output: complete and ragged tiles, K=3"),
        ("D_WRAP_POSITIVE", [[-128] * 131073], [[-128] for _ in range(131073)],
         "1x1 output, 131073 products of (-128)*(-128), crosses signed INT32 maximum"),
    ]
    cases = [_case(case_id, "directed", A, B, generation)
             for case_id, A, B, generation in directed]
    for index in range(RANDOM_CASE_COUNT):
        case_id = f"R{index:03d}"
        seed = _seed(case_id)
        rng = random.Random(seed)
        M, N, K = rng.randint(1, 6), rng.randint(1, 6), rng.randint(1, 16)
        A, B = _random_matrices(rng, M, N, K)
        cases.append(_case(case_id, "randomized", A, B,
                           "Python random.Random(case seed); M,N uniform 1..6; K uniform 1..16; "
                           "row-major A then B, signed values uniform -128..127", seed))
    freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8-sig"))
    if freeze.get("kernel") != "GEMM" or freeze.get("dataflow") != "output_stationary":
        raise ValueError("Unexpected frozen kernel or dataflow")
    workloads = freeze.get("workloads")
    if not isinstance(workloads, list) or len(workloads) != 6:
        raise ValueError("Expected exactly the six frozen GEMM workloads")
    for index, dimensions in enumerate(workloads, 1):
        if (not isinstance(dimensions, list) or len(dimensions) != 3
                or any(type(d) is not int or d <= 0 for d in dimensions)):
            raise ValueError("Malformed frozen GEMM workload")
        M, N, K = dimensions
        case_id = f"W{index}"
        seed = _seed(case_id)
        A, B = _random_matrices(random.Random(seed), M, N, K)
        cases.append(_case(case_id, "frozen_workload_sanity", A, B,
                           "Dimensions from PROJECT_FREEZE.json; Python random.Random(case seed); "
                           "row-major A then B, signed values uniform -128..127", seed))
    return cases
