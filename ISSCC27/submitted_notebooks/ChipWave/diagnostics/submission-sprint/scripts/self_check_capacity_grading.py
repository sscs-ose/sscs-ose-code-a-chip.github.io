"""Actual reference grading plus immutable-view and no-historical-rescue rejection."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from capacity_integration_physical import ROOT
from capacity_physical_evidence import audit, committed_files
from capacity_grade import function, latest_physical,checkpoint
from capacity_toolbox import source_hashes
from capacity_meter import TokenLedger
from capacity_protocol import score,GDS_GATES,CONSTRAINT_GATES
from study_protocol import digest, write_json


def replace_json(path,value):
    replacement=path.with_suffix(path.suffix+'.replacement')
    replacement.write_text(json.dumps(value,indent=2)+'\n');replacement.replace(path)


def diagnostics(temp):
    runtime=temp/'diagnostic-runtime';ledger=TokenLedger()
    tools=[]
    for index in (1,2):
        capture=runtime/'tools/snapshots'/str(index);(capture/'rtl').mkdir(parents=True)
        (capture/'rtl/design.sv').write_text(f'module fixture(output y);assign y=1\'b{index-1};endmodule\n')
        hashes=source_hashes(capture)
        write_json(capture/'capture.json',dict(capture_monotonic=index*10))
        ledger.state['snapshots'].append(dict(id=str(index),tokens=index*100000,
            budget_admissible=True,source_sha256=hashes))
        write_json(runtime/'eda'/f'trial-physical-{index:04d}'/'result.json',
            dict(identity=f'trial-physical-{index:04d}',capture_id=str(index),tool_id=index,
                 source_sha256=hashes,status='passed' if index==1 else 'failed',seconds=1))
        tools.append(dict(id=index,kind='physical',monotonic_end=index*10+1))
    ledger.state['actual_tokens']=200000;write_json(runtime/'usage.json',ledger.state)
    write_json(runtime/'clock.json',dict(start=0));write_json(runtime/'tools/tool-ledger.json',dict(attempts=tools))
    measurements=dict(cell_area=100,die_area=200,workloads=dict(w=dict(throughput=1,latency=1,power=1,energy=1)))
    def audited(run,*args,**kwargs):
        g=dict.fromkeys(GDS_GATES,True)
        if str(run).endswith('0002'):g['hold']=False
        return dict(task='A1',gds=g,constraints=dict.fromkeys(CONSTRAINT_GATES,True),measurements=measurements,errors=[])
    with patch('capacity_grade.function',return_value=dict(function=True,integration=True,evaluation_valid=True)),\
         patch('capacity_grade.audit',side_effect=audited):
        final=checkpoint(runtime,'A1',1000000,measurements,temp/'final-score')
        first=checkpoint(runtime,'A1',1000000,measurements,temp/'first-score',physical_identity='trial-physical-0001')
    assert final['snapshot_id']=='2' and final['functional_pass'] and not final['gds_pass'] and final['final_score']==0
    assert first['selection']=='physical_attempt_diagnostic' and first['snapshot_id']=='1' and first['final_score']==50
    assert first['source_tokens']==100000 and first['source_elapsed_seconds']==10 and first['delivery_elapsed_seconds']==11
    assert final['selection']=='latest_checkpoint' and final['final_score']==0
    assert final['measurements']==measurements and first['measurements']==measurements
    report=dict(passed=True,model_calls=0,physical_runs=0,scope='Synthetic captured sources and evaluator verdicts',
        checks=['first success and second regression remain independently measurable',
                'diagnostic first success cannot replace latest final zero','observed source/delivery costs remain distinct',
                'raw audited measurements retained even when a gate fails'])
    write_json(ROOT/'checks/physical-attempt-diagnostics.json',report)
    return report


def check():
    original=ROOT/'physical/calibration-integration-A1'
    report=dict(model_calls=0,physical_runs=0,checks=[])
    with tempfile.TemporaryDirectory(prefix='capacity-grading-') as temporary:
        temp=Path(temporary)
        diagnostics(temp)
        verified=audit(original,temp/'original-audit')
        assert all(verified['gds'].values()) and all(verified['constraints'].values()),verified['errors']
        mark=score(dict(function=True,integration=True),verified['gds'],verified['constraints'],
                   verified['measurements'],verified['measurements'])
        assert mark['final_score']==50,mark
        report['checks'].append('Actual reference has all physical/measurement gates and self-normalizes to 50')
        clone=temp/'clone';clone.mkdir()
        shutil.copy2(original/'manifest.json',clone/'manifest.json')
        subprocess.run(['git','clone','--shared','--no-checkout','-q',str(original/'project'),str(clone/'project')],check=True)
        manifest=json.loads((original/'manifest.json').read_text())
        for name in [*manifest['rtl_sha256'],'physical/chip-nebula/constraints.sdc','physical/chip-nebula/config.mk']:
            (clone/'project'/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(original/'project'/name,clone/'project'/name)
        shutil.copytree(original/'evidence',clone/'evidence',copy_function=os.link)
        commit,_,files=committed_files(clone)
        net=next(r['path'] for r in files if Path(r['path']).name=='6_final.v')
        path=clone/'evidence'/net;before=digest(original/'evidence'/net)
        replacement=path.with_suffix('.replacement');replacement.write_text('module wrong;endmodule\n');replacement.replace(path)
        rejected=audit(clone,temp/'mixed-netlist')
        assert not rejected['gds']['provenance'] and rejected['errors']
        assert digest(original/'evidence'/net)==before
        path.unlink();os.link(original/'evidence'/net,path)
        report['checks'].append('Mixed netlist is rejected without changing the original attempt')
        shutil.copytree(original/'workloads',clone/'workloads',copy_function=os.link)
        summary=clone/'workloads/summary.json';data=json.loads(summary.read_text())
        data['rows'][0]['estimated_power_w']['total']*=.5
        replace_json(summary,data)
        invalid=audit(clone,temp/'bad-measurement')
        assert all(invalid['gds'].values()) and not invalid['constraints']['measurement_valid'],invalid
        marked=score(dict(function=True,integration=True),invalid['gds'],invalid['constraints'],
                     invalid['measurements'],verified['measurements'])
        assert marked['gds_pass'] and marked['final_score']==0
        report['checks'].append('Changed power summary yields zero while retaining independent GDS pass')
        ledger=TokenLedger();ledger.state['snapshots']=[
            dict(id='first',tokens=100,budget_admissible=True,source_sha256={'rtl/design.sv':'one'}),
            dict(id='second',tokens=200,budget_admissible=True,source_sha256={'rtl/design.sv':'two'})]
        attempts=[dict(capture_id='first',tool_id=1,source_sha256={'rtl/design.sv':'one'},status='passed'),
                  dict(capture_id='second',tool_id=2,source_sha256={'rtl/design.sv':'two'},status='failed')]
        assert latest_physical(attempts,ledger,150)['tool_id']==1
        assert latest_physical(attempts,ledger,250)['status']=='failed'
        attempts[1]['source_sha256']={'rtl/design.sv':'one'}
        try:latest_physical(attempts,ledger,250)
        except ValueError:pass
        else:raise AssertionError('Changed source association accepted')
        report['checks'].append('Latest admitted failed attempt cannot fall back to a historical success')
        for task in ('A1','B2'):
            snapshot=temp/task;(snapshot/'rtl').mkdir(parents=True)
            shutil.copy2(ROOT/'tasks'/task/'grader/reference.sv',snapshot/'rtl/design.sv')
            result=function(snapshot,task,temp/(task+'-graded'))
            assert result['function'] and result['integration'] and result['synthesis'],result
            assert len(result['integration_checks'])==9
            report['checks'].append('Actual '+task+' canonical function/progress/synthesis and nine CPU checks')
    report['passed']=True
    write_json(ROOT/'checks/grading-evidence.json',report)
    return report


if __name__=='__main__':
    print(json.dumps(check()))
