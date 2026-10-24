"""Fresh-driver deterministic controls; no test in this module starts ngspice."""

from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import patch

import support
import reproduce


def history(point_id="test", mode="rc", energies=(100, 100)):
    return [{
        "attempt_id": f"a{i + 1:04d}", "point_id": point_id, "mode": mode,
        "physical_identity": {"point_id": point_id, "mode": mode, "fresh": True},
        "max_step_ps": step, "status": "success",
        "startup_markers": {"qualified": True}, "geometry_device_count": 27,
        "waveform_validated": True, "reset_ok": True, "launch_confirmed": True,
        "measurements": [{
            "deadline_ns": deadline, "decision": 1, "outcome": "correct",
            "decision_time_ns": 0.1, "core_energy_fj": energy, "reset_ok": True,
            "qp_at_deadline_v": 1.8, "qn_at_deadline_v": 0,
        } for deadline in support.DEADLINES],
    } for i, (step, energy) in enumerate(zip(support.STEPS, energies))]


class PlanTests(unittest.TestCase):
    def test_no_mode_shows_help_and_never_constructs_study(self):
        with patch.object(sys, "argv", ["reproduce.py"]), patch("sys.stdout", new_callable=io.StringIO) as output, \
                patch.object(reproduce, "FreshStudy", side_effect=AssertionError("must not execute")):
            self.assertEqual(reproduce.main(), 0)
        self.assertIn("--smoke", output.getvalue())
        self.assertIn("--full", output.getvalue())

    def test_smoke_is_exactly_the_four_authorized_initial_transients(self):
        self.assertEqual(support.initial_order("smoke"), [
            ("c01-schematic-m10", 10), ("c01-rc-m10", 10),
            ("c01-schematic-m10", 5), ("c01-rc-m10", 5),
        ])
        self.assertEqual(support.cap("smoke"), 4)
        self.assertEqual(len(support.points("smoke")), 2)

    def test_full_initial720_and_all2520_deck_hashes_match_frozen_study_plan(self):
        reference = json.loads((support.HERE / "parity-reference.json").read_text())
        points = support.points("full")
        self.assertEqual(len(points), 360)
        self.assertEqual(len({tuple(p["condition"]) for p in points}), 45)
        self.assertEqual(sum(p["mode"] == "rc" for p in points), 180)
        self.assertEqual(support.canonical_sha256(points), reference["matrix_points_canonical_sha256"])
        self.assertEqual(support.canonical_sha256(support.initial_order("full")),
                         reference["initial720_order_canonical_sha256"])
        decks = {
            p["point_id"]: {str(step): hashlib.sha256(support.make_deck(p, step).encode()).hexdigest()
                           for step in support.STEPS}
            for p in points
        }
        self.assertEqual(support.canonical_sha256(decks), reference["all2520_decks_canonical_sha256"])

    def test_single_scale_native_rc_and_actual_geometry_queries_are_preserved(self):
        point = support.points("smoke")[1]
        text = support.make_deck(point, 5)
        native = (support.ENTRY / support.PROTOCOL["circuit"]["rc_path"]).read_text().rstrip()
        self.assertIn(native, text)
        self.assertEqual(text.count("scale=1u"), 1)
        self.assertEqual(text.count("echo NOMINAL27_GEOMETRY "), 27)
        self.assertIn("PVT45W47_NUM_THREADS $num_threads", text)
        self.assertIn("PVT45W47_COMPAT $ngbehavior", text)
        self.assertIn("Cqp qp 0 5f\nCqn qn 0 5f", text)
        self.assertIn("../../model-source", text)
        self.assertNotIn("OneDrive", text)

    def test_source_closure_has_no_checkpoint_or_private_history_requirement(self):
        audit = support.source_audit()
        self.assertTrue(audit["no_historical_checkpoint_or_old_job_receipt_required"])
        self.assertEqual(audit["rc_contract"]["device_count"], 27)
        self.assertEqual(len(audit["rc_contract"]["mapped_devices"]), 27)
        files = json.loads((support.HERE / "source-pins.json").read_text())["files"]
        self.assertFalse(any("remaining.json" in p or "checkpoint.json" in p
                             or "private-error" in p or "controller-pins" in p for p in files))

    def test_caps_no_rerun_and_no_refinement_before_initial720(self):
        smoke = [{"point_id": p, "max_step_ps": s} for p, s in support.initial_order("smoke")]
        with self.assertRaises(support.IntegrityError):
            support.check_charge("smoke", smoke, "c01-rc-m10", 2.5)
        initial = [{"point_id": p, "max_step_ps": s} for p, s in support.initial_order("full")]
        with self.assertRaises(support.IntegrityError):
            support.check_charge("full", initial[:-1], "c01-rc-m10", 2.5)
        with self.assertRaises(support.IntegrityError):
            support.check_charge("full", initial, "c01-rc-m10", 10)
        for p in support.points("full")[:180]:
            support.check_charge("full", initial, p["point_id"], 2.5)
            initial.append({"point_id": p["point_id"], "max_step_ps": 2.5})
        self.assertEqual(len(initial), 900)
        with self.assertRaises(support.IntegrityError):
            support.check_charge("full", initial, support.points("full")[180]["point_id"], 2.5)


