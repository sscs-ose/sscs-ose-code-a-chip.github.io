"""Software qualification fixtures only; these are never NPU-job evidence."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.sdf_timing_audit import audit_sdf_timing, timing_records, TimingAuditError


SDF = '''(DELAYFILE (SDFVERSION "3.0") (DESIGN "fixture_only") (DIVIDER .) (TIMESCALE 1ns)
 (CELL (CELLTYPE "sky130_fd_sc_hd__dfxtp_2") (INSTANCE _fixture_)
  (DELAY (ABSOLUTE (IOPATH CLK Q (0.012:0.012:0.012) (0.010:0.010:0.010))))
  (TIMINGCHECK
   (SETUP (posedge D) (posedge CLK) (0.055:0.055:0.055))
   (HOLD (posedge D) (posedge CLK) (-0.028:-0.028:-0.028))
   (SETUP (negedge D) (posedge CLK) (0.108:0.108:0.108))
   (HOLD (negedge D) (posedge CLK) (-0.041:-0.041:-0.041))
   (WIDTH (posedge CLK) (0.270:0.270:0.270))
   (WIDTH (negedge CLK) (0.265:0.265:0.265)))))'''


def vcd(events=None, *, initial_d="1", initial_q="x", omit=None, timescale="1ps"):
    # Scalar identifiers and times are test-fixture data, not a design recipe.
    definitions = {"D": "!", "CLK": '"', "D_delayed": "#", "CLK_delayed": "%", "Q": "$"}
    header = ["$timescale " + timescale + " $end", "$scope module tb $end",
              "$scope module dut $end", "$scope module _fixture_ $end"]
    header += [f"$var wire 1 {code} {name} $end" for name, code in definitions.items() if name != omit]
    header += ["$upscope $end"] * 3 + ["$enddefinitions $end", "$dumpvars"]
    header += [initial_d + "!", '0"', initial_d + "#", "0%", initial_q + "$", "$end"]
    if events is None:
        events = [(500, '1"'), (512, "1$"), (1000, '0"'), (1500, '1"'), (2000, '0"')]
    for time, value in events:
        header.extend(["#" + str(time), value])
        if value.endswith('"'):
            header.append(value[0] + "%")
    return "\n".join(header) + "\n"


class TimingAuditTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".work" / "m2k" / "timing_audit_qa"
        parent.mkdir(parents=True, exist_ok=True)
        self.folder = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "software_fixture_only.vcd"

    def audit(self, text, sdf=SDF, **kwargs):
        self.path.write_text(text, encoding="ascii")
        return audit_sdf_timing(sdf, self.path, **kwargs)

    def test_exact_negative_windows_and_complete_mapping(self):
        record = timing_records(SDF)[0]
        self.assertEqual(record["pairs"]["posedge"], {"setup_ps": 55, "hold_ps": -28})
        result = self.audit(vcd())
        self.assertEqual(result["status"], "Passed", result)
        self.assertEqual(result["counts"]["mapped_cells"], 1)
        self.assertEqual(result["counts"]["required_pins"], 5)
        self.assertEqual(result["counts"]["clock_captures"], 2)
        self.assertEqual(result["counts"]["capture_qualified"], 2)
        self.assertEqual(result["ignored_startup_or_reset_cycles"], 0)
        self.assertEqual(result["counts"]["initial_unknown_q"], 1)
        self.assertFalse(result["notifier_violation_semantics_qualified"])

    def test_transition_in_negative_hold_window_fails_signed_check(self):
        result = self.audit(vcd([(460, "1!"), (460, "1#"), (500, '1"'),
                                 (512, "1$"), (1000, '0"')], initial_d="0"))
        self.assertEqual(result["status"], "Failed")
        event = next(x for x in result["diagnostics"] if x["code"] == "signed_setuphold_violation")
        self.assertEqual(event["open_window_ps"], [445, 472])
        self.assertEqual(event["hold_ps"], -28)

    def test_raw_signed_endpoints_remain_open(self):
        for time in (445, 472):
            with self.subTest(time=time):
                result = self.audit(vcd([(time, "1!"), (time, "1#"), (500, '1"'),
                                         (512, "1$"), (1000, '0"')], initial_d="0"))
                self.assertEqual(result["counts"]["signed_violations"], 0)
                self.assertEqual(result["status"], "Unsupported")

    def test_after_negative_hold_window_is_not_clamped_but_guard_fails(self):
        result = self.audit(vcd([(480, "1!"), (480, "1#"), (500, '1"'),
                                 (512, "1$"), (1000, '0"')], initial_d="0"))
        self.assertEqual(result["counts"]["signed_violations"], 0)
        self.assertEqual(result["counts"]["capture_unqualified"], 1)
        self.assertEqual(result["status"], "Unsupported")

    def test_same_timestamp_data_pulse_is_not_erased(self):
        result = self.audit(vcd([(480, "0!"), (480, "1!"), (480, "0#"),
                                 (480, "1#"), (500, '1"'), (512, "1$"), (1000, '0"')]))
        self.assertEqual(result["counts"]["capture_unqualified"], 1)
        event = next(x for x in result["diagnostics"] if x["code"] == "capture_window_unqualified")
        self.assertEqual(len(event["changes"]), 2)

    def test_constant_unknown_data_is_preserved_not_blanket_rejected(self):
        for unknown in ("x", "z"):
            with self.subTest(unknown=unknown):
                result = self.audit(vcd([(500, '1"'), (1000, '0"')], initial_d=unknown))
                self.assertEqual(result["status"], "Passed", result)
                self.assertEqual(result["counts"]["constant_unknown_captures"], 1)
                self.assertEqual(result["counts"]["q_checks"], 1)

    def test_x_transition_in_capture_window_is_unqualified(self):
        result = self.audit(vcd([(480, "x!"), (480, "x#"), (500, '1"'), (1000, '0"')]))
        self.assertEqual(result["status"], "Unsupported")
        self.assertEqual(result["counts"]["capture_unqualified"], 1)

    def test_width_high_and_low_and_equality(self):
        for width, status in ((269, "Failed"), (270, "Passed")):
            with self.subTest(width=width):
                result = self.audit(vcd([(500, '1"'), (512, "1$"), (500 + width, '0"'), (1500, '1"'), (2000, '0"')]))
                self.assertEqual(result["status"], status, result)
        result = self.audit(vcd([(500, '1"'), (512, "1$"), (1000, '0"'), (1200, '1"'), (1600, '0"')]))
        self.assertEqual(result["counts"]["width_violations"], 1)

    def test_wrong_delayed_copy_and_q_are_failed(self):
        result = self.audit(vcd([(500, '1"'), (512, "0$"), (1000, '0"')]))
        self.assertEqual(result["counts"]["q_mismatches"], 1)
        self.assertEqual(result["status"], "Failed")
        result = self.audit(vcd().replace("1#", "0#"))
        self.assertEqual(result["counts"]["delayed_data_mismatches"], 1)
        self.assertEqual(result["status"], "Failed")

    def test_missing_pin_unknown_clock_and_no_clock_fail_closed(self):
        for text in (vcd(omit="Q"), vcd().replace('0"', 'x"', 1).replace("0%", "x%", 1), vcd([(2000, "1$")])):
            with self.subTest(text=text):
                result = self.audit(text)
                self.assertEqual(result["status"], "Unsupported", result)

    def test_delayed_clock_mapping_and_copy_cannot_be_skipped(self):
        result = self.audit(vcd(omit="CLK_delayed"))
        self.assertEqual(result["status"], "Unsupported")
        result = self.audit(vcd().replace("1%", "0%", 1))
        self.assertEqual(result["status"], "Failed")
        self.assertEqual(result["counts"]["delayed_clock_mismatches"], 1)

    def test_time_scope_offset_and_record_coverage_errors(self):
        for text, kwargs in ((vcd(timescale="10ps"), {}), (vcd(), {"dut_scope": "other.dut"}),
                             (vcd(), {"offset_ps": True}), (vcd(), {"offset_ps": {}})):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.audit(text, **kwargs)["status"], "Unsupported")
        for text in (SDF.replace("-0.028", "-0.0285"), SDF.replace("(WIDTH (negedge CLK) (0.265:0.265:0.265))", ""),
                     SDF.replace("(WIDTH (negedge CLK)", "(PERIOD (negedge CLK)")):
            with self.subTest(sdf=text), self.assertRaises(TimingAuditError):
                timing_records(text)

    def test_initial_capture_is_not_silently_skipped(self):
        result = self.audit(vcd([(50, '1"'), (62, "1$"), (1000, '0"')]))
        self.assertEqual(result["counts"]["clock_captures"], 1)
        self.assertEqual(result["counts"]["capture_unqualified"], 1)
        self.assertEqual(result["ignored_startup_or_reset_cycles"], 0)
        self.assertEqual(result["status"], "Unsupported")

    def test_missing_and_outside_cell_timing_are_never_dropped(self):
        original = SDF.index("  (TIMINGCHECK")
        missing = SDF[:original] + "))"
        with self.assertRaises(TimingAuditError):
            timing_records(missing)
        extra = SDF[:-1] + "(TIMINGCHECK (WIDTH (posedge CLK) (0.1))))"
        with self.assertRaises(TimingAuditError):
            timing_records(extra)

    def test_truncated_q_deadline_and_dump_suspension_fail_closed(self):
        result = self.audit(vcd([(500, '1"')]))
        self.assertEqual(result["status"], "Unsupported")
        self.assertTrue(any(x["code"] == "trace_ends_before_q_deadline" for x in result["diagnostics"]))
        self.assertEqual(self.audit(vcd().replace("#1000", "$dumpoff\n#1000"))["status"], "Unsupported")

    def test_aliased_delayed_copy_and_four_state_signed_edges(self):
        text = vcd().replace("$var wire 1 # D_delayed $end", "$var wire 1 ! D_delayed $end").replace("1#\n", "")
        self.assertEqual(self.audit(text)["status"], "Passed")
        result = self.audit(vcd([(460, "1!"), (460, "1#"), (500, '1"'),
                                 (512, "1$"), (1000, '0"')], initial_d="x"))
        self.assertEqual(result["counts"]["signed_violations"], 1)

    def test_explicit_startup_settlement_is_proved_not_ignored(self):
        text = vcd([(20, '0"'), (500, '1"'), (512, "1$"), (1000, '0"')])
        text = text.replace('0"', 'x"', 1).replace('0%', 'x%', 1)
        text = text.replace('$scope module dut $end', '$var wire 1 & clk $end\n$scope module dut $end')
        text = text.replace('$dumpvars', '$dumpvars\n0&').replace('#500\n', '#500\n1&\n')
        self.assertEqual(self.audit(text)["status"], "Unsupported")
        result = self.audit(text, qualify_initial_clock_settlement=True, source_clock_path='tb.clk')
        self.assertEqual(result["status"], "Passed", result)
        self.assertEqual(result["counts"]["qualified_initial_clock_settlements"], 1)
        self.assertEqual(result["counts"]["clock_captures"], 1)
        self.assertEqual(result["ignored_startup_or_reset_cycles"], 0)
        self.assertEqual(result["cells"][0]["startup_settlement_ps"], 20)

    def test_startup_special_case_rejects_wrong_source_q_and_later_unknown(self):
        text = vcd([(20, '0"'), (500, '1"'), (512, "1$"), (1000, '0"')])
        text = text.replace('0"', 'x"', 1).replace('0%', 'x%', 1)
        text = text.replace('$scope module dut $end', '$var wire 1 & clk $end\n$scope module dut $end')
        text = text.replace('$dumpvars', '$dumpvars\n0&').replace('#500\n', '#500\n1&\n')
        invalid = [text.replace('0&', '1&', 1), text.replace('x$', '0$', 1),
                   text.replace('#1000', '#600\nx"\nx%\n#1000')]
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                result = self.audit(candidate, qualify_initial_clock_settlement=True, source_clock_path='tb.clk')
                self.assertNotEqual(result["status"], "Passed")
        self.assertEqual(self.audit(text, qualify_initial_clock_settlement=True)["status"], "Unsupported")

    def test_original_sdf_inventory_is_read_only(self):
        # Original input is used solely for parser coverage, not a dynamic run.
        source = ROOT / ".work/m2j/simulator_probe/layout.sdf"
        if not source.exists():
            self.skipTest("Original SDF not present; software fixtures remain independent")
        records = timing_records(source.read_text(encoding="utf-8"))
        self.assertEqual(len(records), 1991)
        unshared = [record["instance"] for record in records
                    if max(-pair["hold_ps"] for pair in record["pairs"].values())
                    > min(pair["setup_ps"] for pair in record["pairs"].values())]
        self.assertEqual(unshared, ["_16685_", "_16691_"])


if __name__ == "__main__":
    unittest.main()
