#!/usr/bin/env python3
"""Check real delivery records and reject an omitted log or unsafe path."""
import json
import gzip
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

import package_submission as packaging
from study_protocol import preregistration


def readiness_check():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);study=root/'results/configurable-study';study.mkdir(parents=True)
        plan=preregistration()
        records={'protocol.json':plan,
            'generation/analysis.json':{'complete':True,'rows':[{'job':job} for job in plan['generation']['jobs']]},
            'baseline/mhz95-run03/evaluation-v4.json':{'rank_eligible':True},
            'tutorial/summary.json':{'passed':True},'transfer/counter/results/result.json':{'passed':True},
            'ppa/analysis.json':{'complete':True,'rows':[{'id':job['id'],'finished':True,'physical_launches':3,'unused_slots':0} for job in plan['ppa']['sessions']]},
            'representatives/summary.json':{'finished':True,'selection':{'integrations':[{}]},'rows':[{}]},
            'high-frequency/summary.json':{'finished':True,'selection':{'choices':[{}]},'rows':[{}]},
            'export-manifest.json':{'complete':True}}
        for name,data in records.items():
            path=study/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data))
        notebook={'metadata':{'chipwave_submission':{'stage':'experiments_complete'}},
                  'cells':[{'cell_type':'code','execution_count':1,'outputs':[]}]}
        (root/'ChipWave.ipynb').write_text(json.dumps(notebook))
        with patch.object(packaging,'ROOT',root):
            packaging.validate_study()
            for name,key in (('ppa/analysis.json','complete'),('export-manifest.json','complete'),
                             ('representatives/summary.json','finished'),('high-frequency/summary.json','finished')):
                changed=dict(records[name]);changed[key]=False;(study/name).write_text(json.dumps(changed))
                try:packaging.validate_study()
                except ValueError:pass
                else:raise AssertionError('Incomplete campaign accepted: '+name)
                (study/name).write_text(json.dumps(records[name]))
            path=study/'ppa/analysis.json'
            for duplicate,launches,unused in ((True,3,0),(False,4,0),(False,2,0)):
                changed=json.loads(json.dumps(records['ppa/analysis.json']))
                if duplicate:changed['rows'].append(changed['rows'][0])
                changed['rows'][0].update(physical_launches=launches,unused_slots=unused)
                path.write_text(json.dumps(changed))
                try:packaging.validate_study()
                except ValueError:pass
                else:raise AssertionError('Invalid candidate/session counts accepted')
            path.write_text(json.dumps(records['ppa/analysis.json']))
            for execution_count,outputs in ((None,[]),(1,[{'output_type':'error'}])):
                notebook['cells'][0].update(execution_count=execution_count,outputs=outputs)
                (root/'ChipWave.ipynb').write_text(json.dumps(notebook))
                try:packaging.validate_study()
                except ValueError:pass
                else:raise AssertionError('Unexecuted or failing notebook accepted')
            notebook['cells'][0].update(execution_count=1,outputs=[])
            notebook['metadata']['chipwave_submission']['stage']='experiments_in_progress'
            (root/'ChipWave.ipynb').write_text(json.dumps(notebook))
            try:packaging.validate_study()
            except ValueError:pass
            else:raise AssertionError('Draft notebook accepted')
    print('PASS: complete frozen campaign required; incomplete searches/extensions/exports, duplicate sessions, invalid slots and draft/unexecuted/error notebooks rejected')


def self_check():
    candidates = packaging.files()
    packaging.validate_deliveries(candidates)
    log = packaging.ROOT/'results/physical-main/simulation/build/simulation.log'
    assert log in candidates
    try:
        packaging.validate_deliveries([p for p in candidates if p != log])
    except AssertionError as error:
        assert 'would be omitted' in str(error)
    else:
        raise AssertionError('Missing delivery log accepted')
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        delivery = root/'results/test'
        delivery.mkdir(parents=True)
        data = b'Collected physical evidence\n'
        compressed = delivery/'example.lvsdb.gz'
        with gzip.open(compressed, 'wb') as handle:
            handle.write(data)
        item = {'path': 'example.lvsdb', 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}
        record = delivery/'selected-delivery.json'
        record.write_text(json.dumps({'collected_files': [item]}))
        with patch.object(packaging, 'ROOT', root):
            packaging.validate_deliveries([compressed])
            item['sha256'] = '0'*64
            record.write_text(json.dumps({'collected_files': [item]}))
            try:
                packaging.validate_deliveries([compressed])
            except AssertionError:
                pass
            else:
                raise AssertionError('Incorrect decoded hash accepted')
        metadata = {'collected_files': [{'path': '../../outside', 'bytes': 0,
                                        'sha256': '0'*64}]}
        (delivery/'selected-delivery.json').write_text(json.dumps(metadata))
        with patch.object(packaging, 'ROOT', root):
            try:
                packaging.validate_deliveries([])
            except ValueError as error:
                assert 'Unsafe collected-file path' in str(error)
            else:
                raise AssertionError('Escaping delivery path accepted')
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);delivery=root/'results/ppa/candidate';delivery.mkdir(parents=True)
        evidence=delivery/'simulation.log';data=b'Collected nested experiment evidence\n';evidence.write_bytes(data)
        (delivery/'selected-delivery.json').write_text(json.dumps({'collected_files':[
            {'path':evidence.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}))
        with patch.object(packaging,'ROOT',root):
            packaging.validate_deliveries([evidence])
            try:packaging.validate_deliveries([])
            except AssertionError:pass
            else:raise AssertionError('Omitted nested PPA evidence accepted')
    readiness_check()
    print('PASS: delivery hashes, missing-log/unsafe-path rejection, gzip decoding/hash rejection, nested PPA delivery validation')


if __name__ == '__main__':
    self_check()
