"""Retained-history duplication and guarded rollback; no model or EDA."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hullcirq.domain import DomainError
from hullcirq.physical_tools import artifact_files, io_path, read_bytes
from hullcirq.store import ProjectStore
from hullcirq.workspace import WorkspaceRegistry, remove_owned_tree


class DuplicateLongPathTests(unittest.TestCase):
    def setUp(self):
        qa=Path(__file__).resolve().parents[1]/'.work/qa'
        qa.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=qa)
        self.root=Path(self.temp.name)
        self.addCleanup(self.cleanup_long_tree,qa)
        self.registry=WorkspaceRegistry(self.root/'workspace')
        self.source=self.registry.create_project('Source','P1','counter_top')
        self.path=self.registry.resolve_system(self.source['project_id'],self.source['system_id'])['path']
        self.deep=self.path/'physical_recovery'/('retained_'+'x'*95)/'handoff.json'
        io_path(self.deep.parent).mkdir(parents=True)
        io_path(self.deep).write_bytes(b'{"original":"history"}\n')
        self.assertGreater(len(str(self.deep)),260)

    def cleanup_long_tree(self,qa):
        remove_owned_tree(self.root,qa)
        self.temp.cleanup()

    def inventory(self,path):
        return {p.relative_to(path).as_posix():(hashlib.sha256(read_bytes(p)).hexdigest(),io_path(p).stat().st_mtime_ns)
                for p in artifact_files(path,reject_links=True)}

    def test_duplicate_keeps_every_long_history_file_but_starts_without_results(self):
        before=self.inventory(self.path)
        cloned=self.registry.duplicate_project(self.source['project_id'],'Replay')
        folder=self.registry.resolve_system(cloned['project_id'],cloned['system_id'])['path']
        copied=folder/'provenance_snapshot'
        self.assertEqual({k:v[0] for k,v in before.items()},{k:v[0] for k,v in self.inventory(copied).items()})
        env=ProjectStore(folder).envelope()
        self.assertEqual(env['runs'],[])
        self.assertEqual(env['reviews'],[])
        self.assertEqual(env['review_policy']['mode'],'manual')
        self.assertTrue(all(s['execution_status']=='Not Run' for s in env['workflow']))
        self.assertEqual(before,self.inventory(self.path))

    def test_commit_failure_rolls_back_long_copy_and_preserves_source(self):
        before=self.inventory(self.path)
        catalog=self.registry.catalog()
        folders=set((self.registry.root/'projects').iterdir())
        with patch.object(self.registry,'_save',side_effect=OSError('simulated commit failure')):
            with self.assertRaises(OSError):self.registry.duplicate_project(self.source['project_id'])
        self.assertEqual(folders,set((self.registry.root/'projects').iterdir()))
        self.assertEqual(catalog,self.registry.catalog())
        self.assertEqual(before,self.inventory(self.path))

    def test_copy_rejects_reparse_inventory_before_creating_destination(self):
        # Simulate Windows reparse detection without requiring symlink privileges.
        original=__import__('os').scandir
        class Entry:
            def __init__(self,item):self.item=item;self.name=item.name
            def stat(self,**kwargs):
                value=self.item.stat(**kwargs)
                return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=0x400)
        class Scan:
            def __init__(self,path):self.scan=original(path)
            def __enter__(self):return self
            def __iter__(self):return (Entry(item) for item in self.scan)
            def __exit__(self,*args):self.scan.close()
        before=set((self.registry.root/'projects').iterdir())
        with patch('hullcirq.physical_tools.os.scandir',Scan):
            with self.assertRaises(DomainError) as caught:self.registry.duplicate_project(self.source['project_id'])
        self.assertEqual(caught.exception.code,'unsafe_system_file')
        self.assertEqual(before,set((self.registry.root/'projects').iterdir()))

    def test_cleanup_rejects_paths_outside_its_owned_root(self):
        keep=self.root/'keep';keep.mkdir();(keep/'original').write_bytes(b'keep')
        with self.assertRaises(DomainError) as caught:remove_owned_tree(keep,self.registry.root)
        self.assertEqual(caught.exception.code,'unsafe_project_cleanup')
        self.assertEqual((keep/'original').read_bytes(),b'keep')
