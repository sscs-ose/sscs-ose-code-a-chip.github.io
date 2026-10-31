"""Negative controls for the draft's paired-performance check."""
import unittest
from copy import deepcopy
import review
import sys,tempfile,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'reproduction'))
import reproduce_performance,performance

class PerformanceChecks(unittest.TestCase):
    def setUp(self):
        self.ref=review.read("evidence/reference-performance.json")
        self.cand=review.read("evidence/P0-performance.json")
    def test_measured_pairs(self):
        rows=review.compare_performance(self.ref,self.cand)
        self.assertEqual(len(rows),162)
        self.assertTrue(all(r["completion_ratio"]==r["supply_ratio"]==1 for r in rows))
    def test_slowed_supply_or_completion(self):
        for field in ["completion_cycles","supply_cycles"]:
            with self.subTest(field=field):
                d=deepcopy(self.cand);d["cases"][0][field]+=1
                with self.assertRaises(AssertionError):review.compare_performance(self.ref,d)
    def test_missing_duplicate_and_wrong_bytes(self):
        bad=[]
        d=deepcopy(self.cand);d["cases"].pop();bad.append(d)
        d=deepcopy(self.cand);d["cases"][-1]=deepcopy(d["cases"][0]);bad.append(d)
        d=deepcopy(self.cand);d["cases"][0]["useful_bytes"]-=1;bad.append(d)
        for d in bad:
            with self.assertRaises(AssertionError):review.compare_performance(self.ref,d)
    def test_nonfinite_or_zero_cycles(self):
        for value in [float("nan"),float("inf"),0,-1]:
            d=deepcopy(self.cand);d["cases"][0]["completion_cycles"]=value
            with self.assertRaises(AssertionError):review.compare_performance(self.ref,d)
    def test_measured_path_accounting(self):
        d=review.path_evidence()
        self.assertIn("consume_tile",d["source"])
        self.assertIn("output_bank",d["sink"])
        self.assertAlmostEqual(d["arrival"],19.691730499,places=8)
        self.assertAlmostEqual(d["required"]-d["arrival"],d["slack"],places=5)
        self.assertAlmostEqual(sum(d["delays"])+d["marks"][0][0],d["arrival"],places=8)
        self.assertEqual(len(d["delays"]),5)
    def test_original_performance_input_binding(self):
        result=reproduce_performance.check_inputs()
        self.assertEqual(result["generated_vectors_verified"],9)
        self.assertEqual(result["simulations_run"],0)
    def test_simulator_failure_propagates_and_keeps_log(self):
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder)/"command.log"
            with self.assertRaises(subprocess.CalledProcessError):
                performance.command(Path(folder),[sys.executable,"-c","print('failed simulator');raise SystemExit(3)"],log,5)
            self.assertIn("failed simulator",log.read_text())
    def test_package_integrity(self):
        self.assertEqual(review.verify()["endpoint_pairs"],727)

if __name__=="__main__":unittest.main()
