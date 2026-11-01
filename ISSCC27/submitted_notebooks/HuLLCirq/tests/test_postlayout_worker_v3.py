"""Worker admission software QA; these fixtures run no EDA or circuit."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import postlayout_execution as host
from hullcirq.domain import DomainError


class EventWorkerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.worker = host.fixed_worker_definition('v3')
        self.cwd = self.worker['WORK_ROOT'] + '/original-job-SOFTWARE_QA'

    def test_version_preserves_original_compilation_and_pins_both_observers(self):
        old = host.fixed_worker_definition('v2')
        self.assertEqual(self.worker['COMPILE_ARGV'], old['COMPILE_ARGV'])
        self.assertEqual(self.worker['TOOL_SHA256'], old['TOOL_SHA256'])
        self.assertEqual(len(self.worker['PLUGIN_SHA256']), 6)
        for name, digest in old['PLUGIN_SHA256'].items():
            self.assertEqual(self.worker['PLUGIN_SHA256'][name], digest)
        self.assertEqual(host.sha(host.WORKER_V3_SOURCE), host.WORKER_V3_SHA256)

    def test_simulation_admission_rejects_extra_plugin_manifest_and_nested_path(self):
        argv = list(self.worker['simulation_argv'](self.cwd))
        validate = self.worker['validate_operation']
        expected = self.worker['COMPILE_INPUTS'] + ('simulation.vvp', *self.worker['PLUGIN_SHA256'])
        self.assertEqual(validate(argv, self.cwd), expected)
        for changed in (argv + ['-m', 'other'], argv[:-1],
                        [value.replace('event-signal-manifest.tsv', 'other.tsv') for value in argv]):
            with self.subTest(argv=changed), self.assertRaises(self.worker['WorkerError']):
                validate(changed, self.cwd)
        for cwd in (self.cwd + '/child', self.cwd + '/../other', '/tmp/original-job-SOFTWARE_QA'):
            with self.subTest(cwd=cwd), self.assertRaises(self.worker['WorkerError']):
                validate(list(self.worker['simulation_argv'](cwd)), cwd)

    def test_host_never_starts_an_unbound_v3_command(self):
        with patch.object(host.subprocess, 'Popen') as popen:
            with self.assertRaises(DomainError):
                host.execute(['unbound'], self.worker['CONFIGURATION'],
                             ROOT / '.work/m2l/dynamic/original-job-SOFTWARE_QA',
                             'simulate', None, 10, worker_version='v3')
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
