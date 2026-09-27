"""Keep adaptive sizing studies separate from previously examined samples."""
from __future__ import annotations


# These results were examined before the September 27 sizing refinement.
# A disjoint *current* screen alone does not make these holdouts unseen again.
PREVIOUSLY_EXAMINED_SEED_RANGES = (
    {"start": 1001, "stop": 1100, "source_run_id": 36256551286},
    {"start": 3001, "stop": 3012, "source_run_id": 36298147889},
    {"start": 7001, "stop": 7100, "source_run_id": 36259524511},
    {"start": 9001, "stop": 9100, "source_run_id": 36298147889},
)
MAX_SEED = 2**31 - 1


def seed_range(start: int, count: int) -> tuple[int, int]:
    """Validate an inclusive positive 31-bit ngspice seed range."""
    if (
        type(start) is not int or type(count) is not int
        or start < 1 or count < 1 or start + count - 1 > MAX_SEED
    ):
        raise ValueError("seeds must form a positive 31-bit integer range")
    return start, start + count - 1


def validation_conflicts(
    start: int, count: int, excluded_ranges: list[dict] | tuple[dict, ...]
) -> list[dict]:
    """Return every examined range touched by the proposed validation set."""
    first, last = seed_range(start, count)
    conflicts = []
    for excluded in excluded_ranges:
        lo, hi = excluded["start"], excluded["stop"]
        if type(lo) is not int or type(hi) is not int:
            raise ValueError("examined seed-range endpoints must be integers")
        seed_range(lo, hi - lo + 1)
        if first <= hi and lo <= last:
            conflicts.append(excluded)
    return conflicts


def workflow_validation_seed(run_number: int, samples: int = 100) -> int:
    """Reserve 1000 seeds per workflow run; retries reproduce the same data."""
    if type(run_number) is not int or run_number < 1:
        raise ValueError("workflow run number must be a positive integer")
    if type(samples) is not int or not 1 <= samples <= 1000:
        raise ValueError("workflow validation supports at most 1000 samples")
    start = 1_000_001 + run_number * 1000
    seed_range(start, samples)
    return start
