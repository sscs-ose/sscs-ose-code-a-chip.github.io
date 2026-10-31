"""Summarize all frozen workflow sessions, including failure and unreached endpoints."""
from __future__ import annotations

import argparse
import datetime
import json
import statistics
from pathlib import Path

from study_protocol import digest,ranking,write_json


def high_frequency(campaign):
    """Selected-but-not-finished is pending; unselected workflows are absent."""
    path=campaign/'high-frequency/selection.json'
    if not path.exists():return dict(finished=False,selection_pending=True,rows=[])
    selection=json.loads(path.read_text());rows=[]
    identities=[entry['identity'] for entry in selection['entries']]
    if len(identities)!=len(set(identities)) or 'high-frequency-common' not in identities or len(identities)>4:
        raise ValueError('High-frequency selection must retain one common start and at most three distinct workflow representatives')
    for entry in selection['entries']:
        result=campaign/'high-frequency'/entry['identity']/'campaign-evaluation.json'
        measured=json.loads(result.read_text()) if result.exists() else None
        failures=list(measured.get('failure_classes',[])) if measured else []
        if measured and not measured['rank_eligible'] and not failures:
            failures=[measured.get('error_class','unqualified_reason_unavailable')]
        rows.append(dict(selection=entry,terminal=measured is not None,evaluation=measured,failure_classes=failures))
    selected={row['selection']['identity'] for row in rows}
    record=dict(finished=all(row['terminal'] for row in rows),selection_pending=False,
        rule=selection['rule'],rows=rows,
        absent_workflows=[flow for flow in ('F0','F1','F2') if 'high-frequency-'+flow not in selected],
        scope='One 100 MHz attempt per selected representative. Qualification is measured at 100 MHz; self-normalized legacy Q is not a cross-clock improvement.')
    write_json(campaign/'high-frequency/summary.json',record)
    return record


def known_sum(values):
    values=list(values)
    return sum(values) if values and all(value is not None for value in values) else None


def benchmark_status(campaign,protocol):
    """Recompute from reference receipts; an old progress label is not qualification."""
    if not protocol.get('tasks'):
        path=campaign/'benchmark/qualification.json'
        return json.loads(path.read_text()) if path.exists() else None
    rows=[]
    for task in protocol['tasks']:
        root=campaign/'benchmark/tasks'/task['id']
        local_path=root/'qualification-v2/qualification.json'
        if not local_path.exists():local_path=root/'qualification/qualification.json'
        local=json.loads(local_path.read_text()) if local_path.exists() else {}
        calibration=json.loads((root/'calibration.json').read_text()) if (root/'calibration.json').exists() else None
        measured=None;postroute=False
        if calibration:
            measured=json.loads((campaign/calibration['reference_output']/'qualification.json').read_text())
            checker=digest(root/'grader/acceptance_tb.sv')
            postroute_record=measured.get('postroute') or {}
            postroute=postroute_record.get('passed',False) and postroute_record.get('checker_sha256')==checker
            if not postroute:
                upgrade=campaign/'checks/checker-revision-v2'/task['id']/'postroute-v2/result.json'
                revised=json.loads(upgrade.read_text()) if upgrade.exists() else {}
                postroute=revised.get('passed',False) and revised.get('checker_sha256')==checker
            assert calibration['after']['area_limit_um2']==1.25*measured['cell_area_um2']
        valid=bool(local.get('local_qualified') and measured and measured['qualified'] and postroute)
        rows.append(dict(task=task,local_checks=bool(local.get('local_qualified')),
            mutants_rejected=sum(r['detected'] for r in local.get('mutants',{}).values()),
            reference=calibration['reference_output'] if calibration else None,
            reference_gds=valid,postroute=postroute,
            cell_area_um2=measured.get('cell_area_um2') if measured else None,
            area_limit_um2=calibration['after']['area_limit_um2'] if calibration else None,
            qualification_path=str(local_path.relative_to(campaign))))
    return dict(qualified=all(r['reference_gds'] for r in rows),families=3,variants=len(rows),
                qualified_variants=sum(r['reference_gds'] for r in rows),rows=rows)


