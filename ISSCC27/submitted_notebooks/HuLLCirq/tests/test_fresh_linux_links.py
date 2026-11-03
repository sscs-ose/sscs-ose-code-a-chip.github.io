"""Isolated Linux-link fixtures; these are not native runtime evidence."""
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fresh_linux_links_under_test', ROOT / 'scripts/fresh_linux_links.py')
links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(links)


class FreshLinuxLinksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.allowed = Path(self.temp.name).resolve()
        self.stage = self.allowed / 'runtime.extract.fixture'
        self.stage.mkdir()
        self.manifest = self.allowed / 'runtime-links.json'

    def put(self, name, raw=b'fixture bytes\x00\xff\n'):
        path = self.stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def link(self, name, target, *, directory=False):
        path = self.stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            if os.name == 'nt':
                self.skipTest('Windows fixture cannot create symlinks: ' + str(error))
            raise
        return path

    def normalize(self, **kwargs):
        return links.normalize_tree(self.stage, self.manifest, allowed_root=self.allowed, **kwargs)

    def audit(self):
        return links.audit_tree(self.stage, self.manifest, allowed_root=self.allowed)

    def assert_rejected_unchanged(self):
        with patch.object(links.os, 'replace', side_effect=AssertionError('Mutation before validation')):
            with self.assertRaises((ValueError, OSError)):
                self.normalize()
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.manifest.with_name(self.manifest.name + '.before.json').exists())

    def test_regular_files_and_empty_directories_are_in_inventory(self):
        self.put('data/file', b'plain')
        (self.stage / 'empty').mkdir()
        result = self.normalize()
        self.assertEqual(result['schema'], links.SCHEMA)
        self.assertEqual(result['links'], {})
        self.assertEqual(result['files']['data/file']['sha256'], hashlib.sha256(b'plain').hexdigest())
        self.assertEqual(result['files']['data/file']['bytes'], 5)
        self.assertEqual(result['directories'], ['data', 'empty'])
        self.assertEqual(json.loads(self.manifest.read_bytes()), result)

    def test_internal_relative_chain_flattens_to_identical_regular_files(self):
        target = self.put('lib/real.so')
        self.link('lib/middle.so', 'real.so')
        self.link('bin/public.so', '../lib/middle.so')
        original = target.read_bytes()
        result = self.normalize()
        self.assertEqual(result['links']['bin/public.so']['original_target'], '../lib/middle.so')
        self.assertEqual(result['links']['bin/public.so']['resolved_target'], 'lib/real.so')
        for name in ('lib/middle.so', 'bin/public.so', 'lib/real.so'):
            path = self.stage / name
            self.assertFalse(path.is_symlink())
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(result['files'][name]['sha256'], hashlib.sha256(original).hexdigest())

    def test_chain_is_preserved_when_intermediate_link_is_replaced_first(self):
        self.put('real')
        self.link('a-intermediate', 'real')
        self.link('z-outer', 'a-intermediate')
        result = self.normalize()
        self.assertFalse((self.stage / 'z-outer').is_symlink())
        self.assertEqual((self.stage / 'z-outer').read_bytes(), (self.stage / 'real').read_bytes())
        self.assertEqual(result['links']['z-outer']['resolved_target'], 'real')

    def test_successful_normalization_keeps_identical_before_and_final_receipts(self):
        self.put('real')
        self.link('alias', 'real')
        self.normalize()
        before_manifest = self.manifest.with_name(self.manifest.name + '.before.json')
        self.assertEqual(before_manifest.read_bytes(), self.manifest.read_bytes())
        self.assertEqual(json.loads(before_manifest.read_bytes())['links']['alias']['original_target'], 'real')

    def test_interrupted_replacement_retains_all_original_links_in_before_receipt_only(self):
        self.put('real', b'original')
        self.link('a-first', 'real')
        self.link('b-second', 'a-first')
        original_replace = links.os.replace
        def interrupted(source, target):
            if Path(target).name == 'b-second':
                raise OSError('fixture interruption after first link replacement')
            return original_replace(source, target)
        with patch.object(links.os, 'replace', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.normalize()
        before_manifest = self.manifest.with_name(self.manifest.name + '.before.json')
        before = json.loads(before_manifest.read_bytes())
        self.assertEqual(before['links']['a-first']['original_target'], 'real')
        self.assertEqual(before['links']['b-second']['original_target'], 'a-first')
        self.assertEqual(before['links']['b-second']['resolved_target'], 'real')
        self.assertEqual(before['files']['b-second']['sha256'], hashlib.sha256(b'original').hexdigest())
        self.assertFalse(self.manifest.exists())
        self.assertFalse((self.stage / 'a-first').is_symlink())
        self.assertTrue((self.stage / 'b-second').is_symlink())

    def test_conflicting_before_receipt_rejects_before_link_replacement(self):
        self.put('real')
        alias = self.link('alias', 'real')
        before_manifest = self.manifest.with_name(self.manifest.name + '.before.json')
        before_manifest.write_bytes(b'previous original receipt')
        with patch.object(links.os, 'replace', side_effect=AssertionError('Mutation before receipt conflict check')):
            with self.assertRaises(ValueError):
                self.normalize()
        self.assertEqual(before_manifest.read_bytes(), b'previous original receipt')
        self.assertFalse(self.manifest.exists())
        self.assertTrue(alias.is_symlink())

    @unittest.skipIf(os.name == 'nt', 'POSIX permission preservation needs Linux')
    def test_preserves_final_target_executable_mode(self):
        target = self.put('lib/tool')
        target.chmod(0o751)
        # DrvFS without metadata can report 0777 after chmod(0751). Verify
        # preservation of the mode the actual filesystem exposes to Python.
        observed_mode = stat.S_IMODE(target.stat().st_mode)
        self.link('bin/tool', '../lib/tool')
        result = self.normalize()
        self.assertEqual(stat.S_IMODE((self.stage / 'bin/tool').stat().st_mode), observed_mode)
        self.assertEqual(result['links']['bin/tool']['mode'], observed_mode)
        self.assertEqual(result['files']['lib/tool']['mode'], observed_mode)

    def test_audit_preserves_every_original_file_link_and_mtime(self):
        target = self.put('real')
        alias = self.link('alias', 'real')
        before = {path.name: (path.lstat().st_mtime_ns, path.lstat().st_mode)
                  for path in self.stage.iterdir()}
        result = self.audit()
        self.assertEqual(result['mode'], 'audit')
        self.assertTrue(alias.is_symlink())
        self.assertEqual(os.readlink(alias), 'real')
        self.assertEqual(target.read_bytes(), b'fixture bytes\x00\xff\n')
        self.assertEqual(before, {path.name: (path.lstat().st_mtime_ns, path.lstat().st_mode)
                                 for path in self.stage.iterdir()})
        self.assertFalse(self.manifest.with_name(self.manifest.name + '.before.json').exists())

    def test_quarantine_preserve_records_broken_external_and_cyclic_literal_links_without_target_opens(self):
        regular = self.put('regular', b'original regular bytes')
        external = self.allowed / 'external-target'
        external.write_bytes(b'outside bytes must not be opened')
        targets = {'broken': 'missing-file', 'external': str(external),
                   'escape': '../external-target', 'first-cycle': 'second-cycle',
                   'second-cycle': 'first-cycle'}
        for name, target in targets.items():
            self.link(name, target)
        before = {path.name: (path.lstat().st_mtime_ns, path.lstat().st_mode,
                              os.readlink(path) if path.is_symlink() else path.read_bytes())
                  for path in self.stage.iterdir()}
        original_file_record = links._file_record
        opened_regular_files = []
        def only_regular(path, *args, **kwargs):
            self.assertEqual(path, regular, 'Preservation opened a symlink target')
            opened_regular_files.append(path)
            return original_file_record(path, *args, **kwargs)
        with patch.object(links, '_resolve_file', side_effect=AssertionError('Preservation resolved a link')):
            with patch.object(links, '_file_record', side_effect=only_regular):
                result = links.preserve_tree(self.stage, self.manifest, allowed_root=self.allowed)
        self.assertTrue(opened_regular_files)
        self.assertEqual(result['mode'], 'preserve')
        self.assertEqual(set(result['files']), {'regular'})
        self.assertEqual(set(result['links']), set(targets))
        for name, target in targets.items():
            record = result['links'][name]
            self.assertEqual(record['original_target'], target)
            self.assertEqual(record['link_text_sha256'], hashlib.sha256(os.fsencode(target)).hexdigest())
            self.assertEqual(record['link_text_bytes'], len(os.fsencode(target)))
            self.assertNotIn('resolved_target', record)
            self.assertNotIn('sha256', record)
        self.assertEqual(before, {path.name: (path.lstat().st_mtime_ns, path.lstat().st_mode,
                                            os.readlink(path) if path.is_symlink() else path.read_bytes())
                                 for path in self.stage.iterdir()})
        self.assertFalse(self.manifest.with_name(self.manifest.name + '.before.json').exists())

    def test_preserve_receipt_does_not_qualify_broken_link_for_audit_or_normalize(self):
        self.link('broken', 'missing')
        links.preserve_tree(self.stage, self.manifest, allowed_root=self.allowed)
        original_manifest = self.manifest.read_bytes()
        for operation in (links.audit_tree, links.normalize_tree):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(ValueError):
                    operation(self.stage, self.allowed / (operation.__name__ + '.json'), allowed_root=self.allowed)
        self.assertEqual(self.manifest.read_bytes(), original_manifest)
        self.assertTrue((self.stage / 'broken').is_symlink())

    def test_preserve_detects_literal_link_change_before_manifest_write(self):
        alias = self.link('broken', 'original-missing')
        original_inspect = links._inspect_preserved
        calls = []
        def changed(root):
            result = original_inspect(root)
            calls.append(root)
            if len(calls) == 1:
                alias.unlink()
                alias.symlink_to('different-missing')
            return result
        with patch.object(links, '_inspect_preserved', side_effect=changed):
            with self.assertRaises(ValueError):
                links.preserve_tree(self.stage, self.manifest, allowed_root=self.allowed)
        self.assertFalse(self.manifest.exists())

    def test_preserve_keeps_operation_path_and_manifest_containment_guards(self):
        self.put('regular')
        for root, manifest in ((self.allowed, self.manifest),
                               (self.stage, self.stage / 'receipt.json'),
                               (self.stage, self.allowed.parent / 'outside-receipt.json')):
            with self.subTest(root=root, manifest=manifest):
                with self.assertRaises(ValueError):
                    links.preserve_tree(root, manifest, allowed_root=self.allowed)
        self.assertFalse(self.manifest.exists())

    def test_all_links_are_validated_before_first_write(self):
        self.put('real')
        good = self.link('a-good', 'real')
        self.link('z-bad', 'missing')
        self.assert_rejected_unchanged()
        self.assertTrue(good.is_symlink())

    def test_absolute_target_is_rejected_even_inside_tree(self):
        target = self.put('real')
        self.link('alias', str(target))
        self.assert_rejected_unchanged()

    def test_external_relative_target_is_rejected(self):
        (self.allowed / 'outside').write_bytes(b'outside')
        self.link('alias', '../outside')
        self.assert_rejected_unchanged()

    def test_escape_then_reenter_is_rejected(self):
        self.put('real')
        self.link('alias', '../' + self.stage.name + '/real')
        self.assert_rejected_unchanged()

    def test_chain_escape_then_reenter_is_rejected(self):
        self.put('real')
        self.link('first', 'second')
        self.link('second', '../' + self.stage.name + '/real')
        self.assert_rejected_unchanged()

    def test_cyclic_links_are_rejected(self):
        self.link('first', 'second')
        self.link('second', 'first')
        self.assert_rejected_unchanged()

    def test_broken_link_is_rejected(self):
        self.link('alias', 'missing')
        self.assert_rejected_unchanged()

    def test_directory_link_is_rejected_without_walking_its_target(self):
        self.put('directory/real')
        self.link('alias', 'directory', directory=True)
        self.assert_rejected_unchanged()

    def test_link_through_directory_link_is_rejected(self):
        self.put('directory/real')
        self.link('diralias', 'directory', directory=True)
        self.link('alias', 'diralias/real')
        self.assert_rejected_unchanged()

    def test_file_target_with_trailing_slash_is_rejected(self):
        self.put('real')
        self.link('alias', 'real/')
        self.assert_rejected_unchanged()

    def test_backslash_and_colon_targets_are_rejected(self):
        for target in ('..\\outside', 'C:/outside', 'name:stream'):
            with self.subTest(target=target):
                alias = self.link('alias', target)
                self.assert_rejected_unchanged()
                alias.unlink()

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO fixture requires POSIX')
    def test_special_file_guard_uses_real_fifo_or_explicit_mock_on_unsupported_filesystem(self):
        self.put('real')
        good = self.link('a-good', 'real')
        fifo_path = self.stage / 'pipe'
        def reject_special():
            self.assert_rejected_unchanged()
            with self.assertRaises(ValueError):
                links.preserve_tree(self.stage, self.manifest, allowed_root=self.allowed)
            self.assertFalse(self.manifest.exists())
        try:
            os.mkfifo(fifo_path)
        except OSError as error:
            if error.errno not in (errno.ENOTSUP, errno.EOPNOTSUPP):
                raise
            # WSL DrvFS can refuse FIFO creation. Exercise the same special
            # lstat branch with an explicit mocked FIFO, without opening it.
            self.put('pipe', b'mocked-FIFO-placeholder-on-unsupported-filesystem')
            original_lstat = links.Path.lstat
            def fifo_lstat(path, *args, **kwargs):
                info = original_lstat(path, *args, **kwargs)
                if path == fifo_path:
                    fields = list(info)
                    fields[0] = stat.S_IFIFO | 0o600
                    return os.stat_result(fields)
                return info
            with patch.object(links.Path, 'lstat', fifo_lstat):
                reject_special()
        else:
            reject_special()
        self.assertTrue(good.is_symlink())

    def test_stage_itself_cannot_be_a_link(self):
        self.put('real')
        alias = self.allowed / 'stage-alias'
        try:
            alias.symlink_to(self.stage, target_is_directory=True)
        except OSError as error:
            if os.name == 'nt':
                self.skipTest(str(error))
            raise
        with self.assertRaises(ValueError):
            links.normalize_tree(alias, self.manifest, allowed_root=self.allowed)

    def test_symlink_ancestor_is_rejected(self):
        self.put('real')
        alias = self.link('unused', 'real')
        alias.unlink()
        parent_alias = self.allowed / 'parent-alias'
        parent_alias.symlink_to(self.allowed, target_is_directory=True)
        with self.assertRaises(ValueError):
            links.normalize_tree(parent_alias / self.stage.name, self.manifest, allowed_root=self.allowed)

    def test_stage_must_be_strict_allowed_root_descendant(self):
        for stage in (self.allowed, self.allowed.parent):
            with self.subTest(stage=stage):
                with self.assertRaises(ValueError):
                    links.normalize_tree(stage, self.manifest, allowed_root=self.allowed)

    def test_allowed_root_cannot_be_filesystem_root(self):
        with self.assertRaises(ValueError):
            links.normalize_tree(self.stage, self.manifest, allowed_root=Path(self.allowed.anchor))

    def test_manifest_must_be_outside_stage_and_inside_allowed_root(self):
        self.put('real')
        for manifest in (self.stage / 'manifest.json', self.allowed.parent / 'outside.json'):
            with self.subTest(manifest=manifest):
                with self.assertRaises(ValueError):
                    links.normalize_tree(self.stage, manifest, allowed_root=self.allowed)
        self.assertEqual([path.name for path in self.stage.iterdir()], ['real'])

    def test_manifest_symlink_and_symlink_parent_are_rejected(self):
        self.put('real')
        self.link('probe', 'real')
        self.manifest.symlink_to(self.stage / 'real')
        with self.assertRaises(ValueError):
            self.normalize()
        self.manifest.unlink()
        parent_alias = self.allowed / 'manifest-parent'
        parent_alias.symlink_to(self.allowed, target_is_directory=True)
        with self.assertRaises(ValueError):
            links.normalize_tree(self.stage, parent_alias / 'record.json', allowed_root=self.allowed)

    def test_manifest_conflict_is_checked_before_mutating_links(self):
        self.put('real')
        good = self.link('alias', 'real')
        self.manifest.write_bytes(b'previous record')
        with patch.object(links.os, 'replace', side_effect=AssertionError('Mutation before conflict check')):
            with self.assertRaises(ValueError):
                self.normalize()
        self.assertEqual(self.manifest.read_bytes(), b'previous record')
        self.assertTrue(good.is_symlink())

    def test_identical_audit_manifest_is_reused_without_overwrite(self):
        self.put('real')
        self.link('alias', 'real')
        self.audit()
        before = (self.manifest.read_bytes(), self.manifest.stat().st_mtime_ns)
        with patch.object(links, '_publish_manifest', side_effect=AssertionError('Record rewritten')):
            self.audit()
        self.assertEqual(before, (self.manifest.read_bytes(), self.manifest.stat().st_mtime_ns))

    def test_tamper_is_rejected_against_retained_audit_manifest(self):
        self.put('real', b'original')
        self.link('alias', 'real')
        self.audit()
        original = self.manifest.read_bytes()
        (self.stage / 'real').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            self.audit()
        self.assertEqual(self.manifest.read_bytes(), original)

    def test_before_after_logical_file_hashes_are_identical(self):
        self.put('real')
        self.link('alias', 'real')
        audited = self.audit()
        self.manifest = self.allowed / 'normalized-links.json'
        normalized = self.normalize()
        self.assertEqual(audited['files'], normalized['files'])
        after, _ = links._inspect(self.stage)
        self.assertEqual(links._content_files(audited['files']), links._content_files(after['files']))
        self.assertEqual(after['links'], {})

    def test_target_change_after_validation_does_not_publish_manifest(self):
        self.put('real', b'original')
        good = self.link('alias', 'real')
        original_inspect = links._inspect
        calls = []
        def changed(root):
            result = original_inspect(root)
            calls.append(root)
            if len(calls) == 1:
                (self.stage / 'real').write_bytes(b'tampered')
            return result
        with patch.object(links, '_inspect', side_effect=changed):
            with self.assertRaises(ValueError):
                self.normalize()
        self.assertTrue(good.is_symlink())
        self.assertFalse(self.manifest.exists())

    def test_atomic_manifest_creation_does_not_overwrite_a_late_conflict(self):
        self.put('real')
        original = links.os.link
        def conflict(source, target):
            if Path(target) == self.manifest:
                Path(target).write_bytes(b'concurrent record')
            return original(source, target)
        with patch.object(links.os, 'link', side_effect=conflict):
            with self.assertRaises(ValueError):
                self.normalize()
        self.assertEqual(self.manifest.read_bytes(), b'concurrent record')
        self.assertTrue(self.stage.is_dir())

    def test_cli_prints_json_summary_and_requires_allowed_root(self):
        self.put('real')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = links.main(['normalize', str(self.stage), str(self.manifest), '--allowed-root', str(self.allowed)])
        self.assertEqual(code, 0)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(summary['link_count'], 0)
        self.assertEqual(summary['manifest_sha256'], hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                links.main(['audit', str(self.stage), str(self.manifest)])

    def test_cli_preserve_records_broken_link_as_literal_metadata(self):
        self.link('broken', 'missing')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = links.main(['preserve', str(self.stage), str(self.manifest), '--allowed-root', str(self.allowed)])
        self.assertEqual(code, 0)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary['mode'], 'preserve')
        self.assertEqual(summary['file_count'], 0)
        self.assertEqual(summary['link_count'], 1)
        self.assertEqual(json.loads(self.manifest.read_bytes())['links']['broken']['original_target'], 'missing')


if __name__ == '__main__':
    unittest.main()
