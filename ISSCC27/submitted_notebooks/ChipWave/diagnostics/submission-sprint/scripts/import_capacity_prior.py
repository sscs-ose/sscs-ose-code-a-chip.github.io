"""Restore the authorized prior evidence and debit its ten attempts before new trials."""
import argparse
import collections
import json
import shutil
from pathlib import Path

from capacity_integration_physical import ROOT
from capacity_protocol import PHYSICAL_LIMITS
from restore_capacity_study import restore
from study_protocol import digest,write_json


def validate_inherited(root=ROOT):
    receipt=json.loads((root/'checks/inherited-attempts.json').read_text())
    ledger=json.loads((root/'physical-ledger.json').read_text())
    if receipt.get('passed') is not True or len(receipt['attempts'])!=10:
        raise ValueError('Ten inherited terminal attempts required')
    if ledger['limits']!=PHYSICAL_LIMITS or ledger['absolute_total']!=194 or ledger['attempts'][:10]!=receipt['attempts']:
        raise ValueError('Inherited physical costs changed or budget reset')
    counts=collections.Counter(row['category'] for row in receipt['attempts'])
    expected=dict(reference_module=4,reference_integration=4,preformal_calibration=1,retained_invalid_pilot=1)
    if counts!=expected or any(row['status']=='allocated' for row in receipt['attempts']):
        raise ValueError('Inherited allocation does not match approved revision')
    if any(digest(root/name)!=sha for name,sha in receipt['source_files'].items()):
        raise ValueError('Retained authorization/provenance changed')
    return receipt


def import_prior(source):
    source=Path(source).resolve()
    auth=json.loads((ROOT/'provenance/authorization.json').read_text())
    if auth.get('approved') is not True:raise ValueError('Explicit revised registration approval required')
    if (ROOT/'campaign-freeze.json').exists() or (ROOT/'checks/inherited-attempts.json').exists():
        raise ValueError('Prior import cannot replace a frozen or already imported study')
    ledger=json.loads((ROOT/'physical-ledger.json').read_text())
    if ledger['attempts'] or (ROOT/'physical').exists():raise ValueError('Expected an empty new physical allocation')
    raw=json.loads((ROOT/'provenance/original-physical-ledger.json').read_text())
    if len(raw['attempts'])!=10 or any(r['status']=='allocated' for r in raw['attempts']):
        raise ValueError('Original ten attempts must all be terminal')
    scratch=ROOT/'provenance/prior-restoration'
    restoration=restore(source,scratch)
    if (scratch/'physical-ledger.json').read_bytes()!=(ROOT/'provenance/original-physical-ledger.json').read_bytes():
        raise ValueError('Export differs from authorized terminal original ledger')
    (scratch/'physical').rename(ROOT/'physical')
    trial=scratch/'trials/pilot/pilot-luna-A1'
    rows=[]
    for old in raw['attempts']:
        row=dict(old)
        if old['category']=='pilot':
            if old['trial']!='pilot-luna-A1':raise ValueError('Unexpected prior design trial')
            physical=trial/'runtime/eda'/old['identity']
            physical.rename(ROOT/'physical'/old['identity'])
            row['category']='retained_invalid_pilot'
        target=ROOT/'physical'/old['identity']/Path(old['evidence']).name
        if not target.is_file():raise ValueError('Missing restored terminal evidence')
        row['evidence']=str(target)
        rows.append(row)
    trial.rename(ROOT/'provenance/retained-invalid-trial')
    for name in ('source-export-manifest.json','restoration.json'):
        shutil.copy2(scratch/name,ROOT/'provenance'/name)
    source_files={str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'provenance').glob('*.json')}
    receipt=dict(passed=True,attempts=rows,source_files=source_files,
        source_manifest_sha256=restoration['source_manifest_sha256'],
        model_calls=0,physical_runs=0,scope='Restored old references and one invalid pilot, charged once. No trial results supplied to new agents; reference audits and runtime qualification remain mandatory.')
    ledger['attempts']=rows
    write_json(ROOT/'physical-ledger.json',ledger)
    write_json(ROOT/'checks/inherited-attempts.json',receipt)
    validate_inherited()
    # Every remaining byte is represented in the verified original export; retain only used evidence here.
    shutil.rmtree(scratch)
    return dict(passed=True,inherited_attempts=10,remaining_physical_slots=184,new_physical_runs=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    print(json.dumps(import_prior(parser.parse_args().source)))
