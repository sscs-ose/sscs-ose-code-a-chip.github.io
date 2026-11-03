"""Software record-language checks; no model, live circuit, or EDA execution."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.global_generation import (build_global_plan, expected_pe_records,
    parse_runtime_records, pe_records_match_plan, public_transfer_counts)


class LegacyGlobalLaneRecordsTests(unittest.TestCase):
    def setUp(self):
        design = json.loads((ROOT / "examples/npu_all_nodes_project.json").read_text(encoding="utf-8"))
        self.plan = build_global_plan(design)
        lanes = [0, 10, 11, 12, 13, 14, 15, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        self.records = expected_pe_records(self.plan)
        for record, lane in zip(self.records, lanes):
            record["lane"] = lane

    def stdout(self, records):
        plan = self.plan
        text = "".join(f"HULLCIRQ_OUTPUT index={i} value={value} cycle={100+i}\n"
                       for i, value in enumerate(plan["recipe"]["expected_outputs"]))
        text += "".join(f"HULLCIRQ_PUBLIC stream={name} transfers={count}\n"
                        for name, count in public_transfer_counts(plan).items())
        text += "".join(f"HULLCIRQ_PE instance={r['instance']} lane={r['lane']} inputs={r['inputs']} outputs={r['outputs']}\n"
                        for r in records)
        return text + f"HULLCIRQ_GLOBAL_PASS outputs=16 vector_hash={plan['vector_hash']}\nHULLCIRQ_PUBLIC_PASS vector_hash={plan['public_boundary_vector_hash']}\n"

    def test_bijective_observed_lane_mapping_keeps_all_original_numeric_checks(self):
        self.assertTrue(pe_records_match_plan(self.plan, self.records))
        passed, outputs, _, observed = parse_runtime_records(self.stdout(self.records), self.plan)
        self.assertTrue(passed)
        self.assertEqual(observed, self.records)
        self.assertEqual([output["value"] for output in outputs], self.plan["recipe"]["expected_outputs"])
        # Existing historical identity-order records remain valid too.
        self.assertTrue(parse_runtime_records(self.stdout(expected_pe_records(self.plan)), self.plan)[0])

    def test_missing_duplicate_out_of_range_and_bad_count_records_are_rejected(self):
        changes = (
            lambda rows: rows.pop(),
            lambda rows: rows.append(copy.deepcopy(rows[0])),
            lambda rows: rows[1].update(lane=rows[0]["lane"]),
            lambda rows: rows[1].update(lane=16),
            lambda rows: rows[1].update(lane=-1),
            lambda rows: rows[1].update(instance=0),
            lambda rows: rows[1].update(instance=16),
            lambda rows: rows[1].update(instance=-1),
            lambda rows: rows.reverse(),
            lambda rows: rows[1].update(inputs=0),
            lambda rows: rows[1].update(outputs=self.plan["recipe"]["source_job"]["k"] - 1),
        )
        for index, change in enumerate(changes):
            rows = copy.deepcopy(self.records)
            change(rows)
            with self.subTest(index=index):
                self.assertFalse(pe_records_match_plan(self.plan, rows))
                self.assertFalse(parse_runtime_records(self.stdout(rows), self.plan)[0])

    def test_original_output_stream_and_failure_markers_are_still_required(self):
        original = self.stdout(self.records)
        variants = (
            original.replace("HULLCIRQ_OUTPUT index=0 value=", "HULLCIRQ_OUTPUT index=0 value=9", 1),
            original.replace("HULLCIRQ_PUBLIC stream=control_config transfers=1", "HULLCIRQ_PUBLIC stream=control_config transfers=0", 1),
            original + "HULLCIRQ_FAIL software negative case\n",
            original.replace("HULLCIRQ_PUBLIC_PASS", "MISSING_PUBLIC_PASS"),
        )
        for index, value in enumerate(variants):
            with self.subTest(index=index):
                self.assertFalse(parse_runtime_records(value, self.plan)[0])


if __name__ == "__main__":
    unittest.main()
