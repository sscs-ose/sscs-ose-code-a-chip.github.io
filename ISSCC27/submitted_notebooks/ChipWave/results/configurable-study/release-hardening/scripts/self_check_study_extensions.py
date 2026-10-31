"""Check frozen representative selection and absence handling without EDA/model calls."""
import copy
import json
import tempfile
from pathlib import Path

from run_study_extensions import generation_representatives, high_frequency_selection
from study_protocol import BASELINE, digest, preregistration, write_json
from summarize_ppa_study import session_row,infrastructure_costs,summarize,service_notes
from initialize_study import initialize
from export_study_results import copy_evidence, ppa_provenance


def run():
    plan=preregistration();rows=[{'job':job,'passed':True} for job in plan['generation']['jobs']]
    selected=generation_representatives({'complete':True,'rows':rows})
    assert all(row['trial'].endswith('-1') for row in selected)
    changed=copy.deepcopy(rows)
    for row in changed:
        row['physical_score']=999 if row['job']['repetition']==1 else .1
    assert generation_representatives({'complete':True,'rows':changed})==selected
    for row in changed:
        if row['job']['input']=='ip':row['passed']=False
    absent=generation_representatives({'complete':True,'rows':changed})
    assert all(row['trial'] is None for row in absent if row['cell'].startswith('ip'))
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        initialize(root/'new-study')
        bindings=json.loads((root/'new-study/ppa/source-bindings.json').read_text())
        assert {'study_portability.py','audit_study_ip.py','study_checks.py','study_ppa_proposal.py'} <= bindings.keys()
        import gzip
        assert json.loads((root/'new-study/protocol.json').read_text())==json.loads(json.dumps(plan))
        try:initialize(root/'new-study')
        except ValueError:pass
        else:raise AssertionError('Initializer overwrote an existing experiment')
        source=root/'activity.vcd';source.write_bytes(b'actual wave\n')
        target=copy_evidence(source,root/'export/activity.vcd')
        assert gzip.decompress(target.read_bytes())==source.read_bytes()
        assert copy_evidence(source,root/'export/activity.vcd')==target
        source.write_bytes(b'changed wave\n')
        try:copy_evidence(source,root/'export/activity.vcd')
        except ValueError:pass
        else:raise AssertionError('Stale compressed evidence accepted')
        link=root/'linked.vcd';link.symlink_to(source)
        try:copy_evidence(link,root/'export/link.vcd')
        except ValueError:pass
        else:raise AssertionError('Evidence symlink accepted')
        provenance=root/'provenance';published=root/'published'
        expected=('ppa/source-bindings.json','ppa/source-bindings-v1.json',
                  'ppa/measurement-source-correction.json','ppa/executed-helpers-v1/runner.py',
                  'source-correction/manifest.json','source-correction/runner.diff',
                  'release-hardening/measured-original-run_counter_transfer.py')
        for name in expected:
            path=provenance/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name)
        (provenance/'freeze_measurement_correction.py').write_text('archived correction operation\n')
        ppa_provenance(provenance,published)
        for name in expected:assert (published/name).read_bytes()==(provenance/name).read_bytes()
        assert (published/'source-correction/freeze_measurement_correction.py').is_file()
        write_json(root/'protocol.json',plan)
        for job in plan['ppa']['sessions']:
            candidates=[]
            if job['workflow']=='W1':
                candidates=[{'rank_eligible':True,'score':.9,'energy_ratio':.9,'cell_area_um2':100,
                             'candidate_index':2,'configuration':BASELINE},
                            {'rank_eligible':False,'score':.1,'candidate_index':3,'configuration':BASELINE}]
            write_json(root/'ppa'/job['id']/'results/search-summary.json',{'finished':True,'candidates':candidates})
        result=high_frequency_selection(root)
        assert [row['name'] for row in result['choices']]==['common-baseline','W1']
        assert {row['workflow'] for row in result['absences']}=={'W0','W2'}
        assert result['choices'][1]['source_candidate'].endswith('/2')
        write_json(root/'infrastructure-failures/summary.json',{'records':[
            {'original_job':'W2-test','interruption_wall_seconds':100,'role_seconds':40}]})
        assert infrastructure_costs(root)[1]=={'W2-test':100}, 'Failed role time is already inside interruption wall time'
        write_json(root/'infrastructure-failures/summary.json',{'records':[
            {'original_job':'W2-test','interruption_wall_seconds':-1}]})
        try:infrastructure_costs(root)
        except ValueError:pass
        else:raise AssertionError('Negative startup duration accepted')
    candidate={'rank_eligible':True,'score':1.1,'energy_ratio':1.1,'cell_area_um2':100,
        'candidate_index':1,'configuration':BASELINE,'elapsed_search_seconds':200,
        'physical_wall_seconds':150,'postprocess_wall_seconds':20}
    summary={'job':{'id':'W2-test','workflow':'W2'},'finished':True,'candidates':[candidate],
        'physical_launches':1,'unused_candidate_slots':2,'slots':[],
        'budget':{'used_agent_seconds':30,'dispatches':[{'role':'ppa-proposer','elapsed_seconds':20},
                                                       {'role':'ppa-verifier','elapsed_seconds':10}]}}
    row=session_row(summary)
    assert row['best_new_score']==1.1 and row['best_incumbent_score']==1
    assert row['first_new_qualified_seconds']==200 and row['first_strict_improvement_seconds'] is None
    assert row['reviewer_seconds']==10 and row['physical_seconds']==150
    interrupted=copy.deepcopy(summary)
    interrupted.update(candidates=[],workflow_state='paused',slots=[
        {'candidate_index':1,'status':'launched_incomplete'},
        {'candidate_index':2,'status':'unused'},{'candidate_index':3,'status':'unused'}])
    row=session_row(interrupted)
    assert row['incomplete_launches']==1 and row['evaluated']==0 and row['qualified']==0
    assert row['best_new_score'] is None and row['best_incumbent_score']==1
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);job=plan['ppa']['sessions'][0]
        interrupted['job']=job
        write_json(root/'protocol.json',plan)
        write_json(root/'baseline/mhz95-run03/evaluation-v4.json',{'rank_eligible':True,'total_wall_seconds':1})
        record=root/'ppa'/job['id']/'results/search-summary.json';write_json(record,interrupted)
        write_json(record.parents[1]/'session.json',{'started_at':'2026-10-16T00:00:00+00:00'})
        event={'type':'post-response-physical-preflight-failure','job':job['id'],
            'terminal_summary_sha256':digest(record),'failed_tool':'klayout','native_eda_workflow_started':False}
        event_path=root/'infrastructure-failures/physical-preflight-01.json';write_json(event_path,event)
        result=summarize(root,require_complete=False)
        assert result['sessions_completed']==1 and result['normally_finished_sessions']==0
        assert result['infrastructure_aborted_sessions']==1 and result['incomplete_physical_launches']==1
        before=(root/'ppa/analysis.json').read_bytes()
        import os
        os.utime(record,(record.stat().st_atime,record.stat().st_mtime+3600))
        repeated=summarize(root,require_complete=False)
        assert repeated['rows'][0]['total_wall_seconds']==result['rows'][0]['total_wall_seconds']
        assert (root/'ppa/analysis.json').read_bytes()==before, 'Extraction timestamps changed recorded search costs'
        event['type']='physical-workflow-timeout';event['failed_tool']='physical-workflow'
        event['native_eda_workflow_started']=True;write_json(event_path,event)
        timed=summarize(root,require_complete=False)
        assert timed['infrastructure_aborted_sessions']==1 and timed['normally_finished_sessions']==0
        assert timed['rows'][0]['execution_interruption']['type']=='physical-workflow-timeout'
        before=(root/'ppa/analysis.json').read_bytes()
        event['terminal_summary_sha256']='0'*64;write_json(event_path,event)
        try:summarize(root,require_complete=False)
        except ValueError:pass
        else:raise AssertionError('An interruption was attached to a different terminal result')
        assert (root/'ppa/analysis.json').read_bytes()==before
        event_path.unlink()
        try:summarize(root,require_complete=False)
        except ValueError:pass
        else:raise AssertionError('An incomplete terminal slot was counted as normal completion')
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);observed=copy.deepcopy(summary)
        observed['budget']['dispatches'][0]['attempt']='failed-request'
        event={'type':'post-response-model-transport-failure','job':observed['job']['id'],
            'failed_role_attempts':[{'attempt':'failed-request','role_seconds':20,'reported_usage_available':False}],
            'failed_role_seconds':20,'already_included_in_session_agent_and_wall_seconds':True}
        event_path=root/'infrastructure-failures/model-transport-01.json';write_json(event_path,event)
        notes=service_notes(root,observed)
        assert notes['unreported_transport_requests']==1 and notes['transport_failure_agent_seconds']==20
        assert dict(session_row(observed),**notes)['agent_seconds']==30, 'Transport time was added to an inclusive budget'
        event['failed_role_attempts'][0]['role_seconds']=21;event['failed_role_seconds']=21;write_json(event_path,event)
        try:service_notes(root,observed)
        except ValueError:pass
        else:raise AssertionError('Transport time differing from its actual role dispatch accepted')
        event['failed_role_attempts'][0]['role_seconds']=20;event['failed_role_seconds']=40
        event['failed_role_attempts']*=2;write_json(event_path,event)
        try:service_notes(root,observed)
        except ValueError:pass
        else:raise AssertionError('Duplicate failed request counted twice')
        event['failed_role_attempts']=event['failed_role_attempts'][:1];event['failed_role_seconds']=20;write_json(event_path,event)
        failed=copy.deepcopy(candidate);failed.update(rank_eligible=False,cell_area_um2=None,energy_j={})
        failed.pop('score');failed.pop('energy_ratio');observed['candidates']=[failed]
        evaluation=root/'ppa'/observed['job']['id']/'candidates/01/evaluation.json';write_json(evaluation,failed)
        physical_event={'type':'physical-stage-environment-failure','job':observed['job']['id'],
            'candidate_index':1,'evaluation_sha256':digest(evaluation),'failed_tool':'yosys',
            'already_included_in_session_wall_seconds':True}
        write_json(root/'infrastructure-failures/candidate-physical-01.json',physical_event)
        notes=service_notes(root,observed)
        assert len(notes['candidate_environment_failures'])==1 and notes['unreported_transport_requests']==1
        evaluation.write_text('{}')
        try:service_notes(root,observed)
        except ValueError:pass
        else:raise AssertionError('Environment annotation accepted for different candidate bytes')
    print('STUDY_EXTENSIONS_SELF_CHECK_PASS: representative/absence rules; portable endpoint clocks; source-bound interruptions and inclusive service costs without duplicate requests')


if __name__=='__main__':run()
