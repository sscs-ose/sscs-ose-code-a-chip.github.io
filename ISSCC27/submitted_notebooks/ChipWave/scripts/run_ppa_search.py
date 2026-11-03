#!/usr/bin/env python3
"""Run a fixed, matched floorplan study through actual ChipWave tool workflows."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
from prepare_replay_physical import prepare

ROOT=Path(__file__).resolve().parents[1]
VARIANTS=(('baseline10',10),('compact30',30),('compact40',40))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(command,log,cwd):
    with log.open('w') as handle:
        result=subprocess.run(command,cwd=cwd,stdout=handle,stderr=subprocess.STDOUT)
    return result.returncode


def search(output, electrical_closure=False):
    if output.exists():raise ValueError('Existing experiment preserved; use another output directory')
    source=ROOT/'released_design'
    rtl={str(p.relative_to(source)):digest(p) for p in sorted(source.glob('rtl/**/*.sv'))}
    released=json.loads((source/'selected-delivery.json').read_text())['exported_source_sha256']
    assert rtl and all(released[k]==v for k,v in rtl.items())
    flow_root=ROOT/'toolchain/orfs'
    os.environ['ORFS_ROOT']=str(flow_root)
    os.environ['NUM_CORES']='2'
    flow_files=json.loads((flow_root/'source-manifest.json').read_text())['files']
    def check_flow():
        for item in flow_files:assert digest(flow_root/item['path'])==item['sha256'],item['path']
    check_flow()
    output.mkdir(parents=True)
    plan={'variants':[{'name':n,'core_utilization_percent':u} for n,u in VARIANTS],
        'rtl_sha256':rtl,'platform':'sky130hd','clock_period_ns':100,
        'corner':{'process':'TT','temperature_c':25,'voltage_v':1.8},
        'place_density':0.55,'abc_area':1,'threads':2,
        'selection_rule':'Smallest die area among completed physical runs with zero timing/DRC/electrical violations and matched LVS; report all PPA tradeoffs',
        'power_scope':'OpenSTA estimate under the unchanged flow activity model; no measured silicon power',
        'execution':'Three separately frozen ChipWave TaskGraph tool workflows; no model calls or RTL edits',
        'flow_source_files':flow_files,'source_bundle_sha256':digest(flow_root/'source-manifest.json')}
    variants=(('repair30',30),) if electrical_closure else VARIANTS
    margins={'cap_margin':10,'slew_margin':10} if electrical_closure else {}
    plan.update(phase='electrical_closure' if electrical_closure else 'floorplan_sweep',
                variants=[{'name':n,'core_utilization_percent':u,**margins} for n,u in variants],
                repair_margins_percent=margins)
    if electrical_closure:plan['execution']='One separately frozen ChipWave tool workflow after electrical violations were observed; unchanged RTL, clock and library limits'
    (output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    rows=[]
    for name,utilization in variants:
        check_flow()
        project=output/name;shutil.copytree(source,project)
        print('PPA_START',name,flush=True);start=time.monotonic()
        prepare(project,core_utilization=utilization,place_density=0.55,**margins)
        assert {k:digest(project/k) for k in rtl}==rtl
        constraints=digest(project/'physical/chip-nebula/constraints.sdc')
        if rows:assert constraints==rows[0]['constraints_sha256']
        code=checked([sys.executable,'-m','chip_nebula.cli.commands','--project-root',str(project),
            'run',str(project/'.chip_nebula/recipes/cpu-npu-physical.yaml'),
            '--workflow','independent-replay','--param','rtl=imported-main-rtl','--workers','1','--resume'],
            output/(name+'-workflow.log'),ROOT)
        row={'name':name,'core_utilization_percent':utilization,'exit_code':code,
             'wall_seconds':time.monotonic()-start,'passed':False,'constraints_sha256':constraints,
             'source_unchanged':{k:digest(project/k) for k in rtl}==rtl}
        check_flow()
        with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            row['task_state']=store.task_state('independent-replay:physical').value
            selected=store.deliveries('independent-replay:physical').get('report')
            if selected:
                artifact=store.get_artifact(selected.artifact_id)
                row['physical_artifact']=artifact.document()
                row['physical_summary']=artifact.payload.get('raw_flow_summary',{})
                if row['task_state']=='satisfied' and artifact.payload.get('verdict')=='passed':
                    collect=output/(name+'-collect.log')
                    collected=checked([sys.executable,str(ROOT/'scripts/collect_physical.py'),
                        '--project',str(project),'--workflow','independent-replay',
                        '--output',str(output/'evidence'/name),'--include-operators'],collect,ROOT)
                    assert collected==0,collect
                    reports=list((output/'evidence'/name).glob('orfs-work/logs/**/6_report.json'))
                    assert len(reports)==1
                    raw=json.loads(reports[0].read_text())
                    row['electrical_violations']={k:raw['finish__timing__drv__'+k] for k in ('max_slew','max_cap','max_fanout')}
                    row['passed']=(code==0 and row['source_unchanged'] and all(v==0 for v in row['electrical_violations'].values()))
            if not selected:
                attempts=store.list_attempts('independent-replay:physical')
                row['failure_reasons']=[a.diagnostics.get('failure_reason','') for a in attempts]
        rows.append(row)
        (output/'progress.json').write_text(json.dumps({'plan':plan,'rows':rows,'complete':len(rows)==len(variants)},indent=2)+'\n')
        print('PPA_FINISHED',name,'qualified=',row['passed'],flush=True)
    eligible=[r for r in rows if r['passed']]
    selected=min(eligible,key=lambda r:r['physical_summary']['metrics']['die_area_um2'])['name'] if eligible else None
    summary={'complete':True,'plan':plan,'rows':rows,'selected':selected,
             'all_scheduled_runs_reported':True,'model_calls':0,'rtl_modified':False}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('PPA_SEARCH_FINISHED selected='+str(selected),flush=True)
    if selected is None:raise RuntimeError('No qualified PPA candidate; all failed evidence is preserved')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--electrical-closure',action='store_true',help='Repeat the 30%% floorplan with 10%% slew/cap repair margins; preserve the initial sweep')
    args=parser.parse_args();search(args.output.resolve(),args.electrical_closure)
