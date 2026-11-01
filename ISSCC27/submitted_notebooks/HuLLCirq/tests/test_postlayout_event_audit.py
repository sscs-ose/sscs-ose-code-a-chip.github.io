"""Event-auditor software fixtures only, never substitute NPU job evidence."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.postlayout_event_audit import audit_postlayout_events, read_event_transcript, EventAuditError


SDF = '''(DELAYFILE (SDFVERSION "3.0") (DESIGN "software_fixture_only") (DIVIDER .) (TIMESCALE 1ns)
 (CELL (CELLTYPE "sky130_fd_sc_hd__dfxtp_2") (INSTANCE _fixture_)
  (DELAY (ABSOLUTE (IOPATH CLK Q (0.012:0.012:0.012) (0.010:0.010:0.010))))
  (TIMINGCHECK
   (SETUP (posedge D) (posedge CLK) (0.055:0.055:0.055))
   (HOLD (posedge D) (posedge CLK) (-0.028:-0.028:-0.028))
   (SETUP (negedge D) (posedge CLK) (0.108:0.108:0.108))
   (HOLD (negedge D) (posedge CLK) (-0.041:-0.041:-0.041))
   (WIDTH (posedge CLK) (0.270:0.270:0.270))
   (WIDTH (negedge CLK) (0.265:0.265:0.265)))))'''


def transcript(changes=None, *, initial_d="1", initial_clk="0", initial_q="x", end=2000,
               include_source=False, initial_bus=None):
    """Produce the actual logger schema using explicit software-only values."""
    pins = ["D", "CLK", "D_delayed", "CLK_delayed", "Q"]
    mapping = {pin: index for index, pin in enumerate(pins, 1)}
    names = {pin: f"tb.dut._fixture_.{pin}" for pin in pins}
    if include_source:
        mapping["source"] = len(mapping) + 1
        names["source"] = "tb.clk"
    if initial_bus is not None:
        mapping["bus"] = len(mapping) + 1
        names["bus"] = "tb.bus"
    initial = {"D": initial_d, "D_delayed": initial_d, "CLK": initial_clk,
               "CLK_delayed": initial_clk, "Q": initial_q, "source": "0", "bus": initial_bus}
    widths = {pin: len(initial[pin]) for pin in mapping}
    roles = {pin: pin if pin in pins else "SOURCE_CLK" if pin == "source" else "TOP_INPUT" for pin in mapping}
    lines = ["HULLCIRQ_EVENTS_V1", "META\ttime_precision\t-12", "META\tdelta_identity\tunavailable"]
    lines += [f"SIGNAL\t{index}\t{names[pin]}\t{widths[pin]}\t{roles[pin]}" for pin, index in mapping.items()]
    counts = {index: Counter(initial=0, change=0, settled=0) for index in mapping.values()}
    seq = 0
    for kind in ("initial", "settled"):
        for pin, index in mapping.items():
            seq += 1
            lines.append(f"EVENT\t{seq}\t0\t{index}\t{kind}\t{initial[pin]}")
            counts[index][kind] += 1
    if changes is None:
        changes = [(500, "CLK", "1"), (512, "Q", "1"), (1000, "CLK", "0"),
                   (1500, "CLK", "1"), (2000, "CLK", "0")]
    expanded = []
    for time, pin, value in changes:
        expanded.append((time, pin, value))
        if pin in ("CLK", "D"):
            expanded.append((time, pin + "_delayed", value))
    for time, pin, value in expanded:
        seq += 1
        index = mapping[pin]
        lines.append(f"EVENT\t{seq}\t{time}\t{index}\tchange\t{value}")
        counts[index]["change"] += 1
    lines += [f"COUNTS\t{index}\t{item['initial']}\t{item['change']}\t{item['settled']}" for index, item in counts.items()]
    lines.append(f"END\t{seq}\t{end}\t{len(mapping)}\t{seq}\t0\t1")
    raw = ("\n".join(lines) + "\n").encode("ascii")
    summary = {"schema_version": "hullcirq-event-capture-summary-v1", "time_precision": -12,
               "delta_identity": "unavailable", "ordering": "callback_invocation_order",
               "initial_scope": "cbStartOfSimulation_before_initial_threads",
               "settled_scope": "time_zero_cbReadOnlySynch", "manifest_signal_count": len(mapping),
               "resolved_signal_count": len(mapping), "events_written": seq, "last_sequence": seq,
               "end_time_ps": end, "dropped_events": 0, "output_bytes": len(raw),
               "initial_events": len(mapping), "settled_events": len(mapping),
               "change_callbacks": sum(item["change"] for item in counts.values()),
               "error_count": 0, "flush_complete": True, "capture_complete": True,
               "end_callback_seen": True, "last_error": "none", "max_events": 20000000,
               "max_bytes": 1073741824, "signals": [
                   {"id": index, "path": names[pin], "resolved_path": names[pin], "width": widths[pin],
                    "role": roles[pin], "object_type": 36,
                    **{key + "_count": value for key, value in counts[index].items()}}
                   for pin, index in mapping.items()]}
    return raw, summary


class PostlayoutEventAuditTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / ".work/m2l/event_audit"
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.events = self.folder / "software-fixture-events.tsv"
        self.summary = self.folder / "software-fixture-summary.json"

    def write(self, raw, summary):
        self.events.write_bytes(raw)
        self.summary.write_text(json.dumps(summary), encoding="utf-8")

    def audit(self, changes=None, *, sdf=SDF, audit_kwargs=None, **kwargs):
        raw, summary = transcript(changes, **kwargs)
        self.write(raw, summary)
        return audit_postlayout_events(sdf, self.events, self.summary, **(audit_kwargs or {}))

    def test_all_q_events_checked_and_limited_pass_cannot_adopt(self):
        result = self.audit()
        self.assertEqual(result["finite_event_status"], "Passed", result)
        self.assertEqual(result["status"], "Unsupported")
        self.assertFalse(result["adoption_permitted"])
        self.assertFalse(result["complete_timing_model_qualification"])
        self.assertEqual(result["counts"]["captures"], 2)
        self.assertEqual(result["counts"]["q_expected_transitions"], 1)
        self.assertEqual(result["counts"]["q_matched_transitions"], 1)
        self.assertTrue(result["cells"][0]["q_trace_complete"])

    def test_previous_deadline_only_extra_q_pulse_counterexample_is_failed(self):
        result = self.audit([(500, "CLK", "1"), (512, "Q", "1"), (800, "Q", "0"),
                             (900, "Q", "1"), (1000, "CLK", "0"),
                             (1500, "CLK", "1"), (2000, "CLK", "0")])
        self.assertEqual(result["status"], "Failed")
        self.assertEqual(result["counts"]["q_extra_transitions"], 2)

    def test_wrong_early_capture_recovery_and_wrong_late_capture_fail(self):
        for time in (501, 513):
            with self.subTest(time=time):
                changes = [(500, "CLK", "1"), (time, "Q", "0"), (514, "Q", "1"), (1000, "CLK", "0")]
                result = self.audit(changes)
                self.assertEqual(result["status"], "Failed")
                self.assertGreater(result["counts"]["q_extra_transitions"], 0)
                self.assertGreater(result["counts"]["q_missing_transitions"], 0)

    def test_wrong_value_exact_deadline_and_missing_q_fail(self):
        for changes in ([(500, "CLK", "1"), (512, "Q", "0"), (1000, "CLK", "0")],
                        [(500, "CLK", "1"), (1000, "CLK", "0")]):
            result = self.audit(changes)
            self.assertEqual(result["status"], "Failed")

    def test_same_timestamp_q_pulse_all_ordered_events_retained(self):
        result = self.audit([(500, "CLK", "1"), (512, "Q", "1"), (800, "Q", "0"),
                             (800, "Q", "x"), (800, "Q", "1"), (1000, "CLK", "0")])
        self.assertEqual(result["counts"]["q_observed_transitions"], 4)
        self.assertEqual(result["counts"]["q_extra_transitions"], 3)
        self.assertEqual(result["status"], "Failed")
        self.assertFalse(result["delta_region_identity_known"])

    def test_no_op_callbacks_are_retained_but_not_invented_edges(self):
        result = self.audit([(400, "D", "1"), (500, "CLK", "1"), (512, "Q", "1"),
                             (800, "Q", "1"), (1000, "CLK", "0")])
        self.assertEqual(result["finite_event_status"], "Passed", result)
        self.assertEqual(result["counts"]["no_op_callbacks"], 3)
        self.assertEqual(result["counts"]["q_observed_transitions"], 1)

    def test_original_negative_hold_windows_are_not_clamped(self):
        result = self.audit([(460, "D", "1"), (500, "CLK", "1"),
                             (512, "Q", "1"), (1000, "CLK", "0")], initial_d="0")
        self.assertEqual(result["status"], "Failed")
        error = next(item for item in result["diagnostics"] if item["code"] == "signed_setuphold_violation")
        self.assertEqual(error["open_window_ps"], [445, 472])
        self.assertEqual(error["hold_ps"], -28)

    def test_signed_open_endpoints_and_late_data_have_stricter_guard(self):
        for time in (445, 472, 480, 500):
            with self.subTest(time=time):
                result = self.audit([(time, "D", "1"), (500, "CLK", "1"),
                                     (512, "Q", "1"), (1000, "CLK", "0")], initial_d="0")
                self.assertEqual(result["counts"]["signed_violations"], 0)
                self.assertEqual(result["finite_event_status"], "Unsupported")

    def test_same_timestamp_data_glitch_is_not_hidden(self):
        result = self.audit([(480, "D", "0"), (480, "D", "1"), (500, "CLK", "1"),
                             (512, "Q", "1"), (1000, "CLK", "0")])
        self.assertEqual(result["finite_event_status"], "Unsupported")
        diagnostic = next(item for item in result["diagnostics"] if item["code"] == "capture_window_unqualified")
        self.assertEqual([event[2] for event in diagnostic["changes"]], ["0", "1"])

    def test_full_x_module_path_timing_uses_original_previous_q_polarity(self):
        cases = [("0", 510, 1512), ("1", 512, 1510)]
        for first, first_deadline, x_deadline in cases:
            with self.subTest(first=first):
                changes = [(500, "CLK", "1"), (first_deadline, "Q", first),
                           (1000, "CLK", "0"), (1200, "D", "x"), (1500, "CLK", "1"),
                           (x_deadline, "Q", "x"), (2000, "CLK", "0")]
                result = self.audit(changes, initial_d=first)
                self.assertEqual(result["finite_event_status"], "Passed", result)
                self.assertEqual(result["counts"]["q_matched_transitions"], 2)
                self.assertEqual(result["counts"]["constant_unknown_captures"], 1)

    def test_constant_x_z_data_remain_unknown_not_binary_success(self):
        for value in ("x", "z"):
            result = self.audit([(500, "CLK", "1"), (1000, "CLK", "0")], initial_d=value)
            self.assertEqual(result["finite_event_status"], "Passed", result)
            self.assertEqual(result["counts"]["constant_unknown_captures"], 1)
            self.assertEqual(result["counts"]["q_observed_transitions"], 0)

    def test_q_z_and_initial_known_q_are_rejected(self):
        result = self.audit([(500, "CLK", "1"), (512, "Q", "z"), (1000, "CLK", "0")])
        self.assertEqual(result["status"], "Failed")
        result = self.audit(initial_q="0")
        self.assertEqual(result["status"], "Failed")

    def test_width_equality_passes_and_zero_width_same_tick_fails(self):
        for width, status in ((269, "Failed"), (270, "Passed"), (0, "Failed")):
            changes = [(500, "CLK", "1")]
            if width < 12:
                changes += [(500 + width, "CLK", "0"), (512, "Q", "1")]
            else:
                changes += [(512, "Q", "1"), (500 + width, "CLK", "0")]
            result = self.audit(changes)
            self.assertEqual(result["finite_event_status"], status, result)

    def test_clock_unknown_after_start_and_missing_capture_fail_closed(self):
        for changes in ([(500, "CLK", "1"), (512, "Q", "1"), (900, "CLK", "x"), (1000, "CLK", "0")], []):
            self.assertEqual(self.audit(changes)["finite_event_status"], "Unsupported")

    def test_zero_q_delay_and_overlapping_pulse_are_unsupported(self):
        sdf = SDF.replace("0.012", "0.400")
        result = self.audit([(500, "CLK", "1"), (800, "CLK", "0"), (900, "Q", "1")], sdf=sdf)
        self.assertEqual(result["finite_event_status"], "Unsupported")
        result = self.audit([(500, "CLK", "1"), (500, "Q", "1"), (1000, "CLK", "0")], sdf=SDF.replace("0.012", "0.000"))
        self.assertEqual(result["finite_event_status"], "Unsupported")

    def test_late_trace_end_is_not_a_zero_missing_count(self):
        result = self.audit([(500, "CLK", "1")], end=500)
        self.assertEqual(result["finite_event_status"], "Unsupported")

    def test_missing_malformed_duplicate_end_sequence_and_counts_fail_closed(self):
        raw, summary = transcript()
        altered = [raw.rsplit(b"END", 1)[0], raw[:-1], raw + b"END\t0\t0\t0\t0\t0\t1\n",
                   raw.replace(b"EVENT\t11\t", b"EVENT\t12\t", 1),
                   raw.replace(b"COUNTS\t1\t1\t0\t1", b"COUNTS\t1\t1\t1\t1"),
                   raw.replace(b"SIGNAL\t2\t", b"SIGNAL\t1\t", 1)]
        for value in altered:
            with self.subTest(value=value[-80:]):
                self.write(value, summary)
                result = audit_postlayout_events(SDF, self.events, self.summary)
                self.assertEqual(result["finite_event_status"], "Unsupported", result)

    def test_postclose_summary_required_counts_and_identity_bindings(self):
        raw, base = transcript()
        cases = []
        for key, value in [("flush_complete", False), ("capture_complete", False), ("end_callback_seen", False),
                           ("dropped_events", 1), ("output_bytes", len(raw) + 1), ("events_written", 0),
                           ("error_count", False), ("time_precision", -9), ("ordering", "delta_order")]:
            summary = copy.deepcopy(base); summary[key] = value; cases.append(summary)
        summary = copy.deepcopy(base); summary["signals"].append(copy.deepcopy(summary["signals"][0])); cases.append(summary)
        summary = copy.deepcopy(base); summary["signals"][0]["change_count"] = 1; cases.append(summary)
        summary = copy.deepcopy(base); summary["signals"][0]["resolved_path"] = "other.d"; cases.append(summary)
        for summary in cases:
            self.write(raw, summary)
            with self.subTest(summary=summary), self.assertRaises(EventAuditError):
                read_event_transcript(self.events, self.summary)

    def test_initial_and_settled_snapshot_and_vector_width_are_checked(self):
        raw, summary = transcript(initial_bus="0011")
        self.write(raw, summary)
        actual = read_event_transcript(self.events, self.summary)
        self.assertEqual(actual.traces[actual.paths["tb.bus"]][0][2], "0011")
        for malformed in (raw.replace(b"settled\t0011", b"settled\t0111"),
                          raw.replace(b"initial\t0011", b"initial\t11")):
            self.write(malformed, summary)
            with self.assertRaises(EventAuditError):
                read_event_transcript(self.events, self.summary)

    def test_startup_requires_raw_bound_source_not_caller_boolean(self):
        changes = [(20, "CLK", "0"), (500, "source", "1"), (520, "CLK", "1"),
                   (532, "Q", "1"), (1000, "source", "0"), (1020, "CLK", "0")]
        options = {"source_clock_path": "tb.clk", "qualify_initial_clock_settlement": True}
        result = self.audit(changes, initial_clk="x", include_source=True, audit_kwargs=options)
        self.assertEqual(result["finite_event_status"], "Unsupported")
        tb = self.folder / "source_fixture_only.v"
        tb.write_bytes(b"module tb;\n  reg clk=0, rst=1;\nendmodule\n")
        options.update(testbench_path=tb, expected_testbench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest())
        result = self.audit(changes, initial_clk="x", include_source=True, audit_kwargs=options)
        self.assertEqual(result["finite_event_status"], "Passed", result)
        self.assertEqual(result["counts"]["qualified_initial_clock_settlements"], 1)
        self.assertEqual(result["ignored_startup_or_reset_cycles"], 0)
        options["expected_testbench_sha256"] = "0" * 64
        self.assertEqual(self.audit(changes, initial_clk="x", include_source=True, audit_kwargs=options)["finite_event_status"], "Unsupported")

    def test_copy_mismatch_and_unsupported_offsets(self):
        raw, summary = transcript()
        raw = raw.replace(b"EVENT\t12\t500\t4\tchange\t1", b"EVENT\t12\t501\t4\tchange\t1")
        summary["output_bytes"] = len(raw)
        self.write(raw, summary)
        result = audit_postlayout_events(SDF, self.events, self.summary)
        self.assertEqual(result["status"], "Failed", result)
        for offset in (True, 1, -1):
            self.assertEqual(self.audit(audit_kwargs={"offset_ps": offset})["finite_event_status"], "Unsupported")

    def startup_options(self):
        tb = self.folder / "startup_source_fixture_only.v"
        tb.write_bytes(b"module tb;\n  reg clk=0, rst=1;\nendmodule\n")
        return {"source_clock_path": "tb.clk", "qualify_initial_clock_settlement": True,
                "testbench_path": tb, "expected_testbench_sha256": hashlib.sha256(tb.read_bytes()).hexdigest()}

    def test_source_clock_correspondence_rejects_early_and_same_tick_local_edge(self):
        options = self.startup_options()
        for local in (400, 500):
            changes = [(20, "CLK", "0"), (local, "CLK", "1"), (local + 12, "Q", "1"),
                       (500, "source", "1"), (1000, "source", "0"), (1020, "CLK", "0")]
            changes.sort(key=lambda item: item[0])
            with self.subTest(local=local):
                result = self.audit(changes, initial_clk="x", include_source=True, audit_kwargs=options)
                self.assertEqual(result["finite_event_status"], "Unsupported", result)

    def test_q_before_original_first_capture_cannot_hide_in_startup_unsupported(self):
        changes = [(20, "CLK", "0"), (100, "Q", "0"), (500, "source", "1"),
                   (520, "CLK", "1"), (532, "Q", "1"), (1000, "source", "0"), (1020, "CLK", "0")]
        result = self.audit(changes, initial_clk="x", include_source=True, audit_kwargs=self.startup_options())
        self.assertEqual(result["status"], "Failed", result)
        self.assertTrue(any(item["code"] == "q_transition_before_first_capture" for item in result["diagnostics"]))

    def test_only_an_exact_end_time_falling_edge_may_be_pending(self):
        options = self.startup_options()
        changes = [(20, "CLK", "0"), (500, "source", "1"), (520, "CLK", "1"),
                   (532, "Q", "1"), (1000, "source", "0")]
        result = self.audit(changes, end=1000, initial_clk="x", include_source=True, audit_kwargs=options)
        self.assertEqual(result["finite_event_status"], "Passed", result)
        self.assertEqual(result["counts"]["unobserved_final_source_falling_edges"], 1)
        result = self.audit(changes, end=2000, initial_clk="x", include_source=True, audit_kwargs=options)
        self.assertEqual(result["finite_event_status"], "Unsupported", result)

    def test_summary_object_quotas_last_error_and_duplicate_json_keys_fail_closed(self):
        raw, summary = transcript()
        self.write(raw, summary)
        for value in ("[]", '{"complete":true,"complete":false}', 'null'):
            self.summary.write_text(value, encoding="utf-8")
            result = audit_postlayout_events(SDF, self.events, self.summary)
            self.assertEqual(result["finite_event_status"], "Unsupported", result)
        for key, value in [("max_events", 0), ("max_bytes", 0), ("last_error", "some error")]:
            other = copy.deepcopy(summary); other[key] = value
            self.write(raw, other)
            self.assertEqual(audit_postlayout_events(SDF, self.events, self.summary)["finite_event_status"], "Unsupported")

    def test_startup_source_declaration_inside_comment_or_string_is_not_proof(self):
        options = self.startup_options()
        changes = [(20, "CLK", "0"), (500, "source", "1"), (520, "CLK", "1"),
                   (532, "Q", "1"), (1000, "source", "0"), (1020, "CLK", "0")]
        for text in (b'module tb;\n/*\n reg clk=0, rst=1;\n*/\nendmodule\n',
                     b'module tb;\n// reg clk=0, rst=1;\nendmodule\n',
                     b'module tb;\ninitial $display("reg clk=0, rst=1;");\nendmodule\n'):
            options["testbench_path"].write_bytes(text)
            options["expected_testbench_sha256"] = hashlib.sha256(text).hexdigest()
            result = self.audit(changes, initial_clk="x", include_source=True, audit_kwargs=options)
            self.assertEqual(result["finite_event_status"], "Unsupported", result)

    def test_inputs_are_read_only_and_old_auditor_unchanged(self):
        raw, summary = transcript()
        self.write(raw, summary)
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (self.events, self.summary)]
        audit_postlayout_events(SDF, self.events, self.summary)
        self.assertEqual(before, [hashlib.sha256(path.read_bytes()).hexdigest() for path in (self.events, self.summary)])


if __name__ == "__main__":
    unittest.main()
