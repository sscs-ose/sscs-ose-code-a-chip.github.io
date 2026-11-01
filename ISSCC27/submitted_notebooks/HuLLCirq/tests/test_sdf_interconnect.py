"""Software-only parser/mapping QA; fixture arcs are not NPU evidence."""
import copy
import gzip
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.sdf_interconnect import (
    InterconnectError, audit_native_interconnect_log, cell_port_directions, interconnect_inventory,
    interconnect_records, parse_sdf, original_metadata_diagnostics,
)


MODELS = "module BUF (X,A); output X; input A; endmodule"
NETLIST = """module software_qa(incoming, outgoing);
input incoming;
output outgoing;
wire internal;
BUF first (.A(incoming), .X(internal));
BUF second (.A(internal), .X(outgoing));
endmodule
"""


def sdf(records=None):
    if records is None:
        records = """
(INTERCONNECT incoming first.A (0.001:0.002:0.003) (0.004:0.005:0.006))
(INTERCONNECT first.X second.A (0.000:0.000:0.000) (0.001:0.001:0.001))
(INTERCONNECT second.X outgoing (0.007:0.007:0.007) (0.008:0.008:0.008))
"""
    return f"""(DELAYFILE (SDFVERSION "3.0") (DESIGN "software_qa")
(DIVIDER .) (TIMESCALE 1ns)
(CELL (CELLTYPE "software_qa") (INSTANCE) (DELAY (ABSOLUTE {records}))))"""


