"""Collect the one completed F0 HF attempt after its observing coordinator exited."""
import datetime
import fcntl
import json
import sqlite3
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT.parents[1]/'CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU'
sys.path.insert(0,str(CASE/'scripts'))
from campaign_budget import finish
from classify_study_failures import classify,read_reports
from collect_physical import collect
from evaluate_study_physical import evaluate
from study_protocol import digest,write_json


def main():
    with (ROOT/'.coordinator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        frozen=json.loads((ROOT/'ppa/formal-freeze.json').read_text())
        for relative,sha in frozen['helpers'].items():assert digest(CASE/relative)==sha
        assert digest(ROOT/'protocol.json')==frozen['protocol_sha256']
        ledger=json.loads((ROOT/'launch-ledger.json').read_text())
        active=[row for row in ledger['launches'] if row['status']=='allocated']
        assert len(active)==1 and active[0]['identity']=='high-frequency-F0'
        output=ROOT/active[0]['output'];project=output/'project'
        assert not any((output/name).exists() for name in ('summary.json','evaluation.json','campaign-evaluation.json','evidence'))
        db=project/'.chip_nebula/shared/memory/taskgraph-v2.db'
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
            attempts=[json.loads(row[0]) for row in connection.execute('SELECT document FROM attempts')]
            assert len(attempts)==1
            attempt=attempts[0]
            assert attempt['status']=='succeeded' and attempt['verdict']=='pass'
            assert connection.execute('SELECT status FROM workflows').fetchone()[0]=='complete'
            artifacts=[json.loads(row[0]) for row in connection.execute("SELECT document FROM artifacts WHERE type='physical.report'")]
            assert len(artifacts)==1 and artifacts[0]['payload']['verdict']=='passed'
            artifact=artifacts[0]
            assert artifact['content']['commit']==attempt['workspace_commit']
        assert (output/'workflow.log').read_text().strip()=='Static Task Graph study-physical: complete'
        start=datetime.datetime.fromisoformat(attempt['created_at'])
        end=datetime.datetime.fromisoformat(attempt['finished_at'])
        elapsed=(end-start).total_seconds()
        assert 0<elapsed<14400
        manifest=json.loads((output/'manifest.json').read_text())
        selection=next(row for row in json.loads((ROOT/'high-frequency/selection.json').read_text())['entries']
                       if row['identity']=='high-frequency-F0')
        delivery=json.loads((ROOT/selection['source']/'selected-delivery.json').read_text())
        assert manifest['configuration']==selection['configuration']
        assert manifest['rtl_sha256']==delivery['exported_source_sha256']
        assert manifest['period_ps']==10000 and manifest['threads']==2
        unchanged=(digest(project/'physical/chip-nebula/constraints.sdc')==manifest['sdc_sha256']
                   and digest(project/'physical/chip-nebula/config.mk')==manifest['config_sha256']
                   and all(digest(project/name)==sha for name,sha in manifest['rtl_sha256'].items()))
        assert unchanged
        recovery=dict(recovered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            reason='The coordinator observer is no longer present; its single native physical attempt completed and committed before collection.',
            original_observer_state=json.loads((output/'state.json').read_text()),
            attempt_id=attempt['id'],artifact_id=artifact['id'],artifact_commit=artifact['content']['commit'],
            taskgraph_created_at=attempt['created_at'],taskgraph_finished_at=attempt['finished_at'],
            physical_wall_seconds_basis='Recovered TaskGraph UTC timestamp span; original coordinator monotonic process duration unavailable.',
            original_observer_wall_seconds=None,original_cli_exit_code=None,native_taskgraph_wall_seconds=elapsed,
            model_calls=0,new_full_physical_calls=0,attempts_before=1,
            scope='Resume collection and first postprocessing of the original immutable result, with identical gates; no physical rerun, repair or changed selection.')
        write_json(output/'collection-recovery.json',recovery)
        collect(project,'study-physical',output/'evidence',include_operators=True)
        raw,native,errors=read_reports(output/'evidence')
        row=dict(physical_finished=True,exit_code=None,timed_out=False,physical_wall_seconds=elapsed,
            physical_wall_seconds_basis=recovery['physical_wall_seconds_basis'],configuration=manifest['configuration'],
            physical_qualified=True,rank_eligible=False,failure_classes=errors,manifest=manifest,
            task_state='satisfied',attempts=[dict(id=attempt['id'],status='succeeded',failure='')],
            metrics=native.get('metrics',{}),
            electrical_violations={k:raw.get('finish__timing__drv__'+k) for k in ('max_slew','max_cap','max_fanout')},
            frozen_inputs_changed=False,frozen_inputs_unchanged=unchanged,
            completion_evidence='Single completed TaskGraph attempt and selected committed artifact; observer exit code unavailable.')
        row['failure_classes']=classify(row,raw,native)
        row['physical_qualified']=not row['failure_classes']
        write_json(output/'summary.json',row)
        write_json(output/'state.json',dict(state='physical_finished',summary='summary.json',recovery='collection-recovery.json'))
        result=evaluate(output)
        result.update(rtl_actions=delivery['rtl_actions'],collection_recovered=True,
                      physical_wall_seconds_basis=recovery['physical_wall_seconds_basis'],original_observer_wall_seconds=None)
        write_json(output/'campaign-evaluation.json',result)
        finish(ROOT,'high-frequency-F0',status='qualified' if result['rank_eligible'] else 'failed',
               evidence=str((output/'campaign-evaluation.json').relative_to(ROOT)))
        assert len(json.loads((ROOT/'launch-ledger.json').read_text())['launches'])==len(ledger['launches'])
        print(json.dumps(dict(recovered=True,rank_eligible=result['rank_eligible'],failure_classes=result['failure_classes'],
                             physical_calls_added=0,original_observer_wall_seconds=None),indent=2),flush=True)


if __name__=='__main__':main()
