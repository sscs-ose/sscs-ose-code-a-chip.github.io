"""Isolated installer QA; fixtures are never real native/model evidence."""
import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fresh_runtime_under_test', ROOT / 'scripts/fresh_runtime.py')
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class FreshRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def model_fixture(self):
        blobs = [b'config', b'weights-fixture-not-real', b'Apache License fixture']
        records = [{'sha256': digest(raw), 'bytes': len(raw)} for raw in blobs]
        manifest = fresh.raw_json({'config': {'digest': 'sha256:' + records[0]['sha256'], 'size': records[0]['bytes']},
                                  'layers': [{'digest': 'sha256:' + item['sha256'], 'size': item['bytes']} for item in records[1:]]})
        pin = {'schema': 'hullcirq-pinned-public-model-v1', 'manifest_sha256': digest(manifest),
               'manifest_bytes': len(manifest),
               'registry': fresh.REGISTRY, 'family': 'qwen2.5-coder', 'tag': '7b', 'license': 'Apache-2.0', 'blobs': records}
        self.put('configs/fresh_model_qwen25_coder.json', fresh.raw_json(pin))
        mapping = {fresh.REGISTRY + '/manifests/7b': manifest,
                   **{fresh.REGISTRY + '/blobs/sha256:' + digest(raw): raw for raw in blobs}}
        return manifest, mapping

    def test_fixed_public_pin_has_original_manifest_and_license(self):
        pin = fresh.model_pin(ROOT)
        self.assertEqual(sum(item['bytes'] for item in pin['blobs']), 4683087561)
        self.assertEqual(pin['license_layer_sha256'], pin['blobs'][-1]['sha256'])

    def test_host_binding_changes_after_move_or_distribution_change(self):
        self.assertNotEqual(fresh.host_root(self.root, 'Ubuntu'), fresh.host_root(self.root / 'moved', 'Ubuntu'))
        self.assertNotEqual(fresh.host_root(self.root, 'Ubuntu'), fresh.host_root(self.root, 'Ubuntu-24.04'))

    def test_distribution_cannot_inject_a_path(self):
        for name in ('../x', 'Ubuntu;bad', 'Ubuntu\nnew', '', '-d'):
            with self.assertRaises(ValueError):
                fresh.host_root(self.root, name)

    def test_work_child_rejects_non_runtime_targets(self):
        for path in (self.root, self.root / 'project.json', self.root.parent / 'outside'):
            with self.assertRaises(ValueError):
                fresh.work_child(self.root, path)

    def test_missing_download_without_permission_is_read_only(self):
        with self.assertRaises(ValueError):
            fresh.download('https://example.org/pin', self.root / 'missing/a', digest(b'a'))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_download_requires_https(self):
        with self.assertRaises(ValueError):
            fresh.download('http://example.org/pin', self.root / 'a', digest(b'a'), allowed=True)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_download_atomic_and_existing_not_redownloaded(self):
        target = self.root / 'a'
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return io.BytesIO(b'abc')
        fresh.download('https://example.org/a', target, digest(b'abc'), 3, allowed=True, opener=opener)
        fresh.download('https://example.org/a', target, digest(b'abc'), 3, allowed=True, opener=opener)
        self.assertEqual(len(calls), 1)
        self.assertEqual(target.read_bytes(), b'abc')
        self.assertEqual(list(self.root.iterdir()), [target])

    def test_conflict_is_preserved(self):
        target = self.put('a', b'old')
        with self.assertRaises(ValueError):
            fresh.download('https://example.org/a', target, digest(b'new'), allowed=True)
        self.assertEqual(target.read_bytes(), b'old')

    def test_bad_hash_retains_partial_without_final_name(self):
        with self.assertRaises(ValueError):
            fresh.download('https://example.org/a', self.root / 'a', digest(b'ok'), 3,
                           allowed=True, opener=lambda *args, **kwargs: io.BytesIO(b'bad'))
        self.assertFalse((self.root / 'a').exists())
        self.assertEqual(len(list(self.root.glob('a.download.*'))), 1)

    def test_interrupted_transfer_can_retry_as_new_partial(self):
        class Interrupted(io.BytesIO):
            def read(self, count=-1):
                raise OSError('fixture interruption')
        with self.assertRaises(OSError):
            fresh.download('https://example.org/a', self.root / 'a', digest(b'ok'), 2,
                           allowed=True, opener=lambda *args, **kwargs: Interrupted(b''))
        self.assertFalse((self.root / 'a').exists())
        fresh.download('https://example.org/a', self.root / 'a', digest(b'ok'), 2,
                       allowed=True, opener=lambda *args, **kwargs: io.BytesIO(b'ok'))
        self.assertEqual((self.root / 'a').read_bytes(), b'ok')
        self.assertEqual(len(list(self.root.glob('a.download.*'))), 1)

    def test_model_download_requires_explicit_license(self):
        manifest, mapping = self.model_fixture()
        with patch.object(fresh, 'MODEL_MANIFEST_SHA', digest(manifest)):
            with self.assertRaises(ValueError):
                fresh.prepare_model(self.root, allowed=True)
        self.assertFalse((self.root / '.work').exists())

    def test_model_from_public_registry_no_cache_or_daemon(self):
        manifest, mapping = self.model_fixture()
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return io.BytesIO(mapping[request.full_url])
        with patch.object(fresh, 'MODEL_MANIFEST_SHA', digest(manifest)), patch.object(fresh.subprocess, 'run', side_effect=AssertionError('No process permitted')):
            target = fresh.prepare_model(self.root, allowed=True, accept_license=True, opener=opener)
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
            fresh.prepare_model(self.root, allowed=False, opener=lambda *args, **kwargs: self.fail('Network during verification'))
            after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(len(calls), 4)
        self.assertTrue((target / 'manifests/registry.ollama.ai/library/qwen2.5-coder/7b').is_file())

    def test_moved_tag_rejected_before_any_blob_request(self):
        manifest, mapping = self.model_fixture()
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return io.BytesIO(b'moved')
        with patch.object(fresh, 'MODEL_MANIFEST_SHA', digest(manifest)):
            with self.assertRaises(ValueError):
                fresh.prepare_model(self.root, allowed=True, accept_license=True, opener=opener)
        self.assertEqual(calls, [fresh.REGISTRY + '/manifests/7b'])
        self.assertFalse((self.root / '.work/m2/ollama-models').exists())

    def test_incomplete_model_is_not_published(self):
        manifest, mapping = self.model_fixture()
        mapping[fresh.REGISTRY + '/blobs/sha256:' + digest(b'weights-fixture-not-real')] = b'corrupt'
        with patch.object(fresh, 'MODEL_MANIFEST_SHA', digest(manifest)):
            with self.assertRaises(ValueError):
                fresh.prepare_model(self.root, allowed=True, accept_license=True,
                                    opener=lambda request, timeout: io.BytesIO(mapping[request.full_url]))
        self.assertFalse((self.root / '.work/m2/ollama-models/manifests/registry.ollama.ai/library/qwen2.5-coder/7b').exists())

    def test_zip_path_traversal_preserved_not_extracted(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('../outside', 'no')
        with self.assertRaises(ValueError):
            fresh.extract_zip(archive, self.root / 'runtime')
        self.assertFalse((self.root / 'outside').exists())
        self.assertFalse((self.root / 'runtime').exists())

    def test_inventory_rejects_tamper_and_extra_file(self):
        target = self.root / 'runtime'
        self.put('runtime/a', b'a')
        records = fresh.inventory(target)
        self.put('runtime/extra', b'x')
        with self.assertRaises(ValueError):
            fresh.check_inventory(target, records)
        (target / 'a').write_bytes(b'b')
        with self.assertRaises(ValueError):
            fresh.check_inventory(target, records)

    def test_windows_linux_reparse_is_rejected_without_following(self):
        info = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
        with patch.object(fresh.os, 'lstat', return_value=info):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                fresh.plain_info(self.root / 'alias')

    def test_plain_child_checks_alias_before_resolve(self):
        self.put('runtime/alias', b'normal fixture')
        original = fresh.plain_info
        def inspect(path):
            if Path(path).name == 'alias':
                raise ValueError('link reintroduced')
            return original(path)
        with patch.object(fresh, 'plain_info', side_effect=inspect), patch.object(fresh, 'sha', side_effect=AssertionError('Alias must be rejected before reading')):
            with self.assertRaisesRegex(ValueError, 'link reintroduced'):
                fresh.check_inventory(self.root / 'runtime', {'alias': {'sha256': digest(b'normal fixture'), 'bytes': 14}})

    def test_native_normalization_provenance_checks_sources_and_contents(self):
        folder = self.root / 'runtime'
        alias = self.put('runtime/yosys/lib/alias', b'library')
        record = {'sha256': digest(b'library'), 'bytes': 7, 'mode': 0o755,
                  'original_target': 'real', 'resolved_target': 'lib/real'}
        native = self.put('runtime/normalizations/native.json', fresh.raw_json({'schema': fresh.LINK_SCHEMA, 'mode': 'normalize', 'links': {'lib/alias': record}}))
        receipt = {'schema': fresh.LINK_SCHEMA, 'component': 'yosys', 'runtime_relative': 'yosys',
                   'sources': [{'sha256': 'pinned-source-fixture'}], 'native_manifest': 'normalizations/native.json',
                   'native_manifest_sha256': fresh.sha(native), 'links': {'lib/alias': record}}
        receipt_path = self.put('runtime/normalizations/receipt.json', fresh.raw_json(receipt))
        with patch.object(fresh.subprocess, 'run', side_effect=AssertionError('Verification must not start native commands')):
            fresh.verify_normalization(folder, 'normalizations/receipt.json', 'yosys', receipt['sources'])
        alias.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            fresh.verify_normalization(folder, 'normalizations/receipt.json', 'yosys', receipt['sources'])
        alias.write_bytes(b'library')
        receipt['sources'] = []
        receipt_path.write_bytes(fresh.raw_json(receipt))
        with self.assertRaisesRegex(ValueError, 'provenance'):
            fresh.verify_normalization(folder, 'normalizations/receipt.json', 'yosys', [{'sha256': 'pinned-source-fixture'}])

    def test_incomplete_stage_is_preserved_outside_active_runtime(self):
        folder = self.root / '.work/fresh/host-binding'
        stage = folder / ('yosys.extract.' + 'a' * 32)
        original_file = self.put(stage.relative_to(self.root) / 'lib/original', b'preserve original')
        before = (original_file.read_bytes(), original_file.stat().st_mtime_ns)
        observed = []
        def audit(root, distribution, selected, manifest, operation):
            observed.append((selected, operation))
            return {'files': {'lib/original': {'sha256': digest(b'preserve original')}}, 'links': {}, 'directories': ['lib']}
        with patch.object(fresh, 'linux_link_operation', side_effect=audit):
            fresh.preserve_incomplete_stages(self.root, folder, 'Ubuntu')
        archived = self.root / '.work/fresh-failures/host-binding' / stage.name / 'lib/original'
        self.assertEqual((archived.read_bytes(), archived.stat().st_mtime_ns), before)
        self.assertFalse(stage.exists())
        self.assertEqual([operation for _, operation in observed], ['preserve', 'preserve'])
        fresh.contained_tree(folder)

    def test_silent_dependency_failure_names_command_and_exit_code(self):
        result = SimpleNamespace(returncode=1, stdout='', stderr='')
        with patch.object(fresh.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'exit 1.*test -r'):
                fresh.run(['test', '-r', 'fixture'], cwd=self.root)

    def test_fresh_yosys_dependency_uses_existing_abc_pin(self):
        packages = fresh.native_packages(ROOT)
        abc = next(item for item in packages if item.get('name') == 'yosys-abc')
        self.assertEqual(abc['sha256'], '916ba59b6ca6dd1b6b927c7364357c2801ccb85db7eb3ca858ac9a856270fa44')
        self.assertEqual(abc['bytes'], 5829332)
        self.assertTrue(abc['source'].endswith('/yosys-abc_0.33-5build2_amd64.deb'))

    def test_receipt_is_not_committed_before_stage_publication(self):
        folder = self.root / 'runtime'
        stage = folder / ('yosys.extract.' + 'b' * 32)
        self.put(stage.relative_to(self.root) / 'lib/file', b'fixture')
        def normalize(root, distribution, selected, manifest, operation):
            value = {'schema': fresh.LINK_SCHEMA, 'mode': operation, 'links': {}}
            fresh.write_exact(manifest, value)
            return value
        with patch.object(fresh, 'linux_link_operation', side_effect=normalize):
            relative, record = fresh.normalization_receipt(self.root, folder, 'Ubuntu', 'yosys', folder / 'yosys', stage, [], publish=False)
        self.assertFalse((folder / relative).exists())
        self.assertEqual(record['runtime_relative'], 'yosys')
        stage.rename(folder / 'yosys')
        fresh.write_exact(folder / relative, record)
        self.assertTrue((folder / relative).is_file())

    def test_uncommitted_component_is_archived_without_overwrite(self):
        folder = self.root / '.work/fresh/host-binding'
        target = self.put((folder / 'yosys/lib/file').relative_to(self.root), b'uncommitted')
        with patch.object(fresh, 'linux_link_operation', return_value={'files': {}, 'links': {}, 'directories': []}):
            fresh.preserve_incomplete_stages(self.root, folder, 'Ubuntu')
        archived = list((self.root / '.work/fresh-failures/host-binding').glob('yosys.uncommitted.*/lib/file'))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), b'uncommitted')
        self.assertFalse(target.exists())

    def test_long_path_inventory_and_hash_without_machine_setting(self):
        target = self.root / 'long-runtime'
        long_file = target / ('a' * 90) / ('b' * 90) / ('c' * 70) / 'library.data'
        self.assertGreater(len(str(long_file)), 300)
        try:
            os.makedirs(fresh.io_path(long_file.parent))
            with open(fresh.io_path(long_file), 'wb') as stream:
                stream.write(b'long-path fixture')
            records = fresh.inventory(target)
            fresh.check_inventory(target, records)
            self.assertEqual(fresh.sha(long_file), digest(b'long-path fixture'))
            self.assertEqual(len(records), 1)
        finally:
            # Only this explicitly checked, newly created fixture child is
            # removed; never the temporary root or any user runtime tree.
            self.assertEqual(target.parent, self.root)
            self.assertNotEqual(target, self.root)
            if os.path.isdir(fresh.io_path(target)):
                shutil.rmtree(fresh.io_path(target))

    def test_default_missing_verify_writes_nothing_and_starts_nothing(self):
        with patch.object(fresh.subprocess, 'run', side_effect=AssertionError('No process permitted')), patch.object(fresh, 'build_opener', side_effect=AssertionError('No network permitted')):
            with self.assertRaises(FileNotFoundError):
                fresh.verify(self.root, 'Ubuntu')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_full_verify_host_binding_and_positive_no_write_fixture(self):
        manifest, mapping = self.model_fixture()
        folder = fresh.host_root(self.root, 'Ubuntu')
        def put_absolute(path, raw):
            return self.put(path.relative_to(self.root), raw)
        with patch.object(fresh, 'MODEL_MANIFEST_SHA', digest(manifest)):
            fresh.prepare_model(self.root, allowed=True, accept_license=True,
                                opener=lambda request, timeout: io.BytesIO(mapping[request.full_url]))
        python_raw, image_raw, sdc_raw, ollama_raw = b'python archive fixture', b'image', b'sdc', b'ollama'
        self.put('.work/runtime/downloads/python-3.12.10-embed-amd64.zip', python_raw)
        put_absolute(folder / 'p/runtime/librelane-devshell-x86_64.AppImage', image_raw)
        put_absolute(folder / 'p/official_base.sdc', sdc_raw)
        put_absolute(folder / 'downloads/ollama-windows-amd64-v0.32.15.zip', ollama_raw)
        put_absolute(folder / 'ollama/ollama.exe', b'ollama fixture')
        put_absolute(folder / 'p/pdks/vendor/a', b'PDK fixture')
        pdk_manifest = {'root': str(folder / 'p/pdks/vendor'), 'ciel_revision': fresh.PDK_REVISION,
                        'files': fresh.inventory(folder / 'p/pdks/vendor')}
        put_absolute(folder / 'p/pdk-input-manifest.json', fresh.raw_json(pdk_manifest))
        physical = {'appimage_sha256': digest(image_raw), 'pdk_revision': fresh.PDK_REVISION,
                    'base_sdc_sha256': digest(sdc_raw), 'distribution': 'Ubuntu',
                    'appimage_path': str(folder / 'p/runtime/librelane-devshell-x86_64.AppImage'),
                    'working_directory': str(folder / 'p/layout'),
                    'pdk_manifest_path': str(folder / 'p/pdk-input-manifest.json')}
        put_absolute(folder / 'p/physical_runtime.json', fresh.raw_json(physical))
        for kind, leaf in (('compiler', 'iverilog'), ('synthesizer', 'yosys')):
            put_absolute(folder / (kind + '.json'), fresh.raw_json({'kind': 'wsl', 'distribution': 'Ubuntu',
                         'executable': fresh.wsl_path(folder / leaf / 'usr/bin' / leaf),
                         'working_directory': str(folder / kind)}))
        for kind in ('drc', 'lvs'):
            put_absolute(folder / kind[0] / (kind + '_runtime.json'), fresh.raw_json({'physical_runtime': physical}))
        put_absolute(folder / 'local_runtime.json', fresh.raw_json({'model_directory': str(self.root / '.work/m2/ollama-models'),
                     'endpoint': 'http://127.0.0.1:11435/v1', 'executable': str(folder / 'ollama/ollama.exe')}))
        files = {path.relative_to(self.root).as_posix(): {'sha256': fresh.sha(path), 'bytes': path.stat().st_size}
                 for path in self.root.rglob('*') if path.is_file()
                 and any(path.is_relative_to(parent) for parent in (folder, self.root / '.work/runtime', self.root / '.work/m2/ollama-models'))}
        state = {'schema': 'hullcirq-fresh-host-runtime-v1', 'checkout': str(self.root), 'distribution': 'Ubuntu',
                 'runtime_root': folder.relative_to(self.root).as_posix(), 'files': files}
        state_path = put_absolute(folder / 'ready.json', fresh.raw_json(state))
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.root.rglob('*') if path.is_file()}
        with patch.object(fresh, 'MODEL_MANIFEST_SHA', digest(manifest)), patch.object(fresh, 'PYTHON_SHA', digest(python_raw)), patch.object(fresh, 'IMAGE_SHA', digest(image_raw)), patch.object(fresh, 'IMAGE_BYTES', len(image_raw)), patch.object(fresh, 'SDC_SHA', digest(sdc_raw)), patch.object(fresh, 'OLLAMA_SHA', digest(ollama_raw)), patch.object(fresh.subprocess, 'run', side_effect=AssertionError('No process')), patch.object(fresh, 'build_opener', side_effect=AssertionError('No network')):
            self.assertEqual(fresh.verify(self.root, 'Ubuntu')['status'], 'Passed')
        after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before, after)
        state['checkout'] = str(self.root / 'old-host')
        state_path.write_bytes(fresh.raw_json(state))
        with self.assertRaisesRegex(ValueError, 'Host binding differs'):
            fresh.verify(self.root, 'Ubuntu')

    def test_launch_uses_isolated_registry_no_legacy_project_or_auto_job(self):
        folder = fresh.host_root(self.root, 'Ubuntu')
        self.put((folder / 'local_runtime.json').relative_to(self.root), fresh.raw_json({'executable': str(folder / 'ollama/ollama.exe')}))
        args = fresh.launch_arguments(self.root, 'Ubuntu', 8772)
        self.assertIn(str(folder / 'workspace'), args)
        self.assertNotIn('--legacy-data-dir', args)
        self.assertFalse(any('run-layout' in arg or 'generate' in arg or 'serve' == arg for arg in args))
        for kind in ('compiler', 'synthesizer', 'physical', 'drc', 'lvs'):
            self.assertIn('--' + kind + '-config', args)

    def test_launch_rejects_invalid_port(self):
        for port in (0, 65536, '8772', True):
            with self.assertRaises(ValueError):
                fresh.launch_arguments(self.root, 'Ubuntu', port)

    def test_powershell_plan_cannot_trigger_bootstrap(self):
        source = (ROOT / 'scripts/setup_fresh_runtime.ps1').read_text()
        self.assertLess(source.index('if ($Plan) {'), source.index("$freshPython ="))
        self.assertIn('default mode is strictly read-only', source)


if __name__ == '__main__':
    unittest.main()
