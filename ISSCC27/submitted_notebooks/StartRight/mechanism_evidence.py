"""Remeasure the included mechanism evidence, without executing SPICE.
SPDX-License-Identifier: Apache-2.0
"""
import ast
import hashlib
import json
from contextlib import nullcontext
import uuid
import zipfile
from mechanism_lab import HERE, score_prediction, paired_control
from check_mechanism_lab import checks
from sequence_evidence import normalize_deck
from sequence_circuits import generate_sequence


def audit():
    folder=HERE/'results/mechanism'
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    bundle=folder/'raw_evidence.zip'
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if sha(bundle.read_bytes())!=manifest['archive_sha256']:
        raise ValueError('Mechanism evidence archive differs')
    cache=HERE/'.cache';cache.mkdir(exist_ok=True)
    workspace=cache/('mechanism_'+uuid.uuid4().hex[:12]);workspace.mkdir()
    with nullcontext(workspace) as root:
        if not root.resolve().is_relative_to(cache.resolve()):raise ValueError('Temporary evidence path leaves cache')
        with zipfile.ZipFile(bundle) as z:
            if set(z.namelist())!=set(manifest['files']):raise ValueError('Unexpected evidence members')
            for name in z.namelist():
                if not (root/name).resolve().is_relative_to(root.resolve()):raise ValueError('Evidence path leaves archive')
                if sha(z.read(name))!=manifest['files'][name]:raise ValueError('Evidence member differs: '+name)
            z.extractall(root)
        plan=json.loads((root/'predictions_before_spice.json').read_text())
        # The plan belongs to the original saved experiment. Keep its source
        # identity, then allow only import/source-list cleanup in the two
        # refactored generators. Current helpers must reproduce every deck below.
        def body(source):
            tree=ast.parse(source)
            tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))
                       and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCES' for t in n.targets))]
            return ast.dump(tree,include_attributes=False)
        with zipfile.ZipFile(folder/'prediction_sources.zip') as sources:
            if set(sources.namelist())!=set(plan['source_hashes']):raise ValueError('Prediction source list differs')
            for name,digest in plan['source_hashes'].items():
                original=sources.read(name)
                if sha(original)!=digest:raise ValueError('Original prediction source differs: '+name)
                current=(HERE/name).read_bytes()
                if sha(current)!=digest:
                    if name not in ('reset_sequence.py','sequence_circuits.py') or body(current)!=body(original):
                        raise ValueError('Prediction logic differs: '+name)
        records={}
        for label in ('retained','commanded','dip_0p6','dip_1p2'):
            record=json.loads((root/label/'run.json').read_text())
            record['output_dir']=str(root/label)
            for row in record['cases']:
                text,_,_=generate_sequence(row['configuration'],record['scenario'],record['contract'],record['settings'])
                text=text.replace('.control\n','.control\nset numdgt=17\n')
                deck=(root/label/'raw'/row['case']/'input.cir').read_text()
                if normalize_deck(text)!=normalize_deck(deck):raise ValueError('Generated and retained deck differ')
            records[label]=record
        outcomes=[score_prediction(p,records['dip_'+str(p['dip_V']).replace('.','p')],plan['node_tolerance_V']) for p in plan['predictions']]
        pair=paired_control(records['retained'],records['commanded'])
        source=json.loads((folder/'summary.json').read_text())
        for actual,expected in zip(outcomes,source['outcomes']):
            for key in actual:
                if key!='record' and actual[key]!=expected[key]:raise ValueError('Mechanism outcome differs: '+key)
        if pair!=source['paired_control']:raise ValueError('Paired control differs')
        # Replay the deliberately mismatched prediction and supply-history controls.
        summary=dict(output_dir=str(root),plan=plan,outcomes=outcomes)
        count=checks(summary,records['retained'],records['commanded'])
    result=dict(status='passed',evidence_kind='saved vectors regenerated and remeasured; no fresh SPICE',
                checks=count,outcomes=[{k:v for k,v in r.items() if k!='record'} for r in outcomes],
                paired_control=pair,archive_sha256=manifest['archive_sha256'])
    return result


if __name__=='__main__':print(json.dumps(audit(),indent=2))