class SdfInterconnectTests(unittest.TestCase):
    @staticmethod
    def native_log():
        # Explicit software-QA log values, never an actual tool transcript.
        return "\n".join([
            "SDF INFO: input.sdf:3: INTERCONNECT with port1 = incoming index = 0, port2 = first.A index = 0",
            "SDF INFO: input.sdf:3: Created a vpiInterModPath",
            "SDF INFO: input.sdf:3: Putting delay: 0.002000 for index 0",
            "SDF INFO: input.sdf:3: Putting delay: 0.005000 for index 1",
            "SDF INFO: input.sdf:4: INTERCONNECT with port1 = first.X index = 0, port2 = second.A index = 0",
            "SDF INFO: input.sdf:4: Created a vpiInterModPath",
            "SDF INFO: input.sdf:4: Putting delay: 0.000000 for index 0",
            "SDF INFO: input.sdf:4: Putting delay: 0.001000 for index 1",
            "SDF INFO: input.sdf:5: INTERCONNECT with port1 = second.X index = 0, port2 = outgoing index = 0",
            "SDF INFO: input.sdf:5: Created a vpiInterModPath",
            "SDF INFO: input.sdf:5: Putting delay: 0.007000 for index 0",
            "SDF INFO: input.sdf:5: Putting delay: 0.008000 for index 1",
            "SDF WARNING: input.sdf:10: TIMINGCHECK not supported."])

    def test_complete_arc_inventory_is_read_only_and_not_annotation_success(self):
        inputs = [NETLIST, sdf(), MODELS]
        before = copy.deepcopy(inputs)
        report = interconnect_inventory(*inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(report["arc_count"], 3)
        self.assertEqual(report["unique_source_count"], 3)
        self.assertEqual(report["top_output_arc_count"], 1)
        self.assertEqual(report["bindings"][1]["original_net"], "internal")
        self.assertEqual(report["bindings"][1]["source_cell_type"], "BUF")
        self.assertEqual(report["bindings"][0]["rise_ps"], 2)
        self.assertEqual(report["bindings"][0]["fall_ps"], 5)
        self.assertFalse(report["dynamic_validation_executed"])
        self.assertFalse(report["source_bytes_modified"])
        self.assertFalse(report["full_sdf_equivalence"])
        self.assertIn("Inventory only", report["qualification_status"])

    def test_corner_choice_is_explicit_and_does_not_round(self):
        self.assertEqual(interconnect_records(sdf(), selection="min")[1][0]["rise_ps"], 1)
        self.assertEqual(interconnect_records(sdf(), selection="max")[1][0]["rise_ps"], 3)
        with self.assertRaisesRegex(InterconnectError, "selection"):
            interconnect_records(sdf(), selection="automatic")
        for number in ("-0.001", "0.0001", "NaN", "Infinity", "1::3", "0_1"):
            with self.subTest(number=number), self.assertRaises(InterconnectError):
                interconnect_records(sdf().replace("0.001:0.002:0.003", number))

    def test_duplicate_destinations_are_rejected(self):
        first = "(INTERCONNECT incoming first.A (0.001) (0.001))"
        with self.assertRaisesRegex(InterconnectError, "Duplicate"):
            interconnect_records(sdf(first + first))

    def test_cross_net_or_reversed_pin_arcs_are_rejected(self):
        bad = [sdf().replace("first.X second.A", "incoming second.A"),
               sdf().replace("first.X second.A", "first.A second.A"),
               sdf().replace("first.X second.A", "first.X second.X")]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(InterconnectError):
                interconnect_inventory(NETLIST, text, MODELS)

    def test_multiple_original_drivers_are_rejected(self):
        text = NETLIST.replace("endmodule", "BUF duplicate (.A(incoming), .X(internal));\nendmodule")
        with self.assertRaisesRegex(InterconnectError, "Multiple drivers"):
            interconnect_inventory(text, sdf(), MODELS)

    def test_all_source_fanout_arcs_remain_individual_records(self):
        text = NETLIST.replace("wire internal;", "wire internal;\nwire unused;")
        text = text.replace("endmodule", "BUF third (.A(internal), .X(unused));\nendmodule")
        records = sdf().replace("(INTERCONNECT second.X outgoing", "(INTERCONNECT first.X third.A (0.010) (0.020))\n(INTERCONNECT second.X outgoing")
        report = interconnect_inventory(text, records, MODELS)
        self.assertEqual(report["arc_count"], 4)
        self.assertEqual(report["maximum_fanout"], 2)
        self.assertEqual({tuple(binding["destination_endpoint"]) for binding in report["bindings"] if binding["source"] == "first.X"},
                         {("second", "A"), ("third", "A")})

    def test_escaped_instance_names_bind_without_treating_literal_dot_as_hierarchy(self):
        text = NETLIST.replace("BUF first ", "BUF \\first.name ")
        records = sdf().replace("first.A", "first\\.name.A").replace("first.X", "first\\.name.X")
        report = interconnect_inventory(text, records, MODELS)
        self.assertEqual(report["bindings"][0]["destination_endpoint"], ["first.name", "A"])
        self.assertEqual(report["bindings"][1]["source_endpoint"], ["first.name", "X"])

    def test_vector_port_bits_are_individual_scalar_arcs(self):
        text = NETLIST.replace("input incoming;", "input [1:0] incoming;").replace(".A(incoming)", ".A(incoming[1])")
        report = interconnect_inventory(text, sdf().replace("INTERCONNECT incoming ", "INTERCONNECT incoming[1] "), MODELS)
        self.assertEqual(report["bindings"][0]["original_net"], "incoming[1]")

    def test_model_variants_must_agree_and_unknown_direction_fails_closed(self):
        self.assertEqual(cell_port_directions(MODELS + MODELS)["BUF"]["A"], "input")
        for model in (MODELS + MODELS.replace("input A", "output A"), MODELS.replace("input A;", ""), MODELS.replace("input A", "inout A")):
            with self.subTest(model=model), self.assertRaises(InterconnectError):
                interconnect_inventory(NETLIST, sdf(), model)

    def test_unsupported_arc_shapes_or_incomplete_tokens_are_rejected(self):
        bad = [sdf().replace("(ABSOLUTE", "(INCREMENT"), sdf().replace("1ns", "10ps"),
               sdf().replace("(0.004:0.005:0.006)", "(0.004:0.005:0.006) (0.010)"),
               sdf().replace("(INTERCONNECT incoming first.A", "(INTERCONNECT incoming nested.first.A"),
               sdf() + " (INTERCONNECT x y (1) (1))", sdf()[:-1], sdf() + '"']
        for text in bad:
            with self.subTest(text=text), self.assertRaises(InterconnectError):
                interconnect_records(text)

    def test_quoted_metadata_comments_are_preserved_as_strings(self):
        root = parse_sdf('(DELAYFILE (VENDOR "https://example.invalid/*literal*/") /* comment */)')
        self.assertEqual(root[1], ["VENDOR", '"https://example.invalid/*literal*/"'])
        with self.assertRaises(InterconnectError):
            parse_sdf('(DELAYFILE /* incomplete comment)')

    def test_native_log_requires_every_endpoint_handle_and_selected_delay(self):
        inventory = interconnect_inventory(NETLIST, sdf(), MODELS)
        result = audit_native_interconnect_log(inventory, self.native_log())
        self.assertTrue(result["binding_complete"])
        self.assertEqual(result["bound_native_log_arc_count"], 3)
        self.assertEqual(result["bound_delay_value_log_count"], 6)
        self.assertEqual(result["ignored_timingcheck_warning_count"], 1)
        self.assertFalse(result["timing_checks_supported_by_native_simulator"])
        self.assertFalse(result["native_delay_readback_executed"])
        self.assertFalse(result["full_sdf_equivalence"])
        bad = [self.native_log().replace("first.A index = 0", "first.A index = 1"),
               self.native_log().replace("0.002000", "0.003000"),
               self.native_log().replace("SDF INFO: input.sdf:3: Created a vpiInterModPath\n", ""),
               self.native_log() + "\nSDF INFO: input.sdf:5: Putting delay: 0.008000 for index 1",
               self.native_log().replace("input.sdf:4: Created", "wrong.sdf:4: Created"),
               self.native_log() + "\nSDF ERROR: input.sdf:12: Could not find intermodpath!",
               self.native_log() + "\nSDF WARNING: input.sdf:12: COND not supported."]
        for log in bad:
            with self.subTest(log=log), self.assertRaises(InterconnectError):
                audit_native_interconnect_log(inventory, log)

    def test_native_log_cannot_omit_or_duplicate_an_entire_arc(self):
        inventory = interconnect_inventory(NETLIST, sdf(), MODELS)
        lines = self.native_log().splitlines()
        for log in ("\n".join(lines[4:]), "\n".join(lines[:4] + lines)):
            with self.subTest(log=log), self.assertRaisesRegex(InterconnectError, "count"):
                audit_native_interconnect_log(inventory, log)

    def test_native_vector_bit_index_must_match_the_original_pin(self):
        text = NETLIST.replace("input incoming;", "input [133:0] incoming;").replace(".A(incoming)", ".A(incoming[133])")
        inventory = interconnect_inventory(text, sdf().replace("INTERCONNECT incoming ", "INTERCONNECT incoming[133] "), MODELS)
        log = self.native_log().replace("port1 = incoming index = 0", "port1 = incoming index = 133")
        self.assertTrue(audit_native_interconnect_log(inventory, log)["binding_complete"])
        with self.assertRaises(InterconnectError):
            audit_native_interconnect_log(inventory, self.native_log())

    def test_original_metadata_classification_is_pinned_to_exact_source_and_errors(self):
        # Read-only source/header qualification, not original-job simulation.
        original = gzip.decompress((ROOT / "results/npu_postlayout_readiness/artifacts/input.sdf.gz").read_bytes()).decode("utf-8")
        errors = "SDF ERROR: input.sdf:9: Chosen value not defined.\nSDF ERROR: input.sdf:11: Chosen value not defined."
        diagnostics = original_metadata_diagnostics(original, errors)
        self.assertEqual([item["field"] for item in diagnostics], ["VOLTAGE", "TEMPERATURE"])
        self.assertTrue(all(item["selected_metadata_value_established"] is False for item in diagnostics))
        for source, log in ((original.replace("1.800::1.800", "1.800:1.800:1.800"), errors),
                            (original, errors + "\nSDF ERROR: input.sdf:55: Chosen value not defined."),
                            (original, errors.splitlines()[0]), (original, errors.replace(":9:", ":10:")),
                            (original, errors.replace("Chosen value not defined.", "Could not find intermodpath!"))):
            with self.subTest(log=log), self.assertRaises(InterconnectError):
                original_metadata_diagnostics(source, log)


if __name__ == "__main__":
    unittest.main()
