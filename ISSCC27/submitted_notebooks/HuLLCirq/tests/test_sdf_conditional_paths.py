"""Software fixtures only; these tests are not NPU dynamic timing evidence."""
import unittest

from hullcirq.sdf_conditional_paths import (
    ConditionalPathError, boolean_expression, compare_sdf_replay,
    conditional_path_inventory, iopath_records, read_graph_edges,
)


LIB = '''library (test) { cell (xor_fixture) {
 pin (A) { direction : input; }
 pin (B) { direction : input; }
 pin (X) { direction : output; function : "A ^ B";
  timing () { related_pin : "A"; timing_sense : positive_unate; timing_type : combinational; }
  timing () { related_pin : "A"; timing_sense : negative_unate; timing_type : combinational; }
 } } }'''
MODEL = '''module xor_fixture(X,A,B); output X; input A,B;
 specify
 if ((!B)) (A +=> X) = (0,0);
 if ((B)) (A -=> X) = (0,0);
 endspecify
endmodule'''
SDF = '''(DELAYFILE (SDFVERSION "3.0") (DESIGN "fixture") (DATE "first")
 (DIVIDER .) (TIMESCALE 1ns)
 (CELL (CELLTYPE "xor_fixture") (INSTANCE u)
 (DELAY (ABSOLUTE (IOPATH A X (0.212:0.212:0.212) (0.101:0.101:0.101))
                  (IOPATH A X (0.196:0.196:0.196) (0.190:0.190:0.190))))))'''
GRAPH = '''instance\tsource\tdest\tindex\tsense\tmin_rise_ns\tmax_rise_ns\tmin_fall_ns\tmax_fall_ns
u\tA\tX\t1\tnegative_unate\t0.211655\t0.211655\t0.100936\t0.100936
u\tA\tX\t2\tpositive_unate\t0.195919\t0.195919\t0.190009\t0.190009
'''


class ConditionalPathTests(unittest.TestCase):
    def audit(self, sdf=SDF, graph=GRAPH, lib=LIB, model=MODEL):
        return conditional_path_inventory(sdf, sdf.replace('"first"', '"replayed"'), graph, lib, model)

    def test_replay_excludes_date_only(self):
        report = compare_sdf_replay(SDF, SDF.replace('"first"', '"next"'))
        self.assertFalse(report["raw_text_equal"])
        self.assertTrue(report["text_equal_excluding_date_only"])
        self.assertFalse(compare_sdf_replay(SDF, SDF.replace("0.212", "0.213"))["text_equal_excluding_date_only"])

    def test_modified_replay_rejected(self):
        with self.assertRaises(ConditionalPathError):
            conditional_path_inventory(SDF, SDF.replace("0.212", "0.213"), GRAPH, LIB, MODEL)

    def test_numeric_sense_mapping_ignores_source_order(self):
        report = self.audit()
        self.assertEqual(report["summary"]["unique_record_attributions"], 2)
        self.assertEqual([r["sense"] for r in report["all_record_mappings"]],
                         ["negative_unate", "positive_unate"])
        self.assertEqual(report["summary"]["condition_truth_mismatches"], 0)
        self.assertEqual(report["overall_stage_status"], "Unsupported")
        self.assertFalse(report["adoption_permitted"])
        self.assertEqual(report["summary"]["native_binding_repair_count"], 0)

    def test_graph_order_is_not_fallback(self):
        lines = GRAPH.splitlines()
        report = self.audit(graph="\n".join([lines[0], lines[2], lines[1]]) + "\n")
        self.assertEqual(report["all_record_mappings"][0]["graph_index"], 1)

    def test_nonunique_numeric_profiles_remain_ambiguous(self):
        graph = GRAPH.replace("0.195919", "0.211655").replace("0.190009", "0.100936")
        report = self.audit(graph=graph)
        self.assertEqual(report["summary"]["ambiguous_record_attributions"], 1)
        self.assertEqual(report["summary"]["unmatched_record_attributions"], 1)
        self.assertIsNone(report["all_record_mappings"][0]["sense"])

    def test_missing_and_extra_graph_groups_explicit(self):
        graph = GRAPH.replace("u\tA", "other\tA")
        report = self.audit(graph=graph)
        self.assertEqual(report["summary"]["unmatched_record_attributions"], 2)
        self.assertEqual(report["summary"]["extra_graph_groups"], 1)
        self.assertEqual(report["summary"]["group_mapping_errors"], 1)

    def test_swapped_model_conditions_detected(self):
        report = self.audit(model=MODEL.replace("(!B)", "(B)").replace("(B)) (A -", "(!B)) (A -"))
        self.assertEqual(report["summary"]["condition_truth_mismatches"], 2)

    def test_unknown_model_condition_variable_rejected(self):
        with self.assertRaises(ConditionalPathError):
            self.audit(model=MODEL.replace("!B", "!C"))

    def test_preprocessor_variants_rejected(self):
        with self.assertRaises(ConditionalPathError):
            self.audit(model="`ifdef FUNCTIONAL\n" + MODEL)

    def test_unparsed_model_path_rejected(self):
        with self.assertRaises(ConditionalPathError):
            self.audit(model=MODEL.replace("endspecify", "(B => X) = (0,0);\nendspecify"))

    def test_liberty_conditional_timing_requires_separate_scope(self):
        with self.assertRaises(ConditionalPathError):
            self.audit(lib=LIB.replace("related_pin : \"A\";", 'related_pin : "A"; when : "B";', 1))

    def test_boolean_precedence_postfix_and_no_eval(self):
        names, evaluate = boolean_expression("(!A * B) + (A * B')")
        self.assertEqual(names, {"A", "B"})
        for a in (0, 1):
            for b in (0, 1):
                self.assertEqual(evaluate({"A": a, "B": b}), a ^ b)
        for text in ("A B", "A == B", "A ? B : 0", "A; __import__('os')", "A &", "A && B"):
            with self.subTest(expression=text), self.assertRaises(ConditionalPathError):
                boolean_expression(text)

    def test_graph_min_max_are_analysis_labels(self):
        rows = read_graph_edges(GRAPH.replace("0.211655\t0.211655", "0.212200\t0.211800"))
        self.assertEqual(rows[0]["rise_triple_ps"], [212, 212, 212])

    def test_signed_and_subpicosecond_path_values_rejected(self):
        for value in ("-0.212", "0.2121"):
            with self.subTest(value=value), self.assertRaises(ConditionalPathError):
                iopath_records(SDF.replace("0.212", value))

    def test_duplicate_graph_index_rejected(self):
        graph = GRAPH + GRAPH.splitlines()[1] + "\n"
        with self.assertRaises(ConditionalPathError):
            read_graph_edges(graph)


if __name__ == "__main__":
    unittest.main()
