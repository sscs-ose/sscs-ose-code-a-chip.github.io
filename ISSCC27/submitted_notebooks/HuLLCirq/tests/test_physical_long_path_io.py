"""Real long-path integrity fixtures; no circuit or external command execution."""
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from hullcirq import physical_tools as physical, drc_tools as drc, lvs_tools as lvs
from hullcirq.domain import DomainError


class PhysicalLongPathIoTests(unittest.TestCase):
    def setUp(self):
        qa=ROOT/'.work/io6';qa.mkdir(parents=True,exist_ok=True)
        self.root=Path(tempfile.mkdtemp(dir=qa)).absolute()
        def cleanup():
            if not self.root.is_relative_to(qa.absolute()):raise AssertionError('Unsafe fixture cleanup')
            shutil.rmtree(physical.io_path(self.root))
        self.addCleanup(cleanup)
        self.relative='/'.join(['long_component_0123456789abcdef']*6)+ '/proof.json'
        self.file=self.root/self.relative
        physical.io_path(self.file.parent).mkdir(parents=True)
        self.raw=b'{"proof":"long path retained"}\n'
        physical.io_path(self.file).write_bytes(self.raw)
        self.metadata={'bytes':len(self.raw),'sha256':hashlib.sha256(self.raw).hexdigest()}

    def test_real_long_file_integrity_preserves_all_bytes(self):
        self.assertGreater(len(str(self.file)),300)
        self.assertEqual(physical.verify_pdk_file(self.root,self.relative,self.metadata),self.file)
        self.assertEqual(physical.file_stat(self.file).st_size,len(self.raw))
        self.assertEqual(physical.read_bytes(self.file),self.raw)
        self.assertEqual(physical.load(self.file),{'proof':'long path retained'})

    def test_wrong_hash_still_fails(self):
        with self.assertRaises(DomainError) as caught:
            physical.verify_pdk_file(self.root,self.relative,{**self.metadata,'sha256':'0'*64})
        self.assertEqual(caught.exception.code,'physical_pdk_conflict')

    def test_missing_is_not_reported_as_changed_bytes(self):
        with self.assertRaises(DomainError) as caught:
            physical.verify_pdk_file(self.root,'missing.json',self.metadata)
        self.assertEqual(caught.exception.code,'physical_pdk_conflict_missing')

    def test_unreadable_is_not_reported_as_changed_bytes(self):
        with patch.object(physical,'sha',side_effect=PermissionError('fixture denied')):
            with self.assertRaises(DomainError) as caught:
                physical.verify_pdk_file(self.root,self.relative,self.metadata)
        self.assertEqual(caught.exception.code,'physical_pdk_conflict_unreadable')

    def test_traversal_and_alias_rejected_without_opening_target(self):
        with self.assertRaises(DomainError):physical.verify_pdk_file(self.root,'../outside',self.metadata)
        real_lstat=physical.os.lstat
        def reparse_info(path):
            info=real_lstat(path)
            class Info:
                st_mode=info.st_mode;st_size=info.st_size;st_file_attributes=0x400
            return Info()
        with patch.object(physical.os,'lstat',side_effect=reparse_info),patch.object(physical,'sha') as digest:
            with self.assertRaises(DomainError) as caught:physical.verify_pdk_file(self.root,self.relative,self.metadata)
            self.assertEqual(caught.exception.code,'physical_pdk_conflict_link')
            digest.assert_not_called()

    def test_complete_artifact_iterator_and_drc_collection_include_long_file(self):
        self.assertEqual(list(physical.artifact_files(self.root)),[self.file])
        result={'artifacts_directory':str(self.root)}
        drc._retain(result)
        self.assertEqual(result['retained_files'][0]['relative_path'],self.relative)
        self.assertEqual(result['retained_files'][0]['sha256'],self.metadata['sha256'])

    def test_lvs_collection_includes_long_file(self):
        result={'artifacts_directory':str(self.root)}
        lvs._retain(result,{'settings':{'top_module':'fixture_top'}})
        self.assertTrue(any(item['relative_path']==self.relative for item in result['retained_files']))

    def test_missing_unstarted_flow_directory_has_no_fabricated_artifacts(self):
        self.assertEqual(physical.artifact_glob(self.root/'not-started','*-klayout-render/state_out.json'),[])

    def test_shared_adapters_read_same_long_file_and_no_namespace_leaks(self):
        self.assertEqual(drc.sha(self.file),self.metadata['sha256'])
        self.assertEqual(lvs.read_bytes(self.file),self.raw)
        self.assertFalse(str(self.file).startswith('\\\\?\\'))
        self.assertEqual(drc._safe(self.root,self.relative),self.file)
        self.assertEqual(lvs._safe(self.root,self.relative),self.file)

    def test_frozen_linux_launcher_contains_no_windows_io_helpers(self):
        from hullcirq import postroute_tools
        import ast
        tree=ast.parse(postroute_tools.LAUNCHER.decode('utf-8'))
        names={node.id for node in ast.walk(tree) if isinstance(node,ast.Name)}
        self.assertFalse(names & {'read_bytes','file_stat','file_exists','artifact_files'})
        # Pre-I6 retained Linux launcher also matches this tracked HEAD literal.
        self.assertEqual(len(postroute_tools.LAUNCHER),2789)
        self.assertEqual(hashlib.sha256(postroute_tools.LAUNCHER).hexdigest(),
                         'fa059ff099a911acc7f21c53d54ac981209ae5bad1f4d03716598547e17cb13b')

    def test_root_ancestor_reparse_point_is_rejected_before_hash(self):
        real_lstat=physical.os.lstat; ancestor=self.root.parent
        def one_reparse(path):
            info=real_lstat(path)
            if Path(path)==physical.io_path(ancestor):
                class Info:
                    st_mode=info.st_mode;st_size=info.st_size;st_file_attributes=0x400
                return Info()
            return info
        with patch.object(physical.os,'lstat',side_effect=one_reparse),patch.object(physical,'sha') as digest:
            with self.assertRaises(DomainError) as caught:physical.verify_pdk_file(self.root,self.relative,self.metadata)
            self.assertEqual(caught.exception.code,'physical_pdk_conflict_link')
            digest.assert_not_called()

    def test_strict_inventory_rejects_directory_reparse_without_descent(self):
        from types import SimpleNamespace
        import stat
        class DirectoryLink:
            name='linked-directory'
            def stat(self,follow_symlinks=False):
                return SimpleNamespace(st_mode=stat.S_IFDIR|0o755,st_file_attributes=0x400)
            def is_file(self):return False
        class Entries(list):
            def __enter__(self):return self
            def __exit__(self,*args):return False
        def directory_entries(path):return Entries([DirectoryLink()])
        with patch.object(physical.os,'scandir',side_effect=directory_entries) as scan:
            with self.assertRaises(DomainError):list(physical.artifact_files(self.root,reject_links=True))
            self.assertEqual(scan.call_count,1)


if __name__=='__main__':unittest.main()
