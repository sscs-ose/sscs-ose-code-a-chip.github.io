"""Guard the exact saved source and independent oracle used by reproduction."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('saved_example_replay', ROOT/'scripts/replay_saved_example.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)
from hullcirq.domain import DomainError

TEST_PARENT = ROOT/'.work/test-saved-replay'
TEST_PARENT.mkdir(parents=True, exist_ok=True)


class SavedReplayInputTests(unittest.TestCase):
    def test_fresh_runtime_profile_is_resolved_without_running_tools(self):
        import fresh_runtime
        with tempfile.TemporaryDirectory(dir=TEST_PARENT) as temp:
            local = Path(temp)
            profile = {'kind':'native', 'executable':str(local/'iverilog')}
            (local/'compiler.json').write_text(json.dumps(profile),encoding='utf-8')
            args = SimpleNamespace(compiler_config=None,fresh_runtime=True,distribution='Ubuntu')
            with mock.patch.object(fresh_runtime,'host_root',return_value=local):
                self.assertEqual(replay.compiler_configuration(args),profile)

    def test_saved_sources_and_original_42_expectations_match(self):
        provenance, plan = replay.load_inputs()
        self.assertEqual(provenance['required_output_samples'], 42)
        self.assertEqual(plan['vector_count'], 14)
        self.assertEqual(plan['interface']['clock']['period_ns'], 50)

    def test_edited_adopted_rtl_is_rejected_before_simulation(self):
        with tempfile.TemporaryDirectory(dir=TEST_PARENT) as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to(ROOT.resolve()))
            case = Path(temp)/'case'
            shutil.copytree(replay.CASE, case)
            (case/'release_counter.v').write_bytes(b'module changed; endmodule\n')
            with self.assertRaisesRegex(ValueError, 'input changed'):
                replay.load_inputs(case)

    def test_repinning_changed_oracle_does_not_replace_original_contract(self):
        with tempfile.TemporaryDirectory(dir=TEST_PARENT) as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to(ROOT.resolve()))
            case = Path(temp)/'case'
            shutil.copytree(replay.CASE, case)
            path = case/'verification-plan.json'
            plan = json.loads(path.read_text(encoding='utf-8'))
            plan['contract']['cycles'][2]['expect']['data_out'] = 0
            data = (json.dumps(plan,indent=2)+'\n').encode()
            path.write_bytes(data)
            provenance_path=case/'provenance.json'
            provenance=json.loads(provenance_path.read_text(encoding='utf-8'))
            provenance['files']['verification-plan.json']['sha256']=hashlib.sha256(data).hexdigest()
            provenance['files']['verification-plan.json']['bytes']=len(data)
            provenance_path.write_text(json.dumps(provenance),encoding='utf-8')
            with self.assertRaisesRegex((ValueError, DomainError), 'Frozen|changed|mismatch'):
                replay.load_inputs(case)


if __name__=='__main__':
    unittest.main()
