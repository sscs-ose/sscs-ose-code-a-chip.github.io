"""Pure-file recovery fixtures; these do not qualify a PDK or execute tools."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fresh_inventory_recovery_under_test', ROOT / 'scripts/fresh_runtime.py')
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)

V3_SCHEMA = 'hullcirq-fresh-host-runtime-v3'
PROFILE_PATHS = {'compiler': 'compiler.json', 'synthesizer': 'synthesizer.json',
                 'physical': 'p/physical_runtime-complete-v2.json',
                 'drc': 'd/drc_runtime-complete-v2.json',
                 'lvs': 'l/lvs_runtime-complete-v2.json'}
NEW_PATHS = ('p/pdk-input-manifest-complete-v2.json',
             'p/physical_runtime-complete-v2.json', 'd/drc_runtime-complete-v2.json',
             'l/lvs_runtime-complete-v2.json', 'ready-complete-v2.json')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class FreshInventoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.distribution = 'Ubuntu'
        self.folder = fresh.host_root(self.root, self.distribution)
        self.pdk = self.folder / 'p/pdks/vendor'
        if os.name != 'nt':
            # The production boundary accepts Windows paths. This pure-file
            # fixture supplies the same deterministic native path on POSIX.
            boundary = patch.object(fresh, 'wsl_path', side_effect=lambda path:
                                    '/mnt/fixture/' + Path(path).relative_to(self.root).as_posix())
            boundary.start()
            self.addCleanup(boundary.stop)
        self.fixture()

    def put(self, path, value):
        raw = value if isinstance(value, bytes) else fresh.raw_json(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def fixture(self, *, complete=False, schema='hullcirq-fresh-host-runtime-v2'):
        self.put(self.pdk / 'a', b'PDK fixture a')
        self.put(self.pdk / 'b', b'PDK fixture b is omitted only by old inventory')
        actual = fresh.inventory(self.pdk)
        self.old_manifest = {'pdk': 'sky130A', 'ciel_revision': fresh.PDK_REVISION,
                             'root': str(self.pdk), 'origin': 'isolated original fixture',
                             'files': actual if complete else {'a': actual['a']}}
        manifest_path = self.put(self.folder / 'p/pdk-input-manifest.json', self.old_manifest)
        self.physical = {'kind': 'wsl', 'distribution': self.distribution,
                         'appimage_sha256': fresh.IMAGE_SHA,
                         'appimage_path': str(self.folder / 'p/runtime/librelane-devshell-x86_64.AppImage'),
                         'pdk_revision': fresh.PDK_REVISION, 'pdk_root': str(self.folder / 'p/pdks'),
                         'pdk_manifest_path': str(manifest_path), 'pdk_manifest_sha256': fresh.sha(manifest_path),
                         'base_sdc_path': str(self.folder / 'p/official_base.sdc'),
                         'base_sdc_sha256': fresh.SDC_SHA,
                         'working_directory': str(self.folder / 'p/layout'),
                         'profile': {'fixture_only': 'original values must survive recovery'}}
        self.put(self.folder / 'p/physical_runtime.json', self.physical)
        for kind in ('drc', 'lvs'):
            self.put(self.folder / kind[0] / (kind + '_runtime.json'),
                     {'physical_runtime': self.physical, 'fixture_profile': kind})
        for kind, leaf in (('compiler', 'iverilog'), ('synthesizer', 'yosys')):
            self.put(self.folder / (kind + '.json'),
                     {'kind': 'wsl', 'distribution': self.distribution,
                      'executable': fresh.wsl_path(self.folder / leaf / 'usr/bin' / leaf),
                      'working_directory': str(self.folder / kind)})
        self.put(self.folder / 'local_runtime.json',
                 {'executable': str(self.folder / 'ollama/ollama.exe')})
        native_files = {name: {**record, 'mode': stat.S_IMODE((self.pdk / name).stat().st_mode)}
                        for name, record in actual.items()}
        native = {'schema': fresh.LINK_SCHEMA, 'mode': 'normalize',
                  'root': fresh.wsl_path(self.pdk), 'links': {}, 'directories': [],
                  'files': native_files}
        native_path = self.put(self.folder / 'p/linux-link-provenance.json', native)
        receipt = {'schema': fresh.LINK_SCHEMA, 'component': 'pdk',
                   'runtime_relative': self.pdk.relative_to(self.folder).as_posix(),
                   'sources': {'ciel_revision': fresh.PDK_REVISION, 'appimage_sha256': fresh.IMAGE_SHA},
                   'native_manifest': native_path.relative_to(self.folder).as_posix(),
                   'native_manifest_sha256': fresh.sha(native_path), 'links': {}}
        receipt_path = self.put(self.folder / 'normalizations/pdk-links-v1.json', receipt)
        self.state = {'schema': schema, 'checkout': str(self.root), 'distribution': self.distribution,
                      'runtime_root': self.folder.relative_to(self.root).as_posix(),
                      'prepared_at': '2026-10-29T00:00:00+00:00',
                      'model_inference_requests': 0, 'circuit_EDA_jobs': 0, 'design_store_writes': 0,
                      'system_installs': 0, 'network_sharing': False,
                      'linux_link_normalizations': {'pdk': receipt_path.relative_to(self.folder).as_posix()}}
        self.rebind_ready()

    def rebind_ready(self):
        self.state['files'] = {path.relative_to(self.root).as_posix():
                               {'sha256': fresh.sha(path), 'bytes': path.stat().st_size}
                               for path in self.folder.rglob('*')
                               if path.is_file() and path.name != 'ready.json'}
        self.put(self.folder / 'ready.json', self.state)

    def snapshot(self):
        return {path: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.root.rglob('*') if path.is_file()}

    def assert_originals_unchanged(self, before):
        for path, expected in before.items():
            with self.subTest(path=path.relative_to(self.root).as_posix()):
                self.assertTrue(path.is_file())
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), expected)

    def recover(self):
        with patch.object(fresh.subprocess, 'run', side_effect=AssertionError('Recovery must not execute native tools')):
            with patch.object(fresh, 'run', side_effect=AssertionError('Recovery must not execute commands')):
                with patch.object(fresh, 'build_opener', side_effect=AssertionError('Recovery must not access network')):
                    with patch.object(fresh, 'download', side_effect=AssertionError('Recovery must not download')):
                        return fresh.recover_pdk_inventory(self.root, self.distribution)

    def assert_rejected_without_publication(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.recover()
        self.assertEqual(self.snapshot(), before)
        for relative in NEW_PATHS:
            self.assertFalse((self.folder / relative).exists())

    def test_partial_inventory_recovers_from_exact_native_capture_without_changing_originals(self):
        before = self.snapshot()
        self.assertIs(self.recover(), True)
        self.assert_originals_unchanged(before)
        for relative in NEW_PATHS:
            self.assertTrue((self.folder / relative).is_file())
        complete_path = self.folder / NEW_PATHS[0]
        complete_manifest = fresh.load(complete_path)
        self.assertEqual(complete_manifest['root'], str(self.pdk))
        self.assertEqual(complete_manifest['ciel_revision'], fresh.PDK_REVISION)
        self.assertEqual(complete_manifest['files'], fresh.inventory(self.pdk))
        new_physical = fresh.load(self.folder / PROFILE_PATHS['physical'])
        self.assertEqual(new_physical['pdk_manifest_path'], str(complete_path))
        self.assertEqual(new_physical['pdk_manifest_sha256'], fresh.sha(complete_path))
        for key, value in self.physical.items():
            if key not in ('pdk_manifest_path', 'pdk_manifest_sha256'):
                self.assertEqual(new_physical[key], value)
        for kind in ('drc', 'lvs'):
            profile = fresh.load(self.folder / PROFILE_PATHS[kind])
            self.assertEqual(profile['physical_runtime'], new_physical)
            self.assertEqual(profile['fixture_profile'], kind)
        state = fresh.load(self.folder / 'ready-complete-v2.json')
        self.assertEqual(state['schema'], V3_SCHEMA)
        self.assertEqual(state['profile_paths'], PROFILE_PATHS)
        self.assertEqual(state['linux_link_normalizations'], self.state['linux_link_normalizations'])
        self.assertEqual(state['checkout'], str(self.root))
        self.assertEqual(state['distribution'], self.distribution)
        for name, record in self.state['files'].items():
            self.assertEqual(state['files'][name], record)
        for relative in NEW_PATHS[:-1]:
            path = self.folder / relative
            self.assertEqual(state['files'][path.relative_to(self.root).as_posix()],
                             {'sha256': fresh.sha(path), 'bytes': path.stat().st_size})

    def test_new_pdk_file_absent_from_original_native_capture_is_rejected(self):
        self.put(self.pdk / 'unrecorded-addition', b'not captured by original normalization')
        self.assert_rejected_without_publication()

    def test_changed_native_captured_pdk_file_is_rejected(self):
        self.put(self.pdk / 'b', b'tampered PDK fixture')
        self.assert_rejected_without_publication()

    def test_missing_native_captured_pdk_file_is_rejected(self):
        (self.pdk / 'b').unlink()
        self.assert_rejected_without_publication()

    def test_old_ready_pins_reject_tampered_metadata_before_new_outputs(self):
        for relative in ('p/physical_runtime.json', 'p/pdk-input-manifest.json',
                         'normalizations/pdk-links-v1.json', 'p/linux-link-provenance.json',
                         'd/drc_runtime.json', 'l/lvs_runtime.json'):
            with self.subTest(relative=relative):
                path = self.folder / relative
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                self.assert_rejected_without_publication()
                path.write_bytes(original)

    def test_native_capture_cannot_be_expanded_by_rebinding_only_old_ready_pin(self):
        self.put(self.pdk / 'unrecorded-addition', b'not in native normalization')
        self.rebind_ready()
        self.assert_rejected_without_publication()

    def test_native_source_pin_mismatch_is_rejected_even_with_matching_file_hashes(self):
        path = self.folder / 'normalizations/pdk-links-v1.json'
        receipt = fresh.load(path)
        receipt['sources']['ciel_revision'] = 'wrong-source-revision'
        self.put(path, receipt)
        self.rebind_ready()
        self.assert_rejected_without_publication()

    def test_native_root_binding_mismatch_is_rejected_even_with_rebound_metadata_pins(self):
        native_path = self.folder / 'p/linux-link-provenance.json'
        native = fresh.load(native_path)
        native['root'] = native['root'] + '-other-pdk'
        self.put(native_path, native)
        receipt_path = self.folder / 'normalizations/pdk-links-v1.json'
        receipt = fresh.load(receipt_path)
        receipt['native_manifest_sha256'] = fresh.sha(native_path)
        self.put(receipt_path, receipt)
        self.rebind_ready()
        self.assert_rejected_without_publication()

    def test_old_v1_ready_is_read_only_noop(self):
        self.fixture(schema='hullcirq-fresh-host-runtime-v1')
        before = self.snapshot()
        self.assertIs(self.recover(), False)
        self.assertEqual(self.snapshot(), before)

    def test_already_complete_old_pdk_inventory_is_read_only_noop(self):
        self.fixture(complete=True)
        before = self.snapshot()
        self.assertIs(self.recover(), False)
        self.assertEqual(self.snapshot(), before)

    def test_launch_arguments_use_exact_recovered_v3_profile_paths(self):
        self.assertIs(self.recover(), True)
        with patch.object(fresh.subprocess, 'run', side_effect=AssertionError('Argument construction must not launch')):
            arguments = fresh.launch_arguments(self.root, self.distribution, 8772)
        for kind, relative in PROFILE_PATHS.items():
            position = arguments.index('--' + kind + '-config')
            self.assertEqual(arguments[position + 1], str(self.folder / relative))
        self.assertNotIn(str(self.folder / 'p/physical_runtime.json'), arguments)
        self.assertNotIn(str(self.folder / 'd/drc_runtime.json'), arguments)
        self.assertNotIn(str(self.folder / 'l/lvs_runtime.json'), arguments)


if __name__ == '__main__':
    unittest.main()
