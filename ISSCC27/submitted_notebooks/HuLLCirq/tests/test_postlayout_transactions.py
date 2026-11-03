"""Parser regression fixtures only; these do not replace the original NPU job."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

PROJECT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('transactions', PROJECT/'scripts/audit_postlayout_transactions.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class RecordedTransactions(unittest.TestCase):
    def check_trace(self, extra=''):
        names=MODULE.SIGNALS
        codes=['!', '"', 'A', '#', '$', 'a', '%', '&', 'B', 'b', '(', ')', '*']
        text='$timescale 1ps $end\n$scope module hullcirq_global_tb $end\n'
        for name,code in zip(names,codes):
            text+=f'$var wire {8 if name in ("config_data","load_data","output_data") else 1} {code} {name} $end\n'
        text+='$upscope $end\n$enddefinitions $end\n#0\n'
        for name,code in zip(names,codes):
            text+=(f'b1010 {code}\n' if name in ('config_data','load_data','output_data') else '0'+code+'\n')
        text+=extra+'#25000\n1!\n'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'recorded.vcd';path.write_text(text,encoding='ascii')
            return MODULE.audit(path)

    def test_vector_identifiers_are_case_sensitive(self):
        report=self.check_trace()
        self.assertEqual(report['status'],'Passed')
        self.assertEqual(report['signal_edge_observations'],12)
        self.assertFalse(report['S14_adopted'])

    def test_pre_edge_transition_cannot_be_hidden_by_equal_final_value(self):
        report=self.check_trace('#24500\nb1011 A\n#24900\nb1010 A\n')
        self.assertEqual(report['status'],'Unsupported')
        self.assertEqual(report['recorded_changes_in_sample_windows'],2)
        self.assertEqual(report['diagnostics'][0]['signal'],'config_data')

    def test_transition_exactly_at_receiving_edge_is_rejected(self):
        report=self.check_trace('#25000\nb1011 a\n')
        self.assertEqual(report['status'],'Unsupported')
        self.assertEqual(report['diagnostics'][0]['signal'],'load_data')

if __name__=='__main__':unittest.main()
