"""Zero-model checks of scoring, shared accounting and durable physical quotas."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from capacity_budget import finish, reserve
from capacity_meter import InvalidMeasurement, TokenLedger
from capacity_protocol import CONSTRAINT_GATES, GDS_GATES, protocol, score, summarize
from study_protocol import write_json


def rejects(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("Invalid operation was accepted")


def usage(i, o, cache=0, reasoning=0):
    return dict(input_tokens=i, output_tokens=o, total_tokens=i+o,
                cached_input_tokens=cache, reasoning_output_tokens=reasoning)


def check():
    plan = protocol()
    assert len(plan["formal_jobs"]) == 84 and len(plan["pilot_jobs"]) == 8
    assert len({r["id"] for r in plan["formal_jobs"]}) == 84
    assert sum(plan["physical_limits"].values()) == 194
    assert plan == protocol()
    fg = dict(function=True, integration=True)
    gg = dict.fromkeys(GDS_GATES, True)
    hg = dict.fromkeys(CONSTRAINT_GATES, True)
    ref = dict(cell_area=100, die_area=250, workloads={
        w: dict(throughput=10, latency=12, power=5, energy=2) for w in ("one", "two")})
    baseline = score(fg, gg, hg, ref, ref)
    assert baseline["final_score"] == 50 and baseline["joint_pass"]
    for key in fg:
        row = score(dict(fg, **{key: False}), gg, hg, ref, ref)
        assert row["gds_pass"] and row["final_score"] == 0
    for key in gg:
        row = score(fg, dict(gg, **{key: False}), hg, ref, ref)
        assert row["functional_pass"] and row["final_score"] == 0
    for key in hg:
        assert score(fg, gg, dict(hg, **{key: False}), ref, ref)["final_score"] == 0
    for key, value in (("throughput", 7), ("latency", 16), ("power", 7), ("energy", 3)):
        bad = copy.deepcopy(ref)
        bad["workloads"]["two"][key] = value
        assert score(fg, gg, hg, bad, ref)["final_score"] == 0
    for key in ("cell_area", "die_area"):
        bad = copy.deepcopy(ref)
        bad[key] *= 1.3
        assert score(fg, gg, hg, bad, ref)["final_score"] == 0
        bad[key] = float("nan")
        assert score(fg, gg, hg, bad, ref)["final_score"] == 0
    assert score(fg, gg, hg, None, ref)["final_score"] == 0
    assert summarize([{}])["conditional_gds_rate"] is None
    assert summarize([dict(baseline, terminal=True), dict(terminal=True)])["average_score"] == 25
    meter = TokenLedger(limit=100)
    meter.record("rtl", "1", usage(30, 10, 20, 5))
    meter.record("rtl", "1", usage(30, 10, 20, 5))
    meter.record("rtl", "2", usage(30, 10, 20, 5))
    assert meter.summary()["actual_tokens"] == 40
    meter = TokenLedger(json.loads(json.dumps(meter.state)))
    meter.record("rtl", "3", usage(40, 20, 25, 8))
    meter.record("review", "1", usage(20, 10, 10, 5))
    assert meter.summary()["actual_tokens"] == 90
    witness = dict.fromkeys(("source_immutable", "tool_completed", "usage_after_capture",
                             "no_unaccounted_mutation", "source_session_matches"), True)
    meter.snapshot(snapshot_id="s1", source_sha256={"rtl/a.sv": "test"},
                   session="review", event_key="1", witness=witness)
    assert meter.at(89) is None and meter.at(100)["id"] == "s1"
    meter.record("rtl", "4", usage(60, 30, 25, 8))
    meter.snapshot(snapshot_id="over", source_sha256={"rtl/a.sv": "changed"},
                   session="rtl", event_key="4", witness=witness)
    assert meter.at(100)["id"] == "s1" and meter.summary()["overshoot_tokens"] == 20
    assert not meter.summary()["dispatch_allowed"]
    bad = TokenLedger()
    rejects(lambda: bad.record("s", "1", {}))
    assert not bad.summary()["measurement_valid"]
    bad = TokenLedger()
    bad.record("s", "1", usage(10, 5))
    rejects(lambda: bad.record("s", "2", usage(1, 1)))
    bad = TokenLedger()
    bad.record("s", "1", usage(10, 5))
    rejects(lambda: bad.record("s", "1", usage(20, 5)))
    bad = TokenLedger()
    bad.record("s", "1", usage(10, 5))
    rejects(lambda: bad.snapshot(snapshot_id="x", source_sha256={"x": "hash"},
                                session="s", event_key="1", witness={}))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_json(root / "protocol.json", plan)
        trial = plan["pilot_jobs"][0]["id"]
        rejects(lambda: reserve(root, "pilot", trial, "premature"))
        write_json(root / "protocol.json", dict(plan, pilot_launch_allowed=True))
        reserve(root, "pilot", trial, "first")
        finish(root, "first", "failed", "retained failure")
        reserve(root, "pilot", trial, "second")
        rejects(lambda: reserve(root, "pilot", trial, "third"))
        rejects(lambda: finish(root, "first", "passed", "overwritten"))
        rejects(lambda: reserve(root, "formal", plan["formal_jobs"][0]["id"], "formal"))
        rejects(lambda: reserve(root, "pilot", "unregistered", "extra"))
        assert len(json.loads((root / "physical-ledger.json").read_text())["attempts"]) == 2
    return dict(passed=True, model_calls=0, physical_runs=0,
                scope=["protocol counts", "independent F/G gates", "constraints and score",
                       "shared cumulative deltas", "duplicate/resume/reset/missing usage",
                       "overshoot and latest-snapshot selection", "immutable terminal attempts",
                       "third physical attempt rejection", "formal prerequisite rejection"],
                not_qualified=["live CLI source association", "sandbox/tool isolation",
                               "task references", "workflow execution"])


if __name__ == "__main__":
    result = check()
    write_json(Path(__file__).resolve().parents[1] / "checks/zero-model-core.json", result)
    print(json.dumps(result))
