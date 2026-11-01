"""Read-only inspection safety and provenance, with isolated saved fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from hullcirq import inspection as view
from hullcirq.domain import DomainError
from hullcirq.verification import object_hash


class InspectionTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        temp=tempfile.TemporaryDirectory(dir=root/'.work/qa');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.patch=patch.object(view,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
        folder=self.root/'project';folder.mkdir();self.path=folder/'state.json';self.path.write_text('saved bytes',encoding='utf-8')
        self.plan={'kind':'generic_cycle_vectors','interface':{'ports':[]},'stimulus_timing':{},'public_boundary_vectors':[{'reset':1,'drive':{},'expect':{'out':9007199254740993}}]}
        self.run={'id':'original','stage_id':'local_netlist_simulation','execution_status':'Completed','validation_status':'Passed','checks':{'cycle_runtime':{'records':[{'cycle':0,'signal':'out','value':9007199254740993}]}},'verification_plan':self.plan}
        self.seal();self.manager=NS(lock=threading.RLock(),_state={'runs':[self.run],'reviews':[]})
        store={'revision':{'id':'r2','created_at':'2026-01-02T00:00:00+00:00'},'snapshots':{'r1':{'nodes':[]},'r2':{'nodes':[{'id':'a'}]}}}
        self.server=NS(workspace=NS(context=True,identity={'project_id':'project','system_id':'system','session_id':'session'}),store=NS(lock=threading.RLock(),_state=store,state_path=self.path))
        for n in set(view.GROUPS.values())|{'generation','global_generation','implementation_specs'}:setattr(self.server,n,self.manager)

    def seal(self): self.run['record_hash']=object_hash({k:v for k,v in self.run.items() if k!='record_hash'})

    def test_wave_observed_and_expected_wide_values_remain_independent_strings(self):
        old=copy.deepcopy(self.run);r=view.waveform(self.server,'workflow','original')
        self.assertEqual(r['samples'][0]['value'],'9007199254740993');self.assertEqual(r['vectors'][0]['expect']['out'],'9007199254740993')
        self.assertIsNone(r['vcd']);self.assertEqual(self.run,old)

    def test_bad_record_stage_unknown_group_and_active_run_are_rejected(self):
        for group,identifier in [('outside','original'),('workflow','missing')]:
            with self.assertRaises(DomainError):view.waveform(self.server,group,identifier)
        self.run['execution_status']='Running';self.seal()
        with self.assertRaises(DomainError):view.waveform(self.server,'workflow','original')

    def test_catalog_and_preview_preserve_all_saved_bytes_mtime_and_state(self):
        before=self.path.read_bytes(),self.path.stat().st_mtime_ns,copy.deepcopy(self.server.store._state)
        data,_=view.catalog(self.server);entry=next(e for e in data['entries'] if e['category']=='Specifications and expectations')
        preview=view.file_content(self.server,entry['id']);self.assertIn('nodes',preview['text'])
        self.assertTrue(any(e['category']=='Design changes' for e in data['entries']))
        self.assertEqual((self.path.read_bytes(),self.path.stat().st_mtime_ns,self.server.store._state),before)

    def test_file_id_is_opaque_and_outside_path_and_traversal_are_rejected(self):
        with self.assertRaises(DomainError):view.file_content(self.server,'../../outside')
        with self.assertRaises(DomainError):view.safe_file(self.root.parent/'outside')
        with self.assertRaises(DomainError):view.verified_artifact({'checks':{'artifacts_directory':str(self.root)}},{'relative_path':'../outside'})

    def test_artifact_hash_change_fails_closed(self):
        p=self.root/'simulation.vcd';p.write_bytes(b'original')
        run={'checks':{'artifacts_directory':str(self.root)}};a={'relative_path':'simulation.vcd','bytes':8,'sha256':hashlib.sha256(b'original').hexdigest()}
        self.assertEqual(view.verified_artifact(run,a),b'original');p.write_bytes(b'modified')
        with self.assertRaises(DomainError):view.verified_artifact(run,a)

    def test_unknown_historical_time_and_actor_are_not_invented(self):
        data,_=view.catalog(self.server);old=next(e for e in data['events'] if e['record_id']=='r1')
        self.assertIsNone(old['time']);self.assertEqual(old['actor'],'Not recorded')

    def test_all_explicit_managed_stores_and_recovery_files_are_listed(self):
        for name in ('generation_batches.json', 'repair_analysis.json'):
            (self.path.parent/name).write_text('{}', encoding='utf-8')
        recovery=self.path.parent/'physical_recovery';recovery.mkdir();(recovery/'handoff.json').write_text('{}', encoding='utf-8')
        data,_=view.catalog(self.server);names={e['name'] for e in data['entries']}
        self.assertTrue({'generation_batches.json','repair_analysis.json','handoff.json'}<=names)

    def test_refresh_adds_generated_sources_without_requiring_checks_or_writes(self):
        generation=NS(lock=threading.RLock(),_state={'jobs':[], 'reviews':[]})
        self.server.generation=generation
        before=self.path.read_bytes(),self.path.stat().st_mtime_ns
        first,_=view.catalog(self.server)
        self.assertFalse(any(e['name']=='rtl · generated-node' for e in first['entries']))
        generation._state['jobs'].append({'id':'generated-node','revision_id':'r2','node_id':'counter',
            'execution_status':'Completed','validation_status':'Passed','review_status':'Awaiting Review',
            'finished_at':'2026-01-02T02:03:04+00:00','rtl':'module counter; endmodule',
            'raw_content':'```verilog\nmodule counter; endmodule\n```','context':{'instruction':'original saved request'},'checks':{}})
        saved=copy.deepcopy(generation._state)
        refreshed,_=view.catalog(self.server)
        rtl=next(e for e in refreshed['entries'] if e['name']=='rtl · generated-node')
        self.assertEqual((rtl['stage_id'],rtl['node_id'],rtl['source_revision']),('local_rtl_generation','counter','r2'))
        self.assertIn('#generated-node/rtl',rtl['location'])
        self.assertEqual(view.file_content(self.server,rtl['id'])['text'],'module counter; endmodule')
        model=next(e for e in refreshed['entries'] if e['name']=='raw_content · generated-node')
        self.assertEqual(view.file_content(self.server,model['id'])['text'],generation._state['jobs'][0]['raw_content'])
        self.assertEqual(generation._state,saved)
        self.assertEqual((self.path.read_bytes(),self.path.stat().st_mtime_ns),before)

    def test_generated_s07_specification_has_its_own_selectable_payload(self):
        specification={'ports':[{'name':'out','width':4}],'expected':[0,15,0]}
        record={'id':'spec-counter','stage_id':'node_implementation_specs','revision_id':'r2','node_id':'counter',
                'specification':specification,'checks':{},'execution_status':'Completed'}
        self.server.implementation_specs=NS(lock=threading.RLock(),_state={'specs':[record],'reviews':[]})
        data,_=view.catalog(self.server)
        entry=next(e for e in data['entries'] if e['name']=='specification · spec-counter')
        self.assertEqual(entry['stage_id'],'node_implementation_specs')
        self.assertEqual(entry['category'],'Specifications and expectations')
        self.assertEqual(json.loads(view.file_content(self.server,entry['id'])['text']),specification)

    def test_generated_waveform_file_is_listed_and_pinned_to_its_source_stage(self):
        raw=b'$timescale 1ps $end\n#0\n';p=self.path.parent/'simulation.vcd';p.write_bytes(raw)
        self.run['checks'].update(artifacts_directory=str(p.parent),artifacts=[{'id':'simulation-waveform',
            'relative_path':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}])
        self.seal();data,_=view.catalog(self.server)
        entry=next(e for e in data['entries'] if e['name']=='simulation-waveform')
        self.assertEqual((entry['stage_id'],entry['run_id']),('local_netlist_simulation','original'))
        self.assertEqual(view.file_content(self.server,entry['id'])['text'],raw.decode())
        p.write_bytes(raw+b'changed')
        with self.assertRaises(DomainError):view.file_content(self.server,entry['id'])

    def test_zero_diagnostic_input_validation_is_selectable(self):
        self.server.store._state['runs']=[{'id':'input-check','stage_id':'global_settings','revision_id':'r2',
                                        'diagnostics':[],'validation_status':'Passed'}]
        data,_=view.catalog(self.server)
        entry=next(e for e in data['entries'] if e['name']=='Input validation · input-check')
        self.assertEqual(entry['stage_id'],'global_settings')
        self.assertEqual(json.loads(view.file_content(self.server,entry['id'])['text'])['diagnostics'],[])

    def test_safe_png_preview_and_explicit_binary_metadata(self):
        import base64
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        for label,raw in [('png',png),('gds',b'\x00\x06\x00\x02\x02X')]:
            p=self.path.parent/('layout.'+label);p.write_bytes(raw)
            self.run['checks'].update(artifacts_directory=str(p.parent),artifacts=[{'id':label,
                'relative_path':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}])
            self.seal();data,_=view.catalog(self.server)
            entry=next(e for e in data['entries'] if e['name']==label and e['stage_id']=='local_netlist_simulation')
            result=view.file_content(self.server,entry['id'])
            if label=='png':
                self.assertEqual((result['kind'],result['mime_type']),('image','image/png'))
                self.assertEqual(base64.b64decode(result['data_base64']),raw)
            else:
                self.assertEqual(result['kind'],'binary')
                self.assertNotIn('text',result)
                self.assertEqual(result['sha256'],hashlib.sha256(raw).hexdigest())

    def test_prepared_profiles_are_directly_selectable_and_isolated_to_current_system(self):
        from hullcirq.workspace_server import _postlayout_profile_directory
        registry=self.root/'workspace';registry.mkdir();self.server.workspace.registry=NS(root=registry)
        active=_postlayout_profile_directory(registry,'project','system');active.mkdir(parents=True)
        other=_postlayout_profile_directory(registry,'project','other-system');other.mkdir(parents=True)
        payload={'schema':'saved-prepare','source_run_id':'original','created_at':'2026-01-02T01:00:00+00:00'}
        paths=[]
        for name in ('lvs_repair_direct_runtime_v7.json','postlayout_runtime.json','physical_repair_runtime_v3.json'):
            path=active/name;path.write_text(json.dumps(payload),encoding='utf-8');paths.append(path)
        (active/'unmanaged-secret.json').write_text('not indexed',encoding='utf-8')
        (other/'lvs_repair_runtime_v3.json').write_text('other system',encoding='utf-8')
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
        data,_=view.catalog(self.server);entries=[e for e in data['entries'] if e['category']=='Prepared runtime profiles']
        self.assertEqual({e['name'] for e in entries},{p.name for p in paths})
        for entry in entries:
            result=view.file_content(self.server,entry['id'])
            self.assertEqual(json.loads(result['text']),payload)
            self.assertIn(active.name,entry['location'])
            self.assertIn('actor is not inferred',entry['action'])
        self.assertEqual({p:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths},before)
        self.server.workspace.identity['system_id']='other-system'
        with self.assertRaises(DomainError):view.file_content(self.server,entries[0]['id'])
        changed,_=view.catalog(self.server)
        self.assertEqual([e['name'] for e in changed['entries'] if e['category']=='Prepared runtime profiles'],['lvs_repair_runtime_v3.json'])

    def large_text_file(self):
        # Force three/four-byte code points across nominal 64 KiB boundaries.
        text=('a'*(view.TEXT_PAGE_BYTES-2)+'あ😀Z')*33+'最後'
        path=self.path.parent/'lvs_workflow.json';raw=text.encode('utf-8');path.write_bytes(raw)
        data,_=view.catalog(self.server)
        entry=next(e for e in data['entries'] if e['name']=='lvs_workflow.json' and e['category']=='Project stores')
        return path,text,raw,entry

    def test_large_utf8_pages_cover_every_codepoint_once_without_writes(self):
        path,text,raw,entry=self.large_text_file();before=path.read_bytes(),path.stat().st_mtime_ns
        first=view.file_content(self.server,entry['id']);pages=[first]
        self.assertEqual(first['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(first['pagination']['start_byte'],0)
        for page in range(1,first['pagination']['page_count']):
            pages.append(view.file_content(self.server,entry['id'],page=page,sha256=first['sha256']))
        self.assertEqual(''.join(p['text'] for p in pages),text)
        self.assertEqual(pages[-1]['pagination']['end_byte'],len(raw))
        self.assertTrue(all(p['sha256']==first['sha256'] and p['verified'] for p in pages))
        self.assertTrue(all(p['pagination']['end_byte']-p['pagination']['start_byte']<=view.TEXT_PAGE_BYTES+3 for p in pages))
        self.assertTrue(all(a['pagination']['end_byte']==b['pagination']['start_byte'] for a,b in zip(pages,pages[1:])))
        self.assertEqual((path.read_bytes(),path.stat().st_mtime_ns),before)

    def test_large_pages_reject_version_changes_missing_hash_and_invalid_pages(self):
        path,_,raw,entry=self.large_text_file();first=view.file_content(self.server,entry['id']);sha=first['sha256']
        for kwargs in ({'page':1},{'page':-1},{'page':True},{'page':'1'},
                       {'page':first['pagination']['page_count'],'sha256':sha},{'sha256':'bad'},
                       {'page':1,'sha256':'0'*64}):
            with self.assertRaises(DomainError):view.file_content(self.server,entry['id'],**kwargs)
        path.write_bytes(raw[:-1]+b'X')
        with self.assertRaises(DomainError):view.file_content(self.server,entry['id'],page=1,sha256=sha)
        with self.assertRaises(DomainError):view.file_content(self.server,entry['id'],page=0,sha256=sha)

    def test_large_page_limits_binary_and_changed_system_remain_explicit(self):
        path,_,raw,entry=self.large_text_file();first=view.file_content(self.server,entry['id'])
        with patch.object(view,'MAX_PAGED_TEXT',len(raw)-1):
            limited=view.file_content(self.server,entry['id'])
        self.assertEqual((limited['kind'],limited['verified'],limited['sha256']),('binary',False,None))
        self.assertNotIn('text',limited)
        path.write_bytes(raw+b'\x00')
        binary=view.file_content(self.server,entry['id'])
        self.assertEqual((binary['kind'],binary['verified']),('binary',True))
        self.assertNotIn('pagination',binary)
        other=self.root/'other-system';other.mkdir();(other/'state.json').write_text('{}',encoding='utf-8')
        self.server.store.state_path=other/'state.json';self.server.workspace.identity['system_id']='other'
        with self.assertRaises(DomainError):view.file_content(self.server,entry['id'],page=1,sha256=first['sha256'])
