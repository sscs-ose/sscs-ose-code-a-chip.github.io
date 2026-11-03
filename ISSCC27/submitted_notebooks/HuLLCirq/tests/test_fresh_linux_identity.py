"""Comparable platform timestamps with unchanged identity and mutation guards."""
from pathlib import Path
import importlib.util
import hashlib
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'src/hullcirq').is_dir())
SPEC=importlib.util.spec_from_file_location('fresh_identity_prototype',ROOT/'scripts/fresh_linux_links.py')
links=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(links)

def information(**fields):
    return SimpleNamespace(**dict(st_dev=1,st_ino=2,st_mode=33206,st_size=5,st_mtime_ns=100,
                                  st_ctime_ns=90,st_birthtime_ns=80,**fields))

class FreshIdentityTests(unittest.TestCase):
    def test_windows_creation_identity_is_comparable_despite_deprecated_ctime_mismatch(self):
        with patch.object(links,'os',SimpleNamespace(name='nt')):
            expected=information();opened=information();opened.st_ctime_ns=100
            self.assertEqual(links._identity(expected),links._identity(opened))
            for key in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_birthtime_ns'):
                changed=information();setattr(changed,key,getattr(changed,key)+1)
                self.assertNotEqual(links._identity(expected),links._identity(changed),key)

    def test_posix_change_time_remains_strict_even_when_creation_time_matches(self):
        with patch.object(links,'os',SimpleNamespace(name='posix')):
            expected=information();changed=information();changed.st_ctime_ns+=1
            self.assertNotEqual(links._identity(expected),links._identity(changed))

    def test_missing_windows_birthtime_keeps_original_strict_fallback(self):
        with patch.object(links,'os',SimpleNamespace(name='nt')):
            expected=information();changed=information();del expected.st_birthtime_ns;del changed.st_birthtime_ns
            changed.st_ctime_ns+=1
            self.assertNotEqual(links._identity(expected),links._identity(changed))

    def test_250_real_regular_file_inventories_keep_exact_bytes_and_required_entries(self):
        import test_fresh_linux_links as existing
        qa=ROOT/'.work/qa';qa.mkdir(parents=True,exist_ok=True)
        with patch.object(existing,'links',links),patch.object(tempfile,'tempdir',str(qa)):
            for index in range(250):
                with self.subTest(iteration=index):
                    case=existing.FreshLinuxLinksTests('test_regular_files_and_empty_directories_are_in_inventory')
                    case.setUp();self.assertTrue(case.allowed.resolve().is_relative_to(qa.resolve()))
                    try:case.test_regular_files_and_empty_directories_are_in_inventory()
                    finally:case.doCleanups()

    def _fixture(self):
        qa=ROOT/'.work/qa';qa.mkdir(parents=True,exist_ok=True)
        temporary=tempfile.TemporaryDirectory(dir=qa)
        self.assertTrue(Path(temporary.name).resolve().is_relative_to(qa.resolve()))
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def test_same_open_handle_ctime_change_is_still_rejected(self):
        path=self._fixture()/'file';path.write_bytes(b'plain');original=path.stat()
        fields=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        before=SimpleNamespace(**{key:getattr(original,key) for key in fields},st_birthtime_ns=getattr(original,'st_birthtime_ns',0))
        after=SimpleNamespace(**vars(before));after.st_ctime_ns+=1
        with patch.object(links.os,'fstat',side_effect=[before,after]):
            with self.assertRaisesRegex(ValueError,'changed while being read'):
                links._file_record(path)

    def test_replaced_path_or_link_target_descriptor_is_rejected_before_read(self):
        root=self._fixture();path=root/'file';path.write_bytes(b'plain');expected=path.lstat()
        other=root/'different-inode';other.write_bytes(b'plain')
        descriptor=os.open(other,os.O_RDONLY|getattr(os,'O_BINARY',0))
        with patch.object(links.os,'open',return_value=descriptor):
            with self.assertRaisesRegex(ValueError,'changed during validation'):
                links._file_record(path,expected)
        self.assertEqual(path.read_bytes(),b'plain')

    def test_real_content_change_during_read_is_rejected(self):
        path=self._fixture()/'file';path.write_bytes(b'plain');before=path.stat();digest=hashlib.sha256()
        class ChangingDigest:
            def update(self,block):
                digest.update(block);path.write_bytes(b'other')
                os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns+1_000_000_000))
            def hexdigest(self):return digest.hexdigest()
        with patch.object(links.hashlib,'sha256',return_value=ChangingDigest()):
            with self.assertRaisesRegex(ValueError,'changed while being read'):
                links._file_record(path)

    def test_path_replacement_between_complete_inventories_preserves_guard(self):
        root=self._fixture();stage=root/'stage';stage.mkdir();path=stage/'file';path.write_bytes(b'plain')
        manifest=root/'manifest.json';inspect=links._inspect;calls=[]
        def changed(folder):
            result=inspect(folder);calls.append(folder)
            if len(calls)==1:
                replacement=root/'replacement';replacement.write_bytes(b'other');os.replace(replacement,path)
            return result
        with patch.object(links,'_inspect',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'Stage changed during validation'):
                links.normalize_tree(stage,manifest,allowed_root=root)
        self.assertFalse(manifest.exists());self.assertEqual(path.read_bytes(),b'other')
