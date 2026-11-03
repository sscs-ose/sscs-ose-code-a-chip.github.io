"""Isolated launcher/source contracts; these tests never execute EDA tools."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from hullcirq import physical_tools


def launcher_module():
    spec = importlib.util.spec_from_file_location('hullcirq_full_lvs_launcher', ROOT / 'scripts/run_full_lvs.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FullExtractionLauncherTests(unittest.TestCase):
    def setUp(self):
        self.module = launcher_module()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.variant = (ROOT / 'scripts/extract_spice_full.tcl').read_bytes()
        self.original = self.variant.replace(b'\nextract all\n', b'\nextract\n', 1)
        self.original_path = self.directory / 'upstream_extract_spice.tcl'
        self.original_path.write_bytes(self.original)
        original_path = self.original_path

        class Extraction:
            id = 'Magic.SpiceExtraction'

            def get_script_path(self):
                return str(original_path)

        self.extraction = Extraction
        self.original_method = Extraction.get_script_path
        self.cli = Mock()
        magic = types.ModuleType('librelane.steps.magic')
        magic.SpiceExtraction = Extraction
        entry = types.ModuleType('librelane.__main__')
        entry.cli = self.cli
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules, {'librelane.steps.magic': magic, 'librelane.__main__': entry}).start()
        patch.object(self.module.importlib.metadata, 'version', return_value='3.0.16').start()

    def test_fixed_variant_is_exactly_one_licensed_upstream_line_change_and_profile_is_bound(self):
        import hashlib
        self.assertEqual(len(self.original), 2993)
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), self.module.UPSTREAM_SCRIPT_SHA256)
        self.assertEqual(hashlib.sha256(self.variant).hexdigest(), self.module.FULL_SCRIPT_SHA256)
        self.assertEqual(self.original.count(b'\nextract\n'), 1)
        self.assertIn(b'Licensed under the Apache License, Version 2.0', self.variant)
        v1 = json.loads((ROOT / 'configs/lvs_profile_sky130.json').read_text())
        v2 = json.loads((ROOT / 'configs/lvs_profile_sky130_v2.json').read_text())
        for key in ('flow', 'jobs', 'config', 'deck_files'):
            self.assertEqual(v1[key], v2[key])
        self.assertIs(v2['force_full_extraction'], True)
        variant = v2['extraction_variant']
        self.assertEqual(variant['replacement'], {'from': 'extract', 'to': 'extract all', 'count': 1})
        self.assertEqual(variant['upstream_sha256'], self.module.UPSTREAM_SCRIPT_SHA256)
        self.assertEqual(variant['script_sha256'], self.module.FULL_SCRIPT_SHA256)
        self.assertEqual(variant['launcher_sha256'], hashlib.sha256((ROOT / variant['launcher_path']).read_bytes()).hexdigest())

    def test_only_extraction_script_path_is_overridden_and_real_cli_arguments_and_exit_are_preserved(self):
        arguments = ['--pdk', 'sky130A', '--run-tag', 'lvs', '/fixed/config.json']

        def cli(*, args):
            self.assertEqual(args, arguments)
            self.assertEqual(Path(self.extraction().get_script_path()), ROOT / 'scripts/extract_spice_full.tcl')
            raise SystemExit(3)

        self.cli.side_effect = cli
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as exit_result:
                self.module.main(arguments)
        self.assertEqual(exit_result.exception.code, 3)
        self.assertIs(self.extraction.get_script_path, self.original_method)
        self.assertIn('librelane.__main__.cli', output.getvalue())
        self.cli.assert_called_once_with(args=arguments)

    def test_mismatched_installed_upstream_script_is_rejected_before_cli(self):
        self.original_path.write_bytes(self.original + b'# changed\n')
        with self.assertRaisesRegex(RuntimeError, 'Installed upstream'):
            self.module.main([])
        self.cli.assert_not_called()
        self.assertIs(self.extraction.get_script_path, self.original_method)

    def test_mismatched_sibling_variant_or_package_version_is_rejected_before_cli(self):
        (self.directory / 'extract_spice_full.tcl').write_bytes(self.variant + b'# changed\n')
        with patch.object(self.module, '__file__', str(self.directory / 'run_full_lvs.py')):
            with self.assertRaisesRegex(RuntimeError, 'exact fixed one-line'):
                self.module.main([])
        with patch.object(self.module.importlib.metadata, 'version', return_value='3.0.17'):
            with self.assertRaisesRegex(RuntimeError, 'pinned LibreLane'):
                self.module.main([])
        self.cli.assert_not_called()
        self.assertIs(self.extraction.get_script_path, self.original_method)

    def test_preparer_defaults_to_full_retains_incremental_option_and_rejects_overwrite(self):
        physical = {'kind': 'wsl', 'release': physical_tools.RELEASE,
                    'appimage_sha256': physical_tools.IMAGE_SHA, 'pdk_revision': physical_tools.PDK_REVISION,
                    'base_sdc_sha256': physical_tools.SDC_SHA,
                    'profile': json.loads((ROOT / 'configs/physical_profile_sky130.json').read_text())}
        path = self.directory / 'isolated_physical_configuration.json'
        path.write_text(json.dumps(physical))

        def run(output, extra=()):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_lvs_runtime.py'),
                                   '--physical-config', str(path), '--output', str(output), *extra],
                                  capture_output=True, text=True, timeout=20, shell=False)

        full_output = self.directory / 'full'
        result = run(full_output)
        self.assertEqual(result.returncode, 0, result.stderr)
        full_path = full_output / 'lvs_runtime.json'
        before = full_path.read_bytes()
        value = json.loads(before)
        self.assertEqual(value['physical_runtime'], physical)
        self.assertEqual(value['profile']['profile_version'], 'hullcirq-sky130-lvs-v2')
        self.assertEqual(json.loads(result.stdout)['EDA_starts'], 0)
        self.assertEqual(run(full_output).returncode, 0)
        conflict = run(full_output, ('--profile', 'incremental'))
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn('No file overwritten', conflict.stderr)
        self.assertEqual(full_path.read_bytes(), before)
        incremental_output = self.directory / 'incremental'
        result = run(incremental_output, ('--profile', 'incremental'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((incremental_output / 'lvs_runtime.json').read_text())['profile']['profile_version'],
                         'hullcirq-sky130-lvs-v1')


if __name__ == '__main__':
    unittest.main()
