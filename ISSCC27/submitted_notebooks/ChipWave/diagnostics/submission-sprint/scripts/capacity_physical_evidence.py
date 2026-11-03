"""Read independent F/G/H evidence from one immutable physical attempt, not agent prose."""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from capacity_integration_physical import CASE, PERIOD_PS, verified_integration
from capacity_protocol import GDS_GATES, CONSTRAINT_GATES
from study_protocol import digest, write_json

sys.path.append(str(CASE/'scripts'))
from classify_study_failures import read_reports, number
from run_postroute_workloads import source_views


def checked_path(root, name):
    path=Path(root)/name
    if Path(name).is_absolute() or not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Evidence path escapes its attempt')
    if any(p.is_symlink() for p in (path,*path.parents) if p.is_relative_to(root)):
        raise ValueError('Evidence symlink')
    return path


def commit_bytes(project, commit, path):
    if not re.fullmatch(r'[0-9a-f]{40}',commit) or Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('Invalid committed view')
    return subprocess.check_output(['git','show',commit+':'+path],cwd=project,timeout=30)


def committed_files(run, expected_source=None):
    """Authenticate collected reports and prepared sources against their attempt commit."""
    project,evidence=run/'project',run/'evidence'
    selected=evidence/'selected-delivery.json'
    if selected.exists():
        record=json.loads(selected.read_text());commit=record['content']['commit'];files=record['collected_files']
    else:
        record=json.loads((evidence/'failed-attempt.json').read_text())
        commit=record['workspace_commit'];files=record['files']
    if not re.fullmatch(r'[0-9a-f]{40}',commit):
        raise ValueError('Invalid attempt commit')
    if len({r['path'] for r in files})!=len(files):
        raise ValueError('Duplicate collected view')
    for item in files:
        path=checked_path(evidence,item['path'])
        if digest(path)!=item['sha256']:
            raise ValueError('Collected view changed: '+item['path'])
        original=item.get('source_path','build/rtl-to-gds/'+item['path'])
        if not original.startswith('build/rtl-to-gds/') or '..' in Path(original).parts:
            raise ValueError('Unexpected physical source path')
        blob=subprocess.check_output(['git','rev-parse',commit+':'+original],cwd=project,text=True,timeout=30).strip()
        h=hashlib.sha1();h.update(f'blob {path.stat().st_size}\0'.encode())
        with path.open('rb') as handle:
            for part in iter(lambda:handle.read(1<<20),b''):h.update(part)
        if h.hexdigest()!=blob:
            raise ValueError('Report is not from its declared attempt commit')
    manifest=json.loads((run/'manifest.json').read_text())
    _,frozen=verified_integration(manifest['task'])
    if manifest['integration_sha256']!=frozen['source_sha256']:
        raise ValueError('Frozen integration inputs changed')
    sources=dict(manifest['rtl_sha256'],**{
        'physical/chip-nebula/constraints.sdc':manifest['sdc_sha256'],
        'physical/chip-nebula/config.mk':manifest['config_sha256']})
    for name,sha in sources.items():
        if digest(checked_path(project,name))!=sha or hashlib.sha256(commit_bytes(project,commit,name)).hexdigest()!=sha:
            raise ValueError('Source/configuration differs between submission and attempt')
    if manifest['period_ps']!=PERIOD_PS or manifest['threads']!=2:
        raise ValueError('Physical resource contract changed')
    if expected_source is not None:
        admitted=manifest['candidate_admission']
        if admitted['source_sha256']!=expected_source or admitted['canonical_rtl_sha256']!=manifest['rtl_sha256'].get('rtl/candidate/design.sv'):
            raise ValueError('GDS belongs to a different budgeted submission')
    return commit,manifest,files


