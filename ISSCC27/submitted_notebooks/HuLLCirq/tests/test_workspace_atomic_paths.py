"""Real deep Unicode atomic-I/O fixtures; no model, tool run or live app."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from hullcirq import store as store_module, workspace
from hullcirq.domain import DomainError
from hullcirq.implementation_specs import ImplementationSpecManager
from hullcirq.physical_tools import artifact_files
from hullcirq.store import ProjectStore, _io_path
from hullcirq.workspace import WorkspaceRegistry, blank_design, new_state, write_json

ROOT = Path(__file__).resolve().parents[1]


class WorkspaceAtomicPathTests(unittest.TestCase):
    def setUp(self):
        self.qa = ROOT / '.work' / 'qa'
        self.qa.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='workspace-atomic-', dir=self.qa)
        self.root = Path(self.temporary.name)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.assertEqual(self.root.resolve().parent, self.qa.resolve())
        self.assertTrue(self.root.name.startswith('workspace-atomic-'))
        self.assertFalse(self.root.is_symlink())
        if _io_path(self.root).exists():
            list(artifact_files(self.root, reject_links=True))
            shutil.rmtree(_io_path(self.root))
        self.temporary.cleanup()

    def deep(self, filename='保存é.json'):
        folder = self.root
        while len(str(folder / filename)) < 330:
            folder /= '深い保存先é_' + 'x' * 27
        _io_path(folder).mkdir(parents=True, exist_ok=True)
        target = folder / filename
        self.assertGreaterEqual(len(str(target)), 330)
        return target

    def external_directory(self, length=198):
        # The managed system's .workspace-*.tmp exceeds262characters while
        # ordinary state.json stays within the original current-host boundary.
        stem = '保存先é_'
        width = length - len(str(self.root)) - 1
        self.assertGreaterEqual(width, len(stem))
        target = self.root / (stem + 'x' * (width - len(stem)))
        self.assertEqual(len(str(target)), length)
        return target

    def snapshot(self, path):
        if not _io_path(path).exists():
            return None
        raw = _io_path(path).read_bytes()
        return raw, _io_path(path).stat().st_mtime_ns

    def test_normal_json_bytes_and_fsync_stay_unchanged(self):
        target = self.root / 'normal.json'
        value = {'name': '保存é', 'values': [1, True, None]}
        expected = '{\n  "name": "保存é",\n  "values": [\n    1,\n    true,\n    null\n  ]\n}\n'.encode('utf-8')
        with patch.object(workspace.os, 'fsync', wraps=os.fsync) as sync:
            write_json(target, value)
        self.assertEqual(_io_path(target).read_bytes(), expected)
        self.assertEqual(sync.call_count, 1)
        self.assertEqual(list(_io_path(target.parent).glob('.workspace-*.tmp')), [])

    def test_deep_unicode_json_replaces_exact_destination_and_cleans_temp(self):
        target = self.deep()
        _io_path(target).write_bytes(b'old raw bytes\r\n')
        write_json(target, {'saved': '日本語é', 'clock_period_ns': 50})
        raw = _io_path(target).read_bytes()
        self.assertEqual(json.loads(raw), {'saved': '日本語é', 'clock_period_ns': 50})
        self.assertTrue(raw.endswith(b'\n'))
        self.assertNotIn(b'\r\n', raw)
        self.assertEqual(list(_io_path(target.parent).glob('.workspace-*.tmp')), [])

    def test_deep_workspace_fsync_failure_preserves_old_bytes_and_mtime(self):
        target = self.deep()
        _io_path(target).write_bytes(b'preserved-original\r\n')
        before = self.snapshot(target)
        with patch.object(workspace.os, 'fsync', side_effect=OSError('isolated fsync failure')):
            with self.assertRaises(OSError):
                write_json(target, {'replacement': True})
        self.assertEqual(self.snapshot(target), before)
        self.assertEqual(list(_io_path(target.parent).glob('.workspace-*.tmp')), [])

    def test_deep_workspace_replace_failure_preserves_old_bytes_and_mtime(self):
        target = self.deep()
        _io_path(target).write_bytes(b'preserved-original\r\n')
        before = self.snapshot(target)
        with patch.object(workspace.os, 'replace', side_effect=OSError('isolated replace failure')):
            with self.assertRaises(OSError):
                write_json(target, {'replacement': True})
        self.assertEqual(self.snapshot(target), before)
        self.assertEqual(list(_io_path(target.parent).glob('.workspace-*.tmp')), [])

    def test_invalid_json_never_replaces_old_deep_file(self):
        target = self.deep()
        _io_path(target).write_bytes(b'preserved-original\r\n')
        before = self.snapshot(target)
        with self.assertRaises(ValueError):
            write_json(target, {'bad': float('nan')})
        self.assertEqual(self.snapshot(target), before)
        self.assertEqual(list(_io_path(target.parent).glob('.workspace-*.tmp')), [])

    def test_deep_project_create_save_duplicate_and_restart_keep_logical_paths(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        external = self.external_directory()
        actual_temp_paths = []
        original = workspace.tempfile.mkstemp
        def observed(*args, **kwargs):
            result = original(*args, **kwargs)
            actual_temp_paths.append(str(result[1]).removeprefix('\\\\?\\'))
            return result
        with patch.object(workspace.tempfile, 'mkstemp', side_effect=observed):
            created = registry.create_project('Deep Unicode', 'Main', 'deep_top', project_directory=str(external))
            folder = registry._system_path(created['project_id'], created['system_id'])
            store = ProjectStore(folder)
            env = store.envelope()
            changed = copy.deepcopy(env['design'])
            changed['project']['name'] = 'Saved Unicode — 保存é'
            saved = store.save(changed, env['revision']['id'])
            before = self.snapshot(store.state_path)
            clone = registry.duplicate_system(created['project_id'], created['system_id'], 'Fresh input copy')
        self.assertTrue(any(len(p) >= 262 for p in actual_temp_paths))
        self.assertEqual(self.snapshot(store.state_path), before)
        clone_path = registry._system_path(clone['project_id'], clone['system_id'])
        copied = _io_path(clone_path / 'provenance_snapshot' / 'state.json').read_bytes()
        self.assertEqual(copied, before[0])
        clone_env = ProjectStore(clone_path).envelope()
        self.assertEqual(clone_env['runs'], [])
        self.assertEqual(clone_env['reviews'], [])
        self.assertEqual(clone_env['review_policy']['mode'], 'manual')
        self.assertEqual(clone_env['design']['settings']['clock_period_ns'], 50)
        reopened = WorkspaceRegistry(self.root / 'registry')
        resolved = reopened.resolve_system(created['project_id'], created['system_id'])
        self.assertEqual(resolved['path'], folder)
        self.assertNotIn('\\\\?\\', str(reopened._project(created['project_id'])['directory']))
        self.assertEqual(ProjectStore(folder).envelope()['revision']['id'], saved['revision']['id'])
        self.assertEqual(self.snapshot(store.state_path), before)

    def test_deep_store_and_s07_existing_constructor_reads_never_rewrite(self):
        path = self.deep('state.json')
        design = blank_design('project-' + 'a' * 32, 'Deep fixture', 'system-' + 'b' * 32, 'Main', 'deep_top')
        write_json(path, new_state(design))
        store = ProjectStore(path.parent)
        env = store.envelope()
        env['design']['project']['name'] = 'Saved only fixture label'
        store.save(env['design'], env['revision']['id'])
        generation = SimpleNamespace(envelope=lambda: {'generation': {'reviews': []}})
        workflow = SimpleNamespace(envelope=lambda: {'workflow_reviews': []})
        spec = ImplementationSpecManager(store, generation, workflow)
        spec._persist()
        before = {p.name: self.snapshot(p) for p in (store.state_path, spec.path)}
        opened = ProjectStore(path.parent)
        reopened_spec = ImplementationSpecManager(opened, generation, workflow)
        reopened_spec.envelope()
        self.assertEqual({p.name: self.snapshot(p) for p in (store.state_path, spec.path)}, before)
        self.assertEqual(opened.envelope()['design']['project']['name'], 'Saved only fixture label')

    def test_deep_store_fsync_failure_keeps_old_revision_and_file(self):
        path = self.deep('state.json')
        design = blank_design('project-' + 'a' * 32, 'Deep fixture', 'system-' + 'b' * 32, 'Main', 'deep_top')
        write_json(path, new_state(design))
        store = ProjectStore(path.parent)
        before = self.snapshot(path)
        env = store.envelope()
        changed = copy.deepcopy(env['design'])
        changed['project']['name'] = 'Must not commit'
        with patch.object(store_module.os, 'fsync', side_effect=OSError('isolated fsync failure')):
            with self.assertRaises(OSError):
                store.save(changed, env['revision']['id'])
        self.assertEqual(self.snapshot(path), before)
        self.assertEqual(store.envelope()['revision']['id'], env['revision']['id'])
        self.assertEqual(list(_io_path(path.parent).glob('.state-*.tmp')), [])

    def test_create_failure_removes_only_new_systems_and_keeps_empty_parent(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        external = self.external_directory()
        external.mkdir()
        before = self.snapshot(registry.registry_path)
        replace = workspace.os.replace
        def fail_state(source, destination):
            if Path(destination).name == 'state.json':
                raise OSError('isolated new-state commit failure')
            return replace(source, destination)
        with patch.object(workspace.os, 'replace', side_effect=fail_state):
            with self.assertRaises(OSError):
                registry.create_project('Must rollback', project_directory=str(external))
        self.assertTrue(external.is_dir())
        self.assertEqual(list(external.iterdir()), [])
        self.assertEqual(self.snapshot(registry.registry_path), before)
        self.assertEqual(registry.catalog()['projects'], [])

    def test_index_failure_restores_exact_prior_marker_bytes(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        created = registry.create_project('Original', project_directory=str(self.external_directory(330)))
        marker = registry._project_path(created['project_id']) / workspace.PROJECT_MANIFEST
        value = json.loads(_io_path(marker).read_bytes())
        original = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\r\n'
        _io_path(marker).write_bytes(original)
        index_before = self.snapshot(registry.registry_path)
        replace = workspace.os.replace
        def fail_index(source, destination):
            if _io_path(destination) == _io_path(registry.registry_path):
                raise OSError('isolated catalog commit failure')
            return replace(source, destination)
        with patch.object(workspace.os, 'replace', side_effect=fail_index):
            with self.assertRaises(OSError):
                registry.rename_project(created['project_id'], 'Must rollback')
        self.assertEqual(_io_path(marker).read_bytes(), original)
        self.assertEqual(self.snapshot(registry.registry_path), index_before)
        self.assertEqual(registry._project(created['project_id'])['name'], 'Original')

    def test_full_deep_project_marker_and_state_load_duplicate_without_rewrite(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        created = registry.create_project('Full deep Unicode', project_directory=str(self.external_directory(330)))
        folder = registry.resolve_system(created['project_id'], created['system_id'])['path']
        self.assertGreater(len(str(folder / 'state.json')), 370)
        before = self.snapshot(folder / 'state.json')
        clone = registry.duplicate_system(created['project_id'], created['system_id'], 'Fresh duplicate')
        self.assertEqual(self.snapshot(folder / 'state.json'), before)
        reopened = WorkspaceRegistry(self.root / 'registry')
        resolved = reopened.resolve_system(created['project_id'], created['system_id'])
        self.assertEqual(resolved['path'], folder)
        self.assertEqual(ProjectStore(folder).envelope()['design']['settings']['clock_period_ns'], 50)
        self.assertEqual(self.snapshot(folder / 'state.json'), before)
        clone_folder = reopened.resolve_system(clone['project_id'], clone['system_id'])['path']
        self.assertEqual(_io_path(clone_folder / 'provenance_snapshot' / 'state.json').read_bytes(), before[0])

    def test_deep_backup_and_restore_retain_exact_state_instead_of_empty_listing(self):
        import base64, gzip
        registry = WorkspaceRegistry(self.root / 'registry')
        created = registry.create_project('Deep backup', project_directory=str(self.external_directory(330)))
        folder = registry.resolve_system(created['project_id'], created['system_id'])['path']
        before = self.snapshot(folder / 'state.json')
        bundle = registry.backup_project(created['project_id'])
        states = [entry for entry in bundle['files'] if entry['path'].endswith('/state.json')]
        self.assertEqual(len(states), 1)
        self.assertEqual(gzip.decompress(base64.b64decode(states[0]['data'])), before[0])
        self.assertTrue(all(not entry['path'].startswith(('\\\\?\\', '/')) for entry in bundle['files']))
        restored = registry.restore_project(bundle)
        self.assertTrue(restored['system']['read_only'])
        restored_path = registry.resolve_system(restored['project_id'], restored['system_id'])['path']
        self.assertEqual(_io_path(restored_path / 'state.json').read_bytes(), before[0])
        self.assertEqual(self.snapshot(folder / 'state.json'), before)

    def test_deep_duplicate_commit_failure_removes_only_new_system(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        created = registry.create_project('Deep rollback', project_directory=str(self.external_directory(330)))
        root = registry._project_path(created['project_id'])
        folder = registry.resolve_system(created['project_id'], created['system_id'])['path']
        before = self.snapshot(folder / 'state.json')
        children = {p.name for p in _io_path(root / 'systems').iterdir()}
        with patch.object(registry, '_save', side_effect=OSError('isolated duplicate commit failure')):
            with self.assertRaises(OSError):
                registry.duplicate_system(created['project_id'], created['system_id'])
        self.assertEqual({p.name for p in _io_path(root / 'systems').iterdir()}, children)
        self.assertEqual(self.snapshot(folder / 'state.json'), before)

    def test_existing_empty_deep_folder_and_legacy_snapshot_do_not_lose_files(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        external = self.external_directory(330)
        _io_path(external).mkdir()
        created = registry.create_project('Existing empty deep folder', project_directory=str(external))
        folder = registry.resolve_system(created['project_id'], created['system_id'])['path']
        before = self.snapshot(folder / 'state.json')
        legacy = registry.register_legacy(folder, 'Deep legacy snapshot')
        self.assertTrue(legacy['system']['read_only'])
        copied = registry.resolve_system(legacy['project_id'], legacy['system_id'])['path']
        self.assertEqual(_io_path(copied / 'state.json').read_bytes(), before[0])
        self.assertEqual(self.snapshot(folder / 'state.json'), before)

    def test_existing_reparse_directory_guard_is_not_bypassed(self):
        registry = WorkspaceRegistry(self.root / 'registry')
        unsafe = self.root / 'simulated-reparse'
        unsafe.mkdir()
        original = Path.lstat
        def marked(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if path == unsafe:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        before = self.snapshot(registry.registry_path)
        with patch.object(Path, 'lstat', marked):
            with self.assertRaises(DomainError) as caught:
                registry.create_project('Reject unsafe', project_directory=str(unsafe))
        self.assertEqual(caught.exception.code, 'unsafe_project_directory')
        self.assertEqual(self.snapshot(registry.registry_path), before)
        self.assertEqual(list(unsafe.iterdir()), [])


if __name__ == '__main__':
    unittest.main()