"""Keep unrounded targets and failed sessions visible in study summaries."""
import json
import tempfile
from pathlib import Path

from study_protocol import write_json
from summarize_benchmark_study import summarize,high_frequency


def run():
    with tempfile.TemporaryDirectory(prefix='chip-study-summary-') as temp:
        root=Path(temp)
        jobs=[dict(id=f'{flow}-{i}',workflow=flow,repetition=i) for i in range(1,4) for flow in ('F0','F1','F2')]
        write_json(root/'protocol.json',dict(ppa_jobs=jobs,demonstrations=['counter8','fifo8x4','dot2']))
        write_json(root/'launch-ledger.json',dict(limits={},launches=[]))
        baseline=dict(score=1.,energy_ratio=1.,candidate_index=0,cell_area_um2=100.,rank_eligible=True)
        for flow in ('F0','F1'):
            path=root/'ppa'/(flow+'-1')/'results/search-summary.json'
            if flow=='F0':
                candidates=[dict(candidate_index=1,rank_eligible=True,score=.9800000001,energy_ratio=1.,cell_area_um2=98.,
                    failure_classes=[],elapsed_search_seconds=10.),dict(candidate_index=2,rank_eligible=True,score=.98,energy_ratio=1.,cell_area_um2=98.,
                    failure_classes=[],elapsed_search_seconds=20.),dict(candidate_index=3,rank_eligible=False,failure_classes=['electrical'],elapsed_search_seconds=30.)]
                best=candidates[1]
            else:
                candidates=[dict(candidate_index=i,rank_eligible=False,failure_classes=['infrastructure'],elapsed_search_seconds=i*10.) for i in (1,2,3)]
                best=baseline
            write_json(path,dict(workflow_state='complete',candidates=candidates,accepted_candidates=3,unused_candidate_slots=0,best_including_start=best,elapsed_seconds=31.,
                budget=dict(used_agent_seconds=8.,dispatches=[dict(role='ppa-verifier')] if flow=='F1' else []),usage=dict(tokens=None)))
        data=summarize(root)
        f0=next(r for r in data['rows'] if r['job']['id']=='F0-1')
        f1=next(r for r in data['rows'] if r['job']['id']=='F1-1')
        assert f0['thresholds']['Q_lt_1']['candidate_slots']==1
        assert f0['thresholds']['Q_le_098']['candidate_slots']==2
        assert all(not r['reached'] and r['censored'] and r['seconds'] is None for r in f1['thresholds'].values())
        assert f1['best_including_start']['score']==1. and f1['tokens'] is None
        assert not data['ppa_complete'] and data['missing_required_evidence']
        assert sum(r['terminal'] for r in data['rows'])==2 and len(data['rows'])==9
        path=root/'ppa/F1-1/results/search-summary.json';partial=json.loads(path.read_text())
        partial['usage']=dict(model_sessions=1,tokens=dict(input_tokens=100,cached_input_tokens=50,output_tokens=10,reasoning_output_tokens=3))
        partial['budget']['dispatches'].append(dict(role='ppa-optimizer'))
        write_json(path,partial)
        incomplete=next(r for r in summarize(root)['rows'] if r['job']['id']=='F1-1')
        assert incomplete['tokens'] is None and incomplete['reported_tokens']['input_tokens']==100
        assert not incomplete['token_coverage']['all_dispatches_have_session_usage']
        assert incomplete['token_coverage']['budgeted_role_dispatches']==2
        assert not high_frequency(root)['finished']
        write_json(root/'high-frequency/selection.json',dict(rule='frozen selection',entries=[dict(identity='high-frequency-common')]))
        assert not high_frequency(root)['finished']
        write_json(root/'high-frequency/high-frequency-common/campaign-evaluation.json',
                   dict(rank_eligible=False,error_class='TimeoutError',error='synthetic retained timeout'))
        high=high_frequency(root)
        assert high['finished'] and high['rows'][0]['failure_classes']==['TimeoutError']
        assert high['absent_workflows']==['F0','F1','F2']
        write_json(root/'launch-ledger.json',dict(limits={},launches=[
            dict(identity='failed-ref',category='reference',status='failed',evidence='failed-ref.json'),
            dict(identity='qualified-ref',category='preformal_calibration',status='qualified',evidence='qualified-ref.json'),
            dict(identity='pending-supplement',category='reference_supplement',status='allocated')]))
        write_json(root/'failed-ref.json',dict(total_seconds=2.))
        write_json(root/'qualified-ref.json',dict(total_seconds=3.))
        prep=summarize(root)['preparation']
        assert prep['reference_and_calibration_attempts']==3
        assert prep['reference_and_calibration_terminal_attempts']==2
        assert prep['reference_and_calibration_seconds']==5., 'Failed preparation must consume measured cost'
        write_json(root/'failed-ref.json',{})
        assert summarize(root)['preparation']['reference_and_calibration_seconds'] is None, 'Missing duration must remain unknown'
    print('BENCHMARK_SUMMARY_SELF_CHECK_PASS: unrounded thresholds, failed/censored endpoints, unknown usage, incomplete schedule and failed preparation costs retained')


if __name__=='__main__':run()
