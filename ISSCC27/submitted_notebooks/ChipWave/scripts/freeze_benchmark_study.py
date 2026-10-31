"""Freeze the public PPA comparison and all used SDK resources before model search."""
from __future__ import annotations
import argparse
import datetime
import json
from pathlib import Path
from study_protocol import digest,write_json

CASE=Path(__file__).resolve().parents[1]


def verify(campaign,metadata):
    campaign=Path(campaign).resolve()
    record=json.loads((campaign/'ppa/formal-freeze.json').read_text())
    for relative,expected in record['helpers'].items():
        if digest(CASE/relative)!=expected:raise ValueError('Frozen execution component changed: '+relative)
        if relative.startswith('runtime/src/'):
            import chip_nebula
            installed=Path(chip_nebula.__file__).resolve().parent.parent/Path(relative).relative_to('runtime/src')
            if digest(installed)!=expected:raise ValueError('Installed SDK differs from frozen public component: '+relative)
    if digest(campaign/'protocol.json')!=record['protocol_sha256']:
        raise ValueError('Frozen experiment protocol changed')
    if metadata['baseline_sha256']!=record['baseline_sha256']:
        raise ValueError('Session received a different normalization baseline')
    if digest(campaign/'checks/rtl-actions/admission.json')!=record['action_admission_sha256']:
        raise ValueError('Shared action qualification changed')
    return record


def freeze(campaign,baseline):
    campaign,baseline=Path(campaign).resolve(),Path(baseline).resolve()
    output=campaign/'ppa/formal-freeze.json'
    if output.exists():raise ValueError('Existing formal freeze retained')
    if not json.loads(baseline.read_text())['rank_eligible']:raise ValueError('The common baseline must qualify first')
    admission=campaign/'checks/rtl-actions/admission.json'
    if not json.loads(admission.read_text())['admitted']:raise ValueError('Shared actions are not admitted')
    helpers=set(json.loads((CASE/'results/configurable-study/ppa/source-bindings.json').read_text()))
    helpers.update(['run_benchmark_ppa.py','benchmark_ppa_proposal.py','benchmark_rtl_actions.py','campaign_budget.py',
                    'study_portability.py','freeze_benchmark_study.py'])
    paths=[CASE/'scripts'/name for name in sorted(helpers)]
    manifest=json.loads((CASE/'runtime/used-components.json').read_text())
    for item in manifest['files']:
        path=CASE/'runtime/src'/item['path']
        if digest(path)!=item['sha256']:raise ValueError('Public SDK source/resource manifest mismatch')
        paths.append(path)
    paths+=[CASE/'runtime/used-components.json',CASE/'workflows/cpu-npu-physical.yaml',CASE/'workflows/case-physical-tool.yaml']
    paths+=list((CASE/'released_design/rtl').rglob('*.sv'))
    paths+=[p for p in (CASE/'verification').iterdir() if p.is_file() and p.suffix in ('.py','.sv','.json')]
    paths.append(CASE/'toolchain/orfs/source-manifest.json')
    snapshot=campaign/'ppa/executed-sources'
    if snapshot.exists():raise ValueError('Existing executed source snapshot retained')
    import shutil
    for path in paths:
        target=snapshot/path.relative_to(CASE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    record=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        protocol_sha256=digest(campaign/'protocol.json'),baseline_sha256=digest(baseline),action_admission_sha256=digest(admission),
        helpers={str(p.relative_to(CASE)):digest(p) for p in paths},
        scope='Common PPA study only; task-factory reference qualification has its own records; no model or physical calls')
    write_json(output,record)
    print('PUBLIC_PPA_FREEZE_READY',len(record['helpers']),'execution sources/resources',flush=True)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,required=True);parser.add_argument('--baseline',type=Path,required=True)
    args=parser.parse_args();freeze(args.campaign,args.baseline)
