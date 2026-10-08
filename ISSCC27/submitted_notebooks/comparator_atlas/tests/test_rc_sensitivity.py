"""Check the bounded published sensitivity evidence without starting SPICE."""

import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from reproduction.pvt45 import run_rc_sensitivity as sensitivity


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "study" / "rc_sensitivity"


def test_card_scaling_only_changes_atlas_passives():
    original = (
        ".subckt outer a b\n"
        "C0 a b 1f\n"
        "R0 a b 2\n"
        ".ends\n"
        ".subckt atlas a b\n"
        + "".join(f"C{i} a b 1f\n" for i in range(319))
        + "".join(f"R{i} a b 2\n" for i in range(675))
        + ".ends\n"
    )
    unchanged = sensitivity.scale_native_cards(
        original, Decimal("1"), Decimal("1"))
    scaled = sensitivity.scale_native_cards(
        original, Decimal("1.2"), Decimal("0.8"))
    assert unchanged == original
    assert scaled.startswith(".subckt outer a b\nC0 a b 1f\nR0 a b 2\n.ends\n")
    assert scaled.count(" a b 0.8f\n") == 319
    assert scaled.count(" a b 2.4\n") == 675
    with pytest.raises(RuntimeError, match="RC card count"):
        sensitivity.scale_native_cards(original.replace("C318 a b 1f\n", ""),
                                       Decimal("1"), Decimal("1"))


def test_sensitivity_scope_and_two_public_baselines():
    plan = json.loads((RESULTS / "plan.json").read_text(encoding="utf-8"))
    result = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert plan["no_physical_uncertainty_interval_or_full_grid_claim"] is True
    assert result["full_new_pvt_grid"] is False
    assert result["geometry_or_pex_physical_fidelity_certification"] is False
    assert result["actual_transients"] == 28
    assert result["numerical_pairs_qualified"] == 14
    assert plan["expected_transients"] == 28
    assert {p["point_id"]
            for p in plan["points"]} == set(sensitivity.POINT_IDS)
    assert [
        (s["name"], s["r_factor"], s["c_factor"]) for s in plan["scenarios"]
    ] == [(name, str(r), str(c)) for name, r, c in sensitivity.CASES]
    assert hashlib.sha256(
        (ROOT / "layout_compact_repair/evidence/attempt1/atlas.rc.spice").read_bytes()
    ).hexdigest() == plan["submitted_rc_netlist_sha256"]
    public_csv = ROOT / "results/study/postlayout_pvt45/measurements.csv"
    assert hashlib.sha256(public_csv.read_bytes()).hexdigest(
    ) == plan["public_results_csv_sha256"]
    with public_csv.open(encoding="utf-8", newline="") as handle:
        baselines = {row["point_id"]: row for row in csv.DictReader(handle)}
    assert len(result["pairs"]) == 14
    assert {(p["point_id"], p["scenario"]) for p in result["pairs"]} == {
        (point, name) for point in sensitivity.POINT_IDS
        for name, _, _ in sensitivity.CASES
    }
    for pair in result["pairs"]:
        assert pair["numerical_comparison"]["passed"] is True
        fine = pair["finest"]
        assert fine["status"] == "success"
        assert fine["step_ps"] == 5
        assert fine["actual_mos_si_count"] == 27
        assert fine["point_id"] == pair["point_id"]
        assert fine["scenario"] == pair["scenario"]
        assert fine["runtime_markers"]["qualified"] is True
        measured = {m["deadline_ns"]: m for m in fine["measurements"]}
        assert 1.0 in measured and 2.0 in measured
        if pair["scenario"] == "original":
            assert pair["archived_baseline_comparison"]["qualified_at_1ns_and_2ns"]
            row = baselines[pair["point_id"]]
            assert measured[2.0]["outcome"] == row["outcome_2ns"]
            assert measured[1.0]["outcome"] == row["outcome_1ns"]
            assert measured[2.0]["core_energy_fj"] == pytest.approx(
                float(row["core_energy_fj"]), rel=0.01
            )
        else:
            assert pair["archived_baseline_comparison"] is None
        assert measured[2.0]["outcome"] == (
            "unresolved" if pair["point_id"] == "c37-rc-m03"
            and pair["scenario"] in ("c_high", "both_high") else "correct"
        )
        assert measured[1.0]["outcome"] == (
            "unresolved" if pair["point_id"] == "c37-rc-m03" else "correct"
        )
        if measured[2.0]["outcome"] == "unresolved":
            assert measured[2.0]["decision_time_ns"] is None