def audit(run, output, *, expected_source=None):
    run,output=Path(run).resolve(),Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    gds=dict.fromkeys(GDS_GATES,False);constraints=dict.fromkeys(CONSTRAINT_GATES,False)
    row=dict(gds=gds,constraints=constraints,measurements=None,errors=[],model_calls=0,physical_attempts=0)
    physical_checked=False
    try:
        commit,manifest,files=committed_files(run,expected_source)
        evidence=run/'evidence';raw,native,errors=read_reports(evidence)
        if errors:raise ValueError('Physical report parse failure')
        gds['provenance']=True
        def path_for(name):
            paths=[item['path'] for item in files if Path(item['path']).name==name]
            if len(paths)!=1:raise ValueError('Missing/ambiguous final view: '+name)
            return checked_path(evidence,paths[0])
        layout=path_for('6_final.gds')
        if digest(layout)!=native.get('gds',{}).get('sha256'):
            raise ValueError('GDS summary belongs to another layout')
        prefix=str(path_for('6_final.v').relative_to(evidence).parent)
        database=output/'6_final.odb'
        database.write_bytes(commit_bytes(run/'project',commit,'build/rtl-to-gds/'+prefix+'/6_final.odb'))
        script=output/'route-audit.tcl'
        script.write_text('if {[catch {\nread_db {'+str(database)+'}\n'
            'set complete [design_is_routed -verbose]\nputs "CAPACITY_ALL_SIGNAL_NETS_ROUTED=$complete"\n'
            '} msg]} {puts stderr $msg;exit 1}\nexit\n')
        result=subprocess.run(['openroad','-no_init','-exit','-threads','2',str(script)],
                              text=True,capture_output=True,timeout=120)
        (output/'route-audit.log').write_text(result.stdout+result.stderr)
        gds['zero_unrouted']=result.returncode==0 and 'CAPACITY_ALL_SIGNAL_NETS_ROUTED=1' in result.stdout
        route_log=path_for('5_2_route.log').read_text()
        gds['routed']='Complete detail routing.' in route_log
        reader=output/'read-gds.py'
        reader.write_text('import pya,json\nl=pya.Layout();l.read('+repr(str(layout))+')\n'
            'tops=[c.name for c in l.top_cells()]\n'
            'assert tops==["nebula_cpu_npu_top"] and l.cells()>0\n'
            'print("CAPACITY_GDS_READ_PASS")\n')
        result=subprocess.run(['klayout','-b','-r',str(reader)],text=True,capture_output=True,timeout=120)
        (output/'read-gds.log').write_text(result.stdout+result.stderr)
        gds['readable_gds']=result.returncode==0 and 'CAPACITY_GDS_READ_PASS' in result.stdout
        # Failed deliveries may omit XML from their collection; recover the unchanged committed deck result.
        xmlname='build/rtl-to-gds/orfs-work/reports/sky130hd/nebula_cpu_npu_top/nebula/6_drc.lyrdb'
        xml=output/'6_drc.lyrdb';xml.write_bytes(commit_bytes(run/'project',commit,xmlname))
        tree=ET.parse(xml)
        gds['drc']=(number(native.get('drc_violations')) and native['drc_violations']==0
                    and tree.getroot().tag=='report-database' and tree.find('items') is not None
                    and len(tree.findall('.//items/item'))==0)
        gds['lvs']=native.get('lvs')=='matched' and 'Netlists match.' in path_for('6_lvs.log').read_text()
        for kind in ('setup','hold'):
            slack=raw.get('finish__timing__'+kind+'__ws')
            count=raw.get('finish__timing__drv__'+kind+'_violation_count')
            constraints[kind]=number(slack) and slack>=0 and number(count) and count==0
        gds['hold']=constraints['hold']
        for key,metric in (('slew','max_slew'),('capacitance','max_cap'),('fanout','max_fanout')):
            value=raw.get('finish__timing__drv__'+metric)
            constraints[key]=number(value) and value==0
        row.update(task=manifest['task'],commit=commit,database_sha256=digest(database),
                   source_sha256=manifest.get('candidate_admission',{}).get('source_sha256'),
                   metrics=raw,declared_unrouted_scope='OpenDB multi-terminal nonspecial nets without routing or abutment; LVS separately checks connectivity')
        physical_checked=True
        measurement=run/'workloads/summary.json'
        if measurement.exists():
            views=source_views(evidence);summary=json.loads(measurement.read_text())
            if summary.get('task')!=manifest['task']:
                raise ValueError('Workload belongs to another task')
            attestation=json.loads((evidence/'measurement-source.json').read_text())
            if attestation['source_commit']!=commit or attestation['database_sha256']!=digest(database):
                raise ValueError('Power extraction belongs to another physical database')
            if summary['source_view_sha256']!=views['hashes'] or summary['clock_period_ns']!=PERIOD_PS/1000:
                raise ValueError('Activity/clock/physical view mismatch')
            workloads={}
            if len(summary['rows'])!=3 or {r['workload'] for r in summary['rows']}!={'short','mixed','long'}:
                raise ValueError('Wrong workload population')
            valid=True
            for item in summary['rows']:
                name=item['workload'];folder=run/'workloads'/name
                if digest(checked_path(run/'workloads',item['vcd']))!=item['vcd_sha256']:
                    raise ValueError('Activity waveform changed')
                power_folder=run/'workloads/power'/name
                for filename,sha in item['power_reports_sha256'].items():
                    if digest(checked_path(power_folder,filename))!=sha:raise ValueError('Power report changed')
                for filename,key in (('memory.hex','memory_sha256'),('workload.json','workload_sha256')):
                    if digest(folder/filename)!=item[key] or item[key]!=manifest['integration_sha256']['workloads/'+name+'/'+filename]:
                        raise ValueError('Workload image changed')
                valid &= (item.get('measurement_qualified') is True and item['activity_annotation']['unannotated_pins']==0
                          and item['activity_annotation']['vcd_pins']>0
                          and item['parasitic_annotation']['eligible_unannotated_drivers']==0)
                watts=json.loads((power_folder/'power.json').read_text())['Total']['total']
                metadata=json.loads((folder/'workload.json').read_text())
                useful=metadata['useful_macs' if manifest['task'].startswith('A') else 'useful_transactions']
                seconds=(item['activity_end_ps']-item['activity_start_ps'])*1e-12
                if useful<=0 or seconds<=0 or not number(watts) or watts<=0:
                    raise ValueError('Invalid workload measurement')
                values=dict(throughput=useful/seconds,latency=seconds,power=watts,energy=watts*seconds/useful)
                for key,reported in (('throughput',item['throughput_per_second']),('latency',item['latency_seconds']),
                                     ('power',item['estimated_power_w']['total']),('energy',item['energy_per_useful_work_j'])):
                    if not math.isclose(values[key],reported,rel_tol=1e-9,abs_tol=0):
                        raise ValueError('Summary differs from raw workload measurement: '+key)
                workloads[name]=values
            constraints['postroute_function']=summary.get('passed') is True and all(r.get('passed') is True for r in summary['rows'])
            constraints['measurement_valid']=bool(valid and summary.get('measurement_qualified') is True and summary.get('gate_level') is True)
            row['measurements']=dict(cell_area=raw['finish__design__instance__area__stdcell'],
                die_area=raw['finish__design__die__area'],workloads=workloads)
    except Exception as error:
        row['errors'].append(type(error).__name__+': '+str(error))
        # A provenance failure cannot be traded against other passing gates.
        if not physical_checked:
            gds['provenance']=False
        constraints['measurement_valid']=False
    write_json(output/'audit.json',row)
    return row
