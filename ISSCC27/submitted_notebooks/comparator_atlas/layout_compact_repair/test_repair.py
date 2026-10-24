"""Offline negative controls, not evidence of a physical or functional pass."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import repair
import compare


class RepairTests(unittest.TestCase):
    def test_frozen_sources_original_policy_and_separate_budget(self):
        report = repair.audit_inherited_inputs()
        self.assertEqual(report["inherited_files_verified"], 26)
        self.assertEqual(report["fixed_non_layout_sha256"],
                         "386bc16f5c55c467d0c7d72ec93d553907f8a2f290aa054b2cd50e0cfcf05454")
        self.assertEqual(repair.PROTOCOL["authorization"]["maximum_new_jobs"], 2)
        self.assertEqual(repair.FIXED_PROTOCOL["budget"]["maximum_new_jobs"], 4)

    def test_protocol_cannot_retune_stimulus_or_erase_prior_budget(self):
        for target, values in (
            ("simulation_schedule", {"primary_deadline_ns": 2}),
            ("simulation_schedule", {"external_load_ff_each": 1}),
            ("authorization", {"maximum_new_jobs": 3}),
        ):
            with self.subTest(values=values), patch.dict(repair.PROTOCOL[target], values):
                with self.assertRaises(AssertionError):
                    repair.audit_inherited_inputs()

    def test_regenerated_routing_is_exact_baseline_plus_four_paints(self):
        placement = json.loads((repair.BASELINE / "placement.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            routing = repair.native_layout.make_routes(out, placement)
            request = repair.append_bridges(out, routing)
            original = (out / "route-request.tcl").read_text()
            self.assertTrue(request.read_text().startswith(original))
            added = request.read_text()[len(original):].splitlines()
            self.assertEqual(len(added), 12)
            self.assertEqual(added.count("paint metal2"), 4)
            self.assertEqual(sum(line.startswith("COMPACT_REPAIR") for line in added), 0)
            self.assertEqual(sum(line.startswith('puts "COMPACT_REPAIR_BRIDGE ') for line in added), 4)
            self.assertNotIn("erase", request.read_text())
            self.assertEqual(routing, json.loads((repair.BASELINE / "routing.json").read_text()))
            repair.validate_placement(placement)

    def test_any_unrelated_route_or_placement_change_is_rejected(self):
        routing = json.loads((repair.BASELINE / "routing.json").read_text())
        routing["terminal_routes"][0]["net"] = "vdd"
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
                AssertionError, "Compact routing changed"):
            repair.append_bridges(Path(directory), routing)
        placement = json.loads((repair.BASELINE / "placement.json").read_text())
        placement["Xinp"]["origin_um"][0] += 0.005
        with self.assertRaisesRegex(AssertionError, "native placement"):
            repair.validate_placement(placement)

    def test_exact_material_addition_covers_pads_with_declared_margin(self):
        baseline = repair.inspect_mag(repair.BASELINE / "atlas.mag")
        actual = copy.deepcopy(baseline)
        actual["rectangles"]["metal2"].extend(
            b["rect_grid"] for b in repair.PROTOCOL["geometry_delta"]["bridges"])
        actual["rectangles"].pop("error_p", None)
        result = repair.check_material_delta(actual, baseline)
        self.assertAlmostEqual(result["added_um2"], 0.3568)
        self.assertAlmostEqual(result["m2_after_um2"], 80.3847)
        self.assertEqual(result["added_grid2"], 14272)
        self.assertEqual(result["native_drc_feedback_rectangles"]["before"], 16)
        self.assertEqual(result["native_drc_feedback_rectangles"]["after"], 0)
        self.assertTrue(result["native_drc_feedback_rectangles"]["not_a_drc_pass_assertion"])
        for bridge in repair.PROTOCOL["geometry_delta"]["bridges"]:
            rectangle = [value * repair.GRID for value in bridge["rect_grid"]]
            self.assertAlmostEqual(rectangle[2] - rectangle[0], 0.36)
            self.assertGreaterEqual(round((rectangle[2] - rectangle[0] - 0.28) / 2, 6), 0.04)
            self.assertLessEqual(rectangle[1], -1.80)
            self.assertGreaterEqual(round(rectangle[3], 6), -0.955)

    def test_missing_bridge_extra_metal_contact_or_label_cannot_pass(self):
        baseline = repair.inspect_mag(repair.BASELINE / "atlas.mag")
        for change in ("missing", "extra_m2", "extra_m1", "contact", "label"):
            actual = copy.deepcopy(baseline)
            bridges = repair.PROTOCOL["geometry_delta"]["bridges"]
            actual["rectangles"]["metal2"].extend(
                b["rect_grid"] for b in (bridges[:3] if change == "missing" else bridges))
            if change.startswith("extra"):
                layer = "metal2" if change == "extra_m2" else "metal1"
                actual["rectangles"][layer].append([100000, 100000, 100100, 100100])
            elif change == "contact":
                actual["rectangles"]["via1"].append([100000, 100000, 100100, 100100])
            elif change == "label":
                actual["label_positions"]["vinp"] = [0, 0, 0, 0]
            with self.subTest(change=change), self.assertRaises(AssertionError):
                repair.check_material_delta(actual, baseline)

    def test_same_area_but_different_geometry_is_not_equivalent(self):
        with self.assertRaisesRegex(AssertionError, "outside declared repair"):
            repair.equal_material_union([[0, 0, 10, 10]], [[1, 0, 11, 10]], "metal2")

    def test_unqualified_numerical_rows_are_not_scorable(self):
        fake = SimpleNamespace(primary_rows=lambda conditions: [
            {"numerically_audited": False} for _ in range(16)])
        with self.assertRaisesRegex(AssertionError, "completed monotone"):
            compare.qualified_rows(fake, [("tt", 1.8, 27)])


class ScheduleTests(unittest.TestCase):
    def run_case(self, failing_condition=None):
        calls = []

        class FakeExperiment:
            def __init__(self, out, models):
                self.records, self.verified_reuse = {}, set()

            def numerical_audit(self, condition):
                if condition not in calls:
                    calls.append(condition)

            def primary_rows(self, conditions):
                return [
                    {"condition": list(condition), "numerically_audited": condition in calls,
                     "mode": mode, "differential_v": differential,
                     "outcome": "unresolved" if condition == failing_condition and mode == "rc" else "correct"}
                    for condition in conditions for mode in ("schematic", "lvs", "c", "rc")
                    for differential in (-0.01, -0.003, 0.003, 0.01)
                ]

            def worst_rc_condition(self, conditions):
                return conditions[-1]

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            repair.write_json(out / "structural-handoff.json", {"qualified": True, "checks": 17})
            repair.write_json(out / "structural-results.json", [{"status": "PASS"} for _ in range(17)])
            with patch.object(compare, "Experiment", FakeExperiment), patch("builtins.print"):
                result = compare.main(out, out / "models")
            report = json.loads((out / "simulation-result.json").read_text())
        return result, calls, report

    def test_tt_failure_gates_all_later_conditions(self):
        result, calls, report = self.run_case(("tt", 1.8, 27))
        self.assertEqual(result, 1)
        self.assertEqual(calls, [("tt", 1.8, 27)])
        self.assertFalse(report["expanded_45_pvt"])

    def test_pilot_failure_is_preserved_without_expansion(self):
        result, calls, report = self.run_case(("ss", 1.62, -40))
        self.assertEqual(result, 1)
        self.assertEqual(calls, [tuple(c) for c in repair.FIXED_PROTOCOL["simulation"]["pilot"]])
        self.assertFalse(report["expanded_45_pvt"])
        self.assertEqual(report["pilot_primary_rows"], 80)

    def test_only_all_audited_pilot_passes_allow_original_45_pvt(self):
        result, calls, report = self.run_case()
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 45)
        self.assertEqual(calls[:5], [tuple(c) for c in repair.FIXED_PROTOCOL["simulation"]["pilot"]])
        self.assertTrue(report["expanded_45_pvt"])
        self.assertEqual(report["primary_rows"], 720)


if __name__ == "__main__":
    unittest.main()
