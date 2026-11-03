from itertools import product

import pandas as pd
import pytest

from comparator_atlas.study import POLICIES
from comparator_atlas.study_report import explorer_cube, paired_energy


def test_explorer_payload_keeps_complete_grid_and_explicit_nulls():
    rows = []
    for design, case, policy, deadline, value in product(
        ("baseline", "lvt_base_3b"), ("A", "B"), POLICIES, (0.5, 1.0), (-1, 0, 1),
    ):
        unavailable = case == "B" and policy == "deadline_aware"
        rows.append({
            "design_name": design, "case_id": case, "policy": policy, "deadline_ns": deadline,
            "input_mv": value, "outcome": "calibration_unavailable" if unavailable else "correct",
            "decision_time_ns": None if unavailable else 0.3,
            "core_energy_fj": None if unavailable else 100,
            "trim_code": None if unavailable else -2,
        })
    reports = [
        {"design_name": design, "case_id": case, "used_for_design_selection": case == "A"}
        for design, case in product(("baseline", "lvt_base_3b"), ("A", "B"))
    ]
    cube = explorer_cube(pd.DataFrame(rows), reports, "lvt_base_3b")
    assert len(cube["rows"]) == 2 * 2 * 4 * 2 * 3
    assert cube["trainingCases"] == [0]
    unavailable = [row for row in cube["rows"] if row[5] == 3]
    assert unavailable
    assert all(row[6:] == [None, None, None] for row in unavailable)


def test_energy_comparison_matches_points_but_keeps_wrong_decisions():
    rows = []
    for design, scale in (("baseline", 1), ("lvt_base_3b", 1.2)):
        for case, energy, outcome in (("A", 100, "correct"), ("B", 200, "wrong"), ("C", 300, "correct")):
            available = not (design == "baseline" and case == "C")
            rows.append({
                "design_name": design, "case_id": case, "input_mv": 1,
                "policy": "local_boundary", "deadline_ns": 1, "policy_available": available,
                "core_energy_fj": energy * scale if available else None, "outcome": outcome,
            })
    result = paired_energy(pd.DataFrame(rows), "lvt_base_3b")
    assert result["matched_points"] == 2
    assert result["baseline_fj"] == 150
    assert result["selected_fj"] == 180
    assert result["relative_change_percent"] == pytest.approx(20)
