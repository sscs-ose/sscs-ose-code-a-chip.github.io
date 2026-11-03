"""I7 S04 lexical-boundary regression; no real synthesis or circuit behavior run."""
import copy
import unittest
from unittest.mock import patch

import test_generation_batches as fixture
from hullcirq.generation import GenerationManager
from hullcirq.rtl_checks import INTERFACE_CHECK_VERSION, check_rtl


PORTS = [{"name": "a", "direction": "input", "width": 8, "signed": True},
         {"name": "b", "direction": "input", "width": 8, "signed": False},
         {"name": "y", "direction": "output", "width": 16, "signed": False}]
HEADER = "module cast_node(input wire signed [7:0] a, input wire [7:0] b, output wire [15:0] y);\n"


class PureCastBoundaryTests(unittest.TestCase):
    def check(self, body, *, header=HEADER):
        return check_rtl(header + body + "\nendmodule\n", PORTS, "cast_node", interface_only=True)

    def test_verilog_cast_expressions_pass_s04_without_claiming_synthesis_or_behavior(self):
        for expression in ("$signed(a) * $signed(b)", "$unsigned(a) + $unsigned(b)",
                           "$unsigned($signed(a))", "$signed /* comment */ (a)",
                           "$unsigned\n(b)"):
            with self.subTest(expression=expression), patch("hullcirq.rtl_checks._syntax_check") as compile_rtl:
                result = self.check("assign y = " + expression + ";")
            self.assertEqual(result["validation_status"], "Passed")
            self.assertEqual(result["checks"]["interface"]["checker_version"], INTERFACE_CHECK_VERSION)
            self.assertEqual(result["checks"]["syntax"]["validation_status"], "Not Run")
            self.assertFalse(result["checks"]["functional_verification"]["executed"])
            compile_rtl.assert_not_called()

    def test_other_system_functions_and_file_tasks_are_still_rejected(self):
        for call in ('$fopen("outside.txt")', '$readmemh("outside.hex", a)',
                     '$writememh("outside.hex", a)', '$system("outside command")',
                     '$display("output")', '$finish', '$random', '$time', '$clog2(a)'):
            with self.subTest(call=call), patch("hullcirq.rtl_checks._syntax_check") as compile_rtl:
                result = self.check("assign y = " + call + ";")
            self.assertEqual(result["validation_status"], "Failed")
            self.assertIn("unsafe_system_task", [d["code"] for d in result["diagnostics"]])
            compile_rtl.assert_not_called()

    def test_allowlisted_cast_does_not_hide_another_nested_or_following_unsafe_call(self):
        for expression in ('$signed($fopen("outside.txt"))',
                           '$unsigned(a) + $random', '$signed(a); $display("outside")'):
            with self.subTest(expression=expression):
                result = self.check("assign y = " + expression + ";")
                self.assertEqual(result["validation_status"], "Failed")
                self.assertIn("unsafe_system_task", [d["code"] for d in result["diagnostics"]])

    def test_cast_names_must_be_exact_case_sensitive_invocations(self):
        for token in ("$signedness(a)", "$unsigned_extra(a)", "$unsigned$display(a)",
                      "$Signed(a)", "$UNSIGNED(a)", "$signed", "$unsigned;"):
            with self.subTest(token=token):
                result = self.check("assign y = " + token + ";")
                self.assertIn("unsafe_system_task", [d["code"] for d in result["diagnostics"]])

    def test_directive_and_systemverilog_guards_remain_independent_of_legal_casts(self):
        for body, code in (('`include "outside.v"\nassign y=$signed(a);', "unsafe_directive"),
                           ("initial begin y=$unsigned(a); end", "unsupported_language"),
                           ("logic state; assign y=$signed(a);", "unsupported_language")):
            with self.subTest(code=code):
                result = self.check(body)
                self.assertEqual(result["validation_status"], "Failed")
                self.assertIn(code, [d["code"] for d in result["diagnostics"]])

    def test_legal_cast_does_not_relax_exact_external_port_contract(self):
        result = self.check("assign y=$signed(a);", header=HEADER.replace("[15:0] y", "[7:0] y"))
        self.assertEqual(result["validation_status"], "Failed")
        self.assertIn("rtl_width_mismatch", [d["code"] for d in result["diagnostics"]])


class FrozenCastDiagnosticTests(unittest.TestCase):
    setUp = fixture.GenerationBatchTests.setUp
    close = fixture.GenerationBatchTests.close
    run_batch = fixture.GenerationBatchTests.run_batch

    def test_legacy_failed_cast_diagnostic_is_not_rechecked_or_changed_on_reload(self):
        def answer(messages, parameters, cancelled, event):
            self.calls.append(copy.deepcopy(messages))
            with self.generation.lock:
                header = self.generation._state["jobs"][-1]["context"]["requested_module_header"]
            return {"execution_status": "Completed", "raw_content": "```verilog\n" + header + "wire signed [7:0] local_value;\nassign local_value=$signed(8'hff);\nendmodule\n```", "error": None, "finish_reason": "stop"}
        def historical_check(rtl, expected, module, compiler=None, **options):
            result = check_rtl(rtl, expected, module, compiler, **options)
            result["checks"]["interface"].pop("checker_version", None)
            result["validation_status"] = result["checks"]["interface"]["validation_status"] = "Failed"
            result["diagnostics"].append({"code": "unsafe_system_task", "severity": "error", "message": "System tasks/functions and file access are not permitted in this candidate."})
            return result
        with patch("hullcirq.generation.check_rtl", side_effect=historical_check):
            self.run_batch(response=answer)
        frozen = copy.deepcopy(self.generation._state["jobs"])
        raw = self.generation.path.read_bytes()
        with patch("hullcirq.generation.check_rtl", side_effect=AssertionError("Frozen diagnostics must not be re-executed")):
            loaded = GenerationManager(self.store)
        self.addCleanup(loaded.close)
        self.assertEqual(loaded._state["jobs"], frozen)
        self.assertEqual(loaded.path.read_bytes(), raw)
        for job in loaded._state["jobs"]:
            self.assertEqual(job["validation_status"], "Failed")
            self.assertNotIn("checker_version", job["checks"]["interface"])


if __name__ == "__main__":
    unittest.main()