def summarize(campaign):
    campaign=Path(campaign).resolve()
    protocol=json.loads((campaign/'protocol.json').read_text())
    ledger=json.loads((campaign/'launch-ledger.json').read_text())
    baseline_path=campaign/'baseline/common/campaign-evaluation.json'
    baseline=json.loads(baseline_path.read_text()) if baseline_path.exists() else None
    rows=[]
    for job in protocol['ppa_jobs']:
        root=campaign/'ppa'/job['id'];path=root/'results/search-summary.json'
        if not path.exists():
            rows.append(dict(job=job,terminal=False,status='not_started' if not root.exists() else 'running_or_interrupted',candidates=[]))
            continue
        summary=json.loads(path.read_text())
        if 'workflow_state' not in summary:
            rows.append(dict(job=job,terminal=False,status='finalizing_worker_receipt',candidates=[]))
            continue
        candidates=summary['candidates']
        assert len(candidates)<=3 and summary['accepted_candidates']<=3
        assert len({r['candidate_index'] for r in candidates})==len(candidates)
        eligible=[r for r in candidates if r['rank_eligible']]
        assert all(r.get('score',0)>0 and not r.get('failure_classes') for r in eligible)
        tokens=summary.get('usage',{}).get('tokens')
        if tokens:
            assert 0<=tokens['cached_input_tokens']<=tokens['input_tokens']
        threshold={}
        for name,criterion in [('new_qualified',lambda r:True),('Q_lt_1',lambda r:r['score']<1),('Q_le_098',lambda r:r['score']<=.98)]:
            matching=[r for r in eligible if criterion(r)]
            first=min(matching,key=lambda r:r['candidate_index']) if matching else None
            threshold[name]=dict(reached=first is not None,seconds=first.get('elapsed_search_seconds') if first else None,
                candidate_slots=first['candidate_index'] if first else None,censored=first is None)
        budget=summary.get('budget',{})
        rows.append(dict(job=job,terminal=True,workflow_state=summary.get('workflow_state'),candidates=candidates,
            accepted_candidates=summary['accepted_candidates'],unused_candidate_slots=summary['unused_candidate_slots'],
            new_qualified=len(eligible),best_new=min(eligible,key=ranking) if eligible else None,
            best_including_start=summary['best_including_start'],total_seconds=summary['elapsed_seconds'],
            agent_seconds=budget.get('used_agent_seconds'),tokens=tokens,thresholds=threshold,
            reviews=sum(r['role']=='ppa-verifier' for r in budget.get('dispatches',[])),
            model_dispatches=len(budget.get('dispatches',[])),summary_sha256=digest(path)))
        rows[-1]['coordination']=summary.get('coordination')
        reported_sessions=summary.get('usage',{}).get('model_sessions')
        covered=(type(reported_sessions) is int and reported_sessions==len(budget.get('dispatches',[])))
        rows[-1]['reported_tokens']=tokens
        rows[-1]['token_coverage']=dict(reported_model_sessions=reported_sessions,
            budgeted_role_dispatches=len(budget.get('dispatches',[])),all_dispatches_have_session_usage=covered,
            scope='Terminal cumulative CLI session usage, not an independently observed provider bill. Failed connection time is charged even when Tokens are unavailable.')
        if not covered:rows[-1]['tokens']=None
        rows[-1]['eda_seconds']=known_sum(c.get('physical_wall_seconds') for c in candidates)
        rows[-1]['postprocess_seconds']=known_sum(c.get('postprocess_wall_seconds') for c in candidates)
        rows[-1]['accepted_evaluation_seconds']=known_sum(c.get('total_wall_seconds') for c in candidates)
        if not summary['accepted_candidates']:
            rows[-1].update(eda_seconds=0,postprocess_seconds=0,accepted_evaluation_seconds=0)
        rows[-1]['candidate_failures']=summary['accepted_candidates']-len(eligible)
        rows[-1]['incomplete_accepted_candidates']=summary['accepted_candidates']-len(candidates)
        rows[-1]['manual_interventions']=0
    groups=[]
    for flow in ('F0','F1','F2'):
        trials=[r for r in rows if r['job']['workflow']==flow];finished=[r for r in trials if r['terminal']]
        groups.append(dict(workflow=flow,scheduled=len(trials),terminal=len(finished),
            sessions_with_new_qualified=sum(r['new_qualified']>0 for r in finished),
            qualified_candidates=sum(r['new_qualified'] for r in finished),
            accepted_candidates=sum(r['accepted_candidates'] for r in finished),
            median_incumbent_Q=statistics.median(r['best_including_start']['score'] for r in finished) if finished else None,
            median_wall_seconds=statistics.median(r['total_seconds'] for r in finished) if finished else None,
            total_reviews=sum(r['reviews'] for r in finished),
            threshold_reached={key:sum(r['thresholds'][key]['reached'] for r in finished) for key in ('new_qualified','Q_lt_1','Q_le_098')}))
        group=groups[-1]
        for field in ('agent_seconds','eda_seconds','postprocess_seconds'):
            values=[r[field] for r in finished]
            group['median_'+field]=statistics.median(values) if values and all(v is not None for v in values) else None
        group['tokens']=({key:known_sum(r['tokens'].get(key) for r in finished)
                         for key in finished[0]['tokens']}
                        if finished and all(r['tokens'] is not None for r in finished) else None)
        group['candidate_failures']=sum(r['candidate_failures'] for r in finished)
        group['review_rejections']=known_sum((r.get('coordination') or {}).get('review_rejections') for r in finished)
    benchmark=benchmark_status(campaign,protocol)
    demonstration=[]
    for name in protocol['demonstrations']:
        path=campaign/'benchmark/demonstrations'/name/'results/result.json'
        physical=path.parent.parent/'physical/qualification.json'
        frontend=json.loads(path.read_text()) if path.exists() else None
        demonstration.append(dict(task=name,frontend_terminal=frontend is not None,
             terminal=bool(frontend and (not frontend['functional_qualified'] or physical.exists())),frontend=frontend,
             physical=json.loads(physical.read_text()) if physical.exists() else None))
    action_path=campaign/'checks/rtl-actions/qualification.json'
    actions=json.loads(action_path.read_text()) if action_path.exists() else {}
    reference_launches=[r for r in ledger['launches']
                       if r['category'] in ('reference','preformal_calibration','reference_supplement')]
    reference_costs=[]
    for launch in reference_launches:
        if launch['status']=='allocated':continue
        evidence=campaign/launch.get('evidence','not-yet-written')
        receipt=json.loads(evidence.read_text()) if evidence.is_file() else {}
        reference_costs.append(dict(identity=launch['identity'],category=launch['category'],
            status=launch['status'],seconds=receipt.get('total_seconds')))
    preparation=dict(task_construction_seconds=known_sum(json.loads((campaign/'benchmark/tasks'/t['id']/'build.json').read_text()).get('created_seconds')
                     for t in protocol.get('tasks',[])),
        formal_action_proof_seconds=actions.get('preparation_seconds'),
        action_cpu_integration_seconds=None,
        baseline_total_seconds=baseline.get('total_wall_seconds') if baseline else None,
        reference_and_calibration_attempts=len(reference_launches),
        reference_and_calibration_terminal_attempts=len(reference_costs),
        reference_and_calibration_seconds=known_sum(r['seconds'] for r in reference_costs),
        reference_and_calibration_costs=reference_costs,
        scope='Shared curation, correctness preparation and common baseline are outside scored sessions. Unrecorded preparation wall time remains unknown, not zero.')
    data=dict(schema_version=1,title='ChipWave: A Configurable Platform for AI-Driven Chip Design and PPA Exploration',
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ppa_complete=all(r['terminal'] for r in rows),
        benchmark=benchmark,baseline=baseline,rows=rows,groups=groups,demonstrations=demonstration,preparation=preparation,
        high_frequency=high_frequency(campaign),
        physical_accounting=dict(limits=ledger['limits'],allocated=len(ledger['launches']),
            by_category={category:sum(r['category']==category for r in ledger['launches']) for category in sorted({r['category'] for r in ledger['launches']})},
            terminal=sum(r['status']!='allocated' for r in ledger['launches']),launches=ledger['launches']),
        protocol_sha256=digest(campaign/'protocol.json'),
        scope='Three repetitions per workflow, descriptive only; all endpoints retain nonattainment. Task validity is separate from agent success.',
        missing_required_evidence=[] if benchmark and benchmark['qualified'] else ['Six-task reference physical qualification incomplete'])
    write_json(campaign/'analysis.json',data)
    print(json.dumps(dict(ppa_terminal=sum(r['terminal'] for r in rows),ppa_scheduled=9,benchmark_qualified=bool(benchmark and benchmark['qualified']),allocated_physical_slots=len(ledger['launches'])),indent=2))
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--campaign',type=Path,required=True)
    summarize(parser.parse_args().campaign)
