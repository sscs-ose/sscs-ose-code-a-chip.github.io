"""Offline replay of public task checks, selected netlists, scores and optional power."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from benchmark_physical import postroute
from qualify_benchmark import qualify,simulate
from study_protocol import digest,score,ranking,write_json

CASE=Path(__file__).resolve().parents[1]


def verify_export(results):
    manifest=json.loads((results/'export-manifest.json').read_text());seen=set()
    for item in manifest['files']:
        path=results/item['path']
        if path.is_symlink() or not path.resolve().is_relative_to(results) or item['path'] in seen:
            raise ValueError('Unsafe or duplicate export path')
        seen.add(item['path'])
        if path.stat().st_size!=item['bytes'] or digest(path)!=item['sha256']:
            raise ValueError('Saved evidence changed: '+item['path'])
    return manifest


def audit_accounting(results,data):
    """Reconcile the execution ledger with the protocol and its explicit extension."""
    protocol=json.loads((results/'protocol.json').read_text())
    ledger=json.loads((results/'launch-ledger.json').read_text())
    limits=dict(protocol['physical_budget'])
    amendment_path=results/'budget-amendment.json'
    amendment=json.loads(amendment_path.read_text()) if amendment_path.exists() else None
    if amendment:
        assert amendment['owner_approved'] is True
        assert amendment['original_protocol_sha256']==digest(results/'protocol.json')
        assert amendment['original_limits']==limits
        assert amendment['original_absolute_total']==limits['absolute_total']==44
        assert amendment['amended_absolute_total']==45
        assert amendment['category']=='reference_supplement' and amendment['additional_attempts']==1
        assert amendment['task']=='dot4' and amendment['identity']=='reference-dot4-supplement'
        assert amendment['output']=='benchmark/reference-dot4-supplement'
        assert amendment['formal_search_replacement_allowed'] is False
        limits.update(absolute_total=45,reference_supplement=1)
    assert ledger['limits']==limits, 'Physical limits differ from the protocol and authorization'
    launches=ledger['launches'];identities=[row['identity'] for row in launches]
    assert len(identities)==len(set(identities)), 'Duplicate physical execution identity'
    categories={row['category'] for row in launches}
    assert categories<=set(limits)-{'planned_total','absolute_total'}
    counts={category:sum(row['category']==category for row in launches) for category in categories}
    assert len(launches)<=limits['absolute_total']
    assert all(count<=limits[category] for category,count in counts.items())
    assert sum(count for category,count in counts.items()
               if category not in ('preformal_calibration','reference_supplement'))<=limits['planned_total']
    ppa_outputs={job['id']+'-candidate-'+str(index):
                 f"ppa/{job['id']}/candidates/{index:02d}/physical"
                 for job in protocol['ppa_jobs'] for index in range(1,protocol['candidates_per_ppa_session']+1)}
    unfinished={row['job']['id'] for row in data['rows'] if not row['terminal']}
    deferred_receipts=[]
    for row in launches:
        assert row['status'] in ('allocated','qualified','failed')
        if row['category']=='ppa':
            assert row['identity'] in ppa_outputs and row['output']==ppa_outputs[row['identity']]
        if row['category']=='reference_supplement':
            assert amendment and row['identity']==amendment['identity'] and row['output']==amendment['output']
        if row['status']!='allocated':
            evidence=results/row['evidence']
            assert evidence.resolve().is_relative_to(results), 'Unsafe execution receipt path'
            if not evidence.is_file():
                # Draft exports deliberately omit every active session's mutable graph/evidence.
                assert row['category']=='ppa' and any(
                    row['identity'].startswith(job+'-candidate-') for job in unfinished), 'Missing execution receipt'
                deferred_receipts.append(row['identity'])
    accounting=data['physical_accounting']
    assert accounting['limits']==limits and accounting['launches']==launches
    assert accounting['allocated']==len(launches) and accounting['by_category']==counts
    assert accounting['terminal']==sum(row['status']!='allocated' for row in launches)
    for row in data['rows']:
        if not row['terminal']:continue
        accepted=[launch for launch in launches if launch['category']=='ppa'
                  and launch['identity'].startswith(row['job']['id']+'-candidate-')]
        assert {launch['identity'] for launch in accepted}=={
            row['job']['id']+'-candidate-'+str(index) for index in range(1,row['accepted_candidates']+1)}
        assert all(launch['status']!='allocated' for launch in accepted)
        assert row['agent_seconds'] is not None and row['agent_seconds']<=protocol['agent_budget_seconds']
    return dict(allocated=len(launches),limits=limits,by_category=counts,
                explicit_reference_extension=amendment is not None,
                unfinished_session_receipts_not_exported=deferred_receipts)


def audit_high_frequency(results,data):
    """Reconcile selected representatives and every terminal 100 MHz attempt."""
    high=data['high_frequency'];selection_path=results/'high-frequency/selection.json'
    if not selection_path.exists():
        assert not high['finished'] and high['selection_pending'] and not high['rows']
        return dict(selection_pending=True,attempts=[])
    assert data['ppa_complete'] and not high['selection_pending']
    protocol=json.loads((results/'protocol.json').read_text())
    expected=[dict(identity='high-frequency-common',source='public-released-design',
                   configuration=protocol['ppa']['baseline_configuration'])]
    sources={'high-frequency-common':CASE/'released_design'}
    for flow in ('F0','F1','F2'):
        candidates=[(candidate,row['job']['id']) for row in data['rows']
                    if row['job']['workflow']==flow for candidate in row['candidates']
                    if candidate['rank_eligible']]
        if not candidates:continue
        best,session=min(candidates,key=lambda item:(*ranking(item[0]),item[1]))
        relative=f'ppa/{session}/candidates/{best["candidate_index"]:02d}/source'
        identity='high-frequency-'+flow
        expected.append(dict(identity=identity,source=relative,configuration=best['configuration'],
                             selected_session=session,candidate_index=best['candidate_index']))
        sources[identity]=results/relative
    selection=json.loads(selection_path.read_text())
    assert selection['entries']==expected, 'High-frequency representatives differ from the frozen ranking rule'
    assert [row['selection'] for row in high['rows']]==expected
    assert high['finished']==all(row['terminal'] for row in high['rows'])
    assert high['absent_workflows']==[flow for flow in ('F0','F1','F2')
                                    if 'high-frequency-'+flow not in sources]
    sdc=('current_design nebula_cpu_npu_top\n'
         'create_clock -name nebula_clock -period 10 [get_ports {clk}]\n'
         'set_clock_uncertainty 0.1 [get_clocks nebula_clock]\n'
         'set_input_delay 0.5 -clock nebula_clock [get_ports {rst_n imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]\n'
         'set_output_delay 0.5 -clock nebula_clock [all_outputs]\n')
    sdc_sha=hashlib.sha256(sdc.encode()).hexdigest();audited=[]
    launches={row['identity']:row for row in data['physical_accounting']['launches']
              if row['category']=='high_frequency'}
    assert set(launches)<=set(sources), 'Unselected high-frequency attempt'
    for row in high['rows']:
        entry=row['selection'];identity=entry['identity'];source=sources[identity]
        delivery=json.loads((source/'selected-delivery.json').read_text())
        hashes=delivery['exported_source_sha256']
        assert hashes
        for relative,sha in hashes.items():
            path=source/relative
            assert not path.is_symlink() and path.resolve().is_relative_to(source.resolve()) and digest(path)==sha
        if identity=='high-frequency-common':
            assert hashes==data['baseline']['physical_manifest']['rtl_sha256']
        if not row['terminal']:
            assert row['evaluation'] is None
            continue
        root=results/'high-frequency'/identity
        saved=json.loads((root/'campaign-evaluation.json').read_text())
        assert row['evaluation']==saved, 'High-frequency summary differs from its raw evaluation'
        assert launches[identity]['status']==('qualified' if saved['rank_eligible'] else 'failed')
        assert launches[identity]['output']=='high-frequency/'+identity
        manifest_path=root/'manifest.json'
        manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        if saved['rank_eligible'] or saved.get('physical_manifest'):assert manifest
        if manifest:
            assert manifest['configuration']==entry['configuration'] and manifest['rtl_sha256']==hashes
            assert manifest['source_design_delivery']==delivery['id']
            assert manifest['period_ps']==10000 and manifest['threads']==2
            assert manifest['sdc_sha256']==sdc_sha and manifest['physical_timeout_seconds']==14400
            if saved.get('physical_manifest'):
                assert saved['physical_manifest']==manifest
                assert saved['configuration']==entry['configuration'] and saved['period_ps']==10000
        audited.append(dict(identity=identity,qualified=saved['rank_eligible'],
                            physical_manifest_checked=manifest is not None))
    return dict(selection_pending=False,representatives=len(expected),attempts=audited,
                scope='Unrounded representative selection, source bytes, configuration and 100 MHz constraints; failed attempts retained.')


def audit_workflows(results,data):
    """Connect configured role policy, captured approval and actual accepted execution."""
    frozen=json.loads((results/'ppa/formal-freeze.json').read_text())
    for relative,key in (('protocol.json','protocol_sha256'),
                         ('baseline/common/campaign-evaluation.json','baseline_sha256'),
                         ('checks/rtl-actions/admission.json','action_admission_sha256')):
        if digest(results/relative)!=frozen[key]:raise ValueError('Frozen experiment input changed: '+relative)
    if data['baseline']!=json.loads((results/'baseline/common/campaign-evaluation.json').read_text()):
        raise ValueError('Summary normalization input differs from the frozen common baseline')
    for name,expected in frozen['helpers'].items():
        if digest(CASE/name)!=expected or digest(results/'ppa/executed-sources'/name)!=expected:
            raise ValueError('Used execution source differs from formal freeze: '+name)
    role_signatures=set();audited=[]
    for row in data['rows']:
        if not row['terminal']:continue
        root=results/'ppa'/row['job']['id'];graph=json.loads((root/'taskgraph.json').read_text())
        signatures=tuple(digest(root/'configuration/.chip_nebula/roles'/(name+'.yaml'))
                         for name in ('ppa-optimizer','ppa-verifier'))
        role_signatures.add(signatures)
        assert row['accepted_candidates']<=3 and row['accepted_candidates']+row['unused_candidate_slots']==3
        indices=sorted(c['candidate_index'] for c in row['candidates'])
        if indices!=list(range(1,len(indices)+1)):
            raise ValueError('An unrecorded intermediate candidate must not be silently bypassed')
        previous_failed=True
        for candidate in sorted(row['candidates'],key=lambda c:c['candidate_index']):
            flow=row['job']['workflow']
            expected=flow=='F1' or flow=='F2' and previous_failed
            slot=root/'candidates'/f'{candidate["candidate_index"]:02d}'
            launch=json.loads((slot/'launch.json').read_text())
            if launch['review_required']!=expected or candidate['review_required']!=expected:
                raise ValueError('Executed review policy differs: '+row['job']['id'])
            if expected:
                approvals=[a for a in graph['attempts'] if a['task_id']=='workflow-ppa:reviewer'
                           and a['input_deliveries'].get('candidate')==candidate['candidate_artifact']
                           and a['verdict'] in ('pass','passed')]
                if not approvals:raise ValueError('Accepted reviewed candidate has no captured approval')
            source=slot/'source';delivery=json.loads((source/'selected-delivery.json').read_text())
            assert digest(source/'selected-delivery.json')==candidate['source_delivery_sha256']
            for relative,sha in delivery['exported_source_sha256'].items():
                path=source/relative
                assert path.resolve().is_relative_to(source) and not path.is_symlink() and digest(path)==sha
            manifest=candidate.get('physical_manifest')
            if candidate['rank_eligible']:assert manifest, 'Qualified candidate lacks its physical input manifest'
            # Failed physical attempts must also use the declared source and conditions.
            if manifest:
                assert manifest['rtl_sha256']==delivery['exported_source_sha256']
                for key in ('period_ps','threads','sdc_sha256'):
                    assert manifest[key]==data['baseline']['physical_manifest'][key]
            previous_failed=not candidate['rank_eligible']
        if row['job']['workflow']=='F0':assert row['reviews']==0
        expected=min([data['baseline'],*[c for c in row['candidates'] if c['rank_eligible']]],key=ranking)
        assert ranking(expected)==ranking(row['best_including_start'])
        audited.append(dict(session=row['job']['id'],accepted=row['accepted_candidates'],review_policy_verified=True,
                            physical_manifests_checked=sum(bool(c.get('physical_manifest')) for c in row['candidates']),
                            best_qualified_incumbent_retained=True))
    if len(role_signatures)>1:raise ValueError('Optimizer/reviewer roles differ between scored sessions')
    return dict(frozen_execution_files=len(frozen['helpers']),sessions=audited,
        physical_accounting=audit_accounting(results,data),
        high_frequency=audit_high_frequency(results,data),
        scope='Independent links between role configuration, captured review attempts, accepted source, common constraints and retained best result. Physical manifests are checked for failed as well as qualified attempts when present.')


def first_per_workflow(data):
    """Earliest qualified repetition/candidate; measured PPA never selects the replay."""
    selected=[]
    for workflow in sorted({row['job']['workflow'] for row in data['rows']}):
        eligible=[(row['job']['repetition'],candidate['candidate_index'],row['job']['id'],candidate)
                  for row in data['rows'] if row['job']['workflow']==workflow
                  for candidate in row['candidates'] if candidate['rank_eligible']]
        if eligible:
            _,_,session,candidate=min(eligible,key=lambda item:item[:3])
            selected.append((candidate,session))
    return selected


def run(results,output,*,measurement='none',allow_incomplete=False):
    results,output=Path(results).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Choose a new replay directory; previous checks are retained')
    manifest=verify_export(results)
    if not manifest['complete'] and not allow_incomplete:raise ValueError('Final replay requires a complete exported campaign')
    output.mkdir(parents=True)
    data=json.loads((results/'analysis.json').read_text());rows=[]
    workflow_audit=audit_workflows(results,data)
    for row in data['benchmark']['rows']:
        label=row['task']['id'];task=results/'benchmark/tasks'/label
        local=qualify(task,output/'tasks'/label)
        assert local['local_qualified']
        receipt=dict(task=label,reference_and_mutants=True,physical_record_qualified=row['reference_gds'])
        if row['reference_gds']:
            # Fresh simulation of the delivered routed netlist with the current held-out grader.
            reference=results/row['reference']
            gate=postroute(task,reference/'evidence',output/'netlists'/label)
            assert gate['passed'];receipt['postroute_replayed']=True
        rows.append(receipt)
    for row in data['demonstrations']:
        label=row['task'];saved=row['frontend']
        if not saved:continue
        if not saved['functional_qualified']:
            rows.append(dict(demonstration=label,original_failed=True,passed=True,
                             scope='Original failure retained, no repair or replacement'))
            continue
        selected=results/'benchmark/demonstrations'/label/'results/selected'
        for name,expected in saved['source_sha256'].items():
            if digest(selected/name)!=expected:raise ValueError('Selected RTL changed')
        task=results/'benchmark/tasks'/label
        check=simulate([selected/p for p in saved['source_sha256']],task/'grader/acceptance_tb.sv',
                       output/'demonstrations'/label)
        assert check['passed']
        rows.append(dict(demonstration=label,independent_function_replayed=True))
    baseline=data['baseline'];ranked=[]
    for row in data['rows']:
        for candidate in row['candidates']:
            if not candidate['rank_eligible']:continue
            recalculated=score(candidate['cell_area_um2'],candidate['energy_j'],
                               baseline['cell_area_um2'],baseline['energy_j'])
            for key,value in recalculated.items():
                if not math.isclose(value,candidate[key],rel_tol=1e-12,abs_tol=1e-14):
                    raise ValueError('Saved comparative score differs: '+row['job']['id']+'/'+key)
            ranked.append((candidate,row['job']['id']))
    measurements=[]
    if measurement!='none':
        if baseline is None or not baseline['rank_eligible']:raise ValueError('No qualified common baseline to remeasure')
        targets=[('common',results/'baseline/common',baseline)]
        if measurement in ('best','all','first-per-workflow') and ranked:
            chosen=(first_per_workflow(data) if measurement=='first-per-workflow' else
                    ranked if measurement=='all' else [min(ranked,key=lambda item:(item[0]['score'],item[1],item[0]['candidate_index']))])
            for candidate,session in chosen:
                targets.append((session+'-'+str(candidate['candidate_index']),
                    results/'ppa'/session/'candidates'/f'{candidate["candidate_index"]:02d}'/'physical',candidate))
        for name,source,saved in targets:
            destination=output/'measurement'/name
            with (output/(name+'-measurement.log')).open('w') as log:
                subprocess.run([sys.executable,str(CASE/'scripts/run_postroute_workloads.py'),'--source',str(source/'evidence'),
                    '--output',str(destination),'--period-ps',str(saved['period_ps'])],
                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
                subprocess.run([sys.executable,str(CASE/'scripts/check_postroute_waveforms.py'),str(destination),
                    '--output',str(destination/'waveform-audit.json')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            measured=json.loads((destination/'summary.json').read_text());assert measured['measurement_qualified']
            for workload in measured['rows']:
                if not math.isclose(workload['estimated_energy_j'],saved['energy_j'][workload['workload']],rel_tol=1e-9,abs_tol=1e-18):
                    raise ValueError('Independent saved-netlist energy replay differs: '+name+'/'+workload['workload'])
            measurements.append(dict(name=name,passed=True,period_ps=saved['period_ps']))
    record=dict(passed=True,complete_campaign=manifest['complete'],tasks=rows,comparative_scores_recomputed=len(ranked),
        measurements=measurements,workflow_audit=workflow_audit,model_calls=0,full_physical_calls=0,
        scope='New functional/netlist checks and arithmetic score verification. Optional measurement reruns candidate-bound workloads and OpenSTA, not synthesis or place-and-route. Original failures retained.')
    write_json(output/'replay.json',record);print('OFFLINE_BENCHMARK_REPLAY_PASS',flush=True)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,default=CASE/'results/benchmark-study')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--measurement',choices=['none','common','best','all','first-per-workflow'],default='none',
                        help='Optional model-account-free power replay; best/all also include the common baseline')
    parser.add_argument('--allow-incomplete',action='store_true',help='Development check only; retain incomplete campaign status')
    args=parser.parse_args();run(args.results,args.output,measurement=args.measurement,allow_incomplete=args.allow_incomplete)