class StrictGuardTests(unittest.TestCase):
    def test_exact_console_notice_only_and_real_warning_error_detection(self):
        notice = "Comments and warnings go to log-file: ngspice.log"
        self.assertFalse(support.classify("", notice)["warnings"])
        self.assertTrue(support.classify("Warning: model problem", notice)["warnings"])
        self.assertTrue(support.classify("", notice + "\nWarning: console problem")["warnings"])
        self.assertTrue(support.classify("Error: parse failed", notice)["errors"])
        self.assertTrue(support.classify(notice, "")["warnings"])
        self.assertTrue(support.classify("", notice + " unexpected")["warnings"])

    def test_runtime_markers_cannot_be_missing_wrong_or_repeated(self):
        valid = "PVT45W47_NUM_THREADS 1\nPVT45W47_COMPAT hsa\n"
        self.assertTrue(support.old_windows.runtime_markers(valid)["qualified"])
        for text in ("", valid.replace("1", "8"), valid.replace("hsa", "other"), valid * 2):
            with self.subTest(text=text), self.assertRaises(support.IntegrityError):
                support.old_windows.runtime_markers(text)

    def test_finest_monotone_evidence_and_sensitive_floor_remain_strict(self):
        records = history(energies=(100, 100, 105, 105, 105))
        self.assertTrue(support.phase.history_state(records[:2])["qualified"])
        self.assertFalse(support.phase.history_state(records[:4])["qualified"])
        self.assertTrue(support.phase.history_state(records)["qualified"])
        contrary = history(energies=(100, 105, 100, 105, 100, 105, 100))
        self.assertFalse(support.phase.history_state(contrary)["qualified"])
        contrary[-1]["max_step_ps"] = 10
        with self.assertRaises(support.IntegrityError):
            support.phase.history_state(contrary)

    def test_smoke_reference_compares_same_point_and_fixed_tolerances(self):
        reference = json.loads((support.HERE / "smoke-reference.json").read_text())["records"][0]
        record = {key: copy.deepcopy(reference[key]) for key in ("mode", "point", "max_step_ps", "measurements")}
        self.assertTrue(support.compare_reference(record)["passed"])
        for row in record["measurements"]:
            row["core_energy_fj"] *= 1.02
        self.assertFalse(support.compare_reference(record)["passed"])
        record["point"]["trim_code"] = 1
        with self.assertRaises(support.IntegrityError):
            support.compare_reference(record)


