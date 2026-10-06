"""Regression tests for adaptive reuse of Monte-Carlo holdout samples."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mismatch_sizing_sweep
import seed_policy


def test_successive_workflow_runs_reserve_disjoint_unseen_samples():
    previous = set()
    # Run 242 has now completed and is retained as examined evidence.
    for run in (243, 244, 245):
        start = seed_policy.workflow_validation_seed(run)
        seeds = set(range(start, start + 100))
        assert not seeds & previous
        assert not seed_policy.validation_conflicts(
            start, 100, seed_policy.PREVIOUSLY_EXAMINED_SEED_RANGES
        )
        assert seed_policy.workflow_validation_seed(run) == start
        previous.update(seeds)


@pytest.mark.parametrize("start,conflict", [
    (8901, False), (8902, True), (9001, True), (9100, True), (9101, False),
])
def test_seen_holdout_overlap_includes_both_endpoints(start, conflict):
    assert bool(seed_policy.validation_conflicts(
        start, 100, seed_policy.PREVIOUSLY_EXAMINED_SEED_RANGES
    )) is conflict


@pytest.mark.parametrize("run,samples", [
    (0, 100), (True, 100), (1, 1001), (1, 0), (3_000_000, 100),
])
def test_invalid_or_overflowing_workflow_seed_blocks_are_rejected(run, samples):
    with pytest.raises(ValueError):
        seed_policy.workflow_validation_seed(run, samples)


@pytest.mark.parametrize("seed_args", [
    [], ["--validation-seed-start", "9001"],
    ["--validation-seed-start", "1242001"],
    ["--validation-seed-start", "2000001"],
    ["--validation-seed-start", "2000100"],
])
def test_sweep_rejects_missing_or_seen_holdout_before_simulation(
    monkeypatch, capsys, seed_args
):
    monkeypatch.setattr(sys, "argv", [
        "mismatch_sizing_sweep.py", "--validation-samples", "100", *seed_args,
    ])

    def unexpected_simulator_lookup(*args):
        pytest.fail("invalid holdout must be rejected before starting ngspice")

    monkeypatch.setattr(mismatch_sizing_sweep.shutil, "which", unexpected_simulator_lookup)
    assert mismatch_sizing_sweep.main() == 2
    assert "MISMATCH SIZING SWEEP: FAIL:" in capsys.readouterr().out


@pytest.mark.parametrize("start,conflict", [
    (1999901, False), (1999902, True), (2000001, True),
    (2000100, True), (2000101, False),
])
def test_frozen_candidate_holdout_is_unavailable_to_new_studies(start, conflict):
    assert bool(seed_policy.validation_conflicts(
        start, 100, seed_policy.new_validation_exclusions()
    )) is conflict
