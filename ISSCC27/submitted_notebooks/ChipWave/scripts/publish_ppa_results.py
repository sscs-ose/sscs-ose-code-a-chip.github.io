#!/usr/bin/env python3
"""Publish actual matched PPA deliveries and derive a readable comparison."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from chip_nebula.taskgraph.static_store import StaticTaskGraphStore

ROOT=Path(__file__).resolve().parents[1]
RAW_METRICS={
    'die_area_um2':'finish__design__die__area',
    'placed_instance_area_um2':'finish__design__instance__area',
    'estimated_total_power_w':'finish__power__total',
    'estimated_fmax_hz':'finish__timing__fmax',
    'setup_slack_ns':'finish__timing__setup__ws',
    'hold_slack_ns':'finish__timing__hold__ws',
}


def comparison_metrics(physical,raw):
    for name,key in RAW_METRICS.items():
        value=raw[key]
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('Invalid physical measurement: '+name)
        if name in ('die_area_um2','placed_instance_area_um2','estimated_total_power_w','estimated_fmax_hz') and value<=0:
            raise ValueError('Nonpositive physical measurement: '+name)
        if physical['metrics'][name]!=value:
            raise ValueError('Summary and original report disagree: '+name)
    return {name:raw[key] for name,key in RAW_METRICS.items()}


def publish(study, closure_study=None):
    data=json.loads((study/'summary.json').read_text())
    assert data['complete'] and len(data['rows'])==len(data['plan']['variants'])
    assert [(r['name'],r['core_utilization_percent']) for r in data['rows']]==[
        ('baseline10',10),('compact30',30),('compact40',40)],'Incomplete or unexpected study matrix'
    destination=ROOT/'results/ppa'
    if destination.exists():raise ValueError('Existing PPA evidence preserved')
    cases=[(study,r,'floorplan_sweep',{}) for r in data['rows']]
    closure=None
    if closure_study is not None:
        closure=json.loads((closure_study/'summary.json').read_text())
        assert closure['complete'] and len(closure['rows'])==1
        assert [(r['name'],r['core_utilization_percent']) for r in closure['rows']]==[('repair30',30)]
        assert closure['plan']['repair_margins_percent']=={'cap_margin':10,'slew_margin':10}
        for key in ('rtl_sha256','platform','clock_period_ns','corner','place_density','abc_area','threads','flow_source_files','source_bundle_sha256'):
            assert closure['plan'][key]==data['plan'][key], 'Unmatched closure input: '+key
        cases.extend((closure_study,r,'electrical_closure',closure['plan']['repair_margins_percent']) for r in closure['rows'])
    rows=[];configs=[]
    for source_study,row,phase,margins in cases:
        name=row['name'];project=source_study/name
        result={'name':name,'initial_core_utilization_percent':row['core_utilization_percent'],
            'phase':phase,'repair_margins_percent':margins,
            'qualified':row['passed'],'task_state':row['task_state'],
            'source_unchanged':row['source_unchanged'],'electrical_violations':row.get('electrical_violations'),
            'constraints_sha256':row['constraints_sha256'],'workflow_wall_seconds':row['wall_seconds'],
            'metrics':None,'evidence_directory':name,
            'tool_versions':row.get('physical_artifact',{}).get('payload',{}).get('tool_versions')}
        evidence=source_study/'evidence'/name
        if evidence.is_dir():
            physical=json.loads((evidence/'summary.json').read_text())
            reports=list(evidence.glob('orfs-work/logs/**/6_report.json'));assert len(reports)==1
            raw=json.loads(reports[0].read_text())
            result['metrics']=comparison_metrics(physical,raw)
            qualified=(row['exit_code']==0 and row['task_state']=='satisfied' and row['source_unchanged']
                       and physical['passed'] and physical['metrics']['clock_period_ns']==100
                       and physical['detailed_routing_violations']==0 and physical['drc_violations']==0
                       and physical['lvs']=='matched' and physical['metrics']['setup_violations']==0
                       and physical['metrics']['hold_violations']==0
                       and all(raw['finish__timing__drv__'+k]==0 for k in ('max_slew','max_cap','max_fanout')))
            assert qualified==row['passed'],'Recorded qualification disagrees with raw evidence'
            result.update(route_drc=physical['detailed_routing_violations'],gds_drc=physical['drc_violations'],
                          lvs=physical['lvs'],setup_violations=physical['metrics']['setup_violations'],
                          hold_violations=physical['metrics']['hold_violations'])
        with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            source=store.get_artifact('imported-main-rtl')
            assert source
            commit=source.content.commit
            frozen={}
            for relative in ('physical/chip-nebula/config.mk','physical/chip-nebula/constraints.sdc',
                             'physical/chip-nebula/flow-definition.json','physical/chip-nebula/implementation-variant.json'):
                content=subprocess.run(['git','show',commit+':'+relative],cwd=project,capture_output=True,check=True).stdout
                frozen[Path(relative).name]=content
            assert hashlib.sha256(frozen['constraints.sdc']).hexdigest()==row['constraints_sha256']
            config=frozen['config.mk'].decode()
            for key,value in [('CORE_UTILIZATION',row['core_utilization_percent']),
                              ('CAP_MARGIN',margins.get('cap_margin')),('SLEW_MARGIN',margins.get('slew_margin'))]:
                declarations=[line for line in config.splitlines() if line.startswith('export '+key+' = ')]
                assert declarations==([] if value is None else ['export '+key+' = '+str(value)]), 'Frozen search parameter disagrees: '+key
            configs.append(config)
            result['input_artifact']=source.document()
            result['attempts']=[{'id':a.id,'status':a.status.value,'failure_reason':a.diagnostics.get('failure_reason',''),
                                'workspace_commit':a.workspace_commit} for a in store.list_attempts('independent-replay:physical')]
            result['frozen_input_files']={k:hashlib.sha256(v).hexdigest() for k,v in frozen.items()}
        result['_frozen']=frozen
        result['_study']=source_study
        rows.append(result)
    baseline=next(r for r in rows if r['name']=='baseline10')
    selected=min((r for r in rows if r['qualified']),key=lambda r:r['metrics']['die_area_um2'])
    assert baseline['qualified'] and selected['qualified']
    assert baseline['tool_versions'] and all(
        r['tool_versions']==baseline['tool_versions'] for r in rows if r['qualified']), 'Unmatched reported tool versions'
    assert selected==min((r for r in rows if r['qualified']),key=lambda r:r['metrics']['die_area_um2'])
    assert selected['metrics']['die_area_um2']<baseline['metrics']['die_area_um2'],'No qualified footprint improvement yet'
    for config in configs:
        knobs=('export CORE_UTILIZATION = ','export CAP_MARGIN = ','export SLEW_MARGIN = ')
        normalized='\n'.join(line for line in config.splitlines() if not line.startswith(knobs))
        first='\n'.join(line for line in configs[0].splitlines() if not line.startswith(knobs))
        assert normalized==first,'Unmatched physical configuration beyond the planned search parameters'
    destination.mkdir(parents=True)
    for row in rows:
        name=row['name'];folder=destination/name
        source_study=row.pop('_study')
        if (source_study/'evidence'/name).exists():shutil.copytree(source_study/'evidence'/name,folder)
        else:folder.mkdir()
        inputs=folder/'frozen-inputs';inputs.mkdir()
        for filename,content in row.pop('_frozen').items():(inputs/filename).write_bytes(content)
        (folder/'attempts.json').write_text(json.dumps(row['attempts'],indent=2)+'\n')
        shutil.copy2(source_study/(name+'-workflow.log'),folder/'workflow.log')
    reduction={name:100*(1-selected['metrics'][name]/baseline['metrics'][name])
               for name in ('die_area_um2','placed_instance_area_um2','estimated_total_power_w')}
    summary={'complete':True,'passed':True,'selected':selected['name'],'rows':rows,'plan':data['plan'],
        'electrical_closure_plan':closure['plan'] if closure else None,
        'electrical_closure_description_note':(
            'The preserved early closure plan says three workflows in its execution prose; its variant list schedules one repair30 workflow. This descriptive typo was fixed in the released script; the original plan is preserved.'
            if closure and closure['plan']['execution'].startswith('Three') else None),
        'reported_tool_versions':baseline['tool_versions'],
        'reduction_percent':reduction,
        'estimated_fmax_change_percent':100*(selected['metrics']['estimated_fmax_hz']/baseline['metrics']['estimated_fmax_hz']-1),
        'scope':'Physical-parameter exploration of byte-identical accepted RTL at one nominal corner and common 100 ns constraints; power and Fmax are tool estimates, not silicon measurements',
        'selection_rule':data['plan']['selection_rule'],'global_optimum_claimed':False,
        'functional_evidence':'Original complete CPU/NPU acceptance is bound by unchanged RTL bytes; each physical workflow also executed the common kernel simulation command, preserved in its simulation log'}
    (destination/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    shutil.copy2(study/'plan.json',destination/'plan.json')
    if closure_study is not None:shutil.copy2(closure_study/'plan.json',destination/'electrical-closure-plan.json')
    print(json.dumps({'selected':summary['selected'],'reduction_percent':reduction,'output':str(destination)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--closure-study',type=Path)
    args=parser.parse_args();publish(args.study.resolve(),args.closure_study.resolve() if args.closure_study else None)