class FreshSchedulerTests(unittest.TestCase):
    def study(self, directory, mode, first_ok=True, failing_point=None):
        obj = object.__new__(reproduce.FreshStudy)
        obj.mode, obj.out = mode, directory
        obj.definitions = support.points(mode)
        obj.by_id = {p["point_id"]: p for p in obj.definitions}
        obj.checkpoint = {"attempts": [], "startup_gate": None, "global_error": None}
        obj.records, obj.stop_reason = {}, None
        obj.persist = lambda: None
        calls = []

        def reserve(self, point_id, step):
            support.check_charge(mode, self.checkpoint["attempts"], point_id, step)
            r = {"attempt_id": f"a{len(self.checkpoint['attempts']) + 1:04d}",
                 "point_id": point_id, "mode": self.by_id[point_id]["mode"], "max_step_ps": step}
            self.checkpoint["attempts"].append(r)
            calls.append(("reserve", point_id, step))
            return r

        def execute(self, attempt):
            calls.append(("execute", attempt["point_id"], attempt["max_step_ps"]))
            record = history(attempt["point_id"], attempt["mode"],
                             energies=(100, 100, 100, 100, 100, 100, 100))[support.STEPS.index(attempt["max_step_ps"])]
            record.update(attempt)
            record["same_point_reference_comparison"] = {"passed": True}
            if not first_ok and len(self.checkpoint["attempts"]) == 1:
                record["status"] = "integrity_error"
            if attempt["point_id"] == failing_point:
                for m in record["measurements"]:
                    m.update(decision=0, outcome="unresolved", decision_time_ns=None)
            return record

        def retain(self, attempt, record):
            self.records[attempt["attempt_id"]] = record
            attempt["status"] = record["status"]
            if record["status"] == "integrity_error":
                self.checkpoint["global_error"] = {"attempt_id": attempt["attempt_id"]}

        def batch(self, requests):
            self_test.assertTrue(self.checkpoint["startup_gate"]["qualified"])
            for point_id, step in requests:
                attempt = self.reserve(point_id, step)
                self.retain(attempt, self.execute(attempt))
            return self.checkpoint["global_error"] is None

        self_test = self
        obj.reserve = MethodType(reserve, obj)
        obj.execute = MethodType(execute, obj)
        obj.retain = MethodType(retain, obj)
        obj.batch = MethodType(batch, obj)
        return obj, calls

    def test_failed_first_counted_trace_prevents_all_other_transients(self):
        with tempfile.TemporaryDirectory() as d, patch("builtins.print"):
            obj, calls = self.study(Path(d), "smoke", first_ok=False)
            obj.run()
            self.assertEqual(len(obj.checkpoint["attempts"]), 1)
            self.assertFalse(obj.report()["qualified_before_independent_owner_stop"])
            self.assertEqual(len([c for c in calls if c[0] == "execute"]), 1)

    def test_fresh_smoke_has_four_charges_no_old_checkpoint_or_extra_smoke(self):
        with tempfile.TemporaryDirectory() as d, patch("builtins.print"):
            obj, calls = self.study(Path(d), "smoke")
            obj.run()
            self.assertEqual([(c[1], c[2]) for c in calls if c[0] == "execute"], support.initial_order("smoke"))
            summary = obj.report()
            self.assertTrue(summary["qualified_before_independent_owner_stop"])
            self.assertEqual(summary["charged_attempts"], 4)
            self.assertFalse(summary["full_new_rerun_performed"])
            self.assertEqual(summary["coverage"]["rc"]["denominator"], 1)

    def test_full_static_scheduler_covers_all720_even_if_functional_point_fails(self):
        with tempfile.TemporaryDirectory() as d, patch("builtins.print"):
            obj, calls = self.study(Path(d), "full", failing_point="c01-rc-m10")
            obj.run()
            self.assertEqual([(c[1], c[2]) for c in calls if c[0] == "execute"], support.initial_order("full"))
            summary = obj.report()
            self.assertEqual(summary["charged_attempts"], 720)
            self.assertEqual(summary["point_rows"], 360)
            self.assertFalse(summary["qualified_before_independent_owner_stop"])
            self.assertEqual(summary["coverage"]["rc"]["2ns"]["unresolved"], 1)
            self.assertEqual(summary["coverage"]["rc"]["2ns"]["correct"], 179)


if __name__ == "__main__":
    unittest.main()
