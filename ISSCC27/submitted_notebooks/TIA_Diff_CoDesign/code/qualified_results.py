"""Assemble TIA responses and figures from a qualified search or submitted design."""
from environment import ROOT,CODE,configure
configure()
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
import workflow as W
from features14 import FEATURE_KEYS,physical14_features
from joint_passives import joint_geometry


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(proposal_path,search_record,qualification):
    proposal_path=Path(proposal_path).resolve();qualification=Path(qualification).resolve()
    proposal=W.read(proposal_path)
    if search_record is None:
        if proposal.get('proposal_role')!='submitted_final_design' or 'stage_contract' in proposal:
            raise ValueError('A search record is required for an optimizer proposal')
        progress=dict(initialization='submitted_final_design',selected_stage=None)
    else:
        progress=W.read(search_record)
    q=W.read(qualification/'final_design.json');provenance=W.read(qualification/'qualification_inputs.json')
    if q.get('strict_feasible') is not True:raise ValueError('Independent qualification has not passed')
    if (q['qualification_inputs_sha256']!=sha(qualification/'qualification_inputs.json')
            or provenance['proposal_sha256']!=sha(proposal_path)):
        raise ValueError('Proposal and qualification identities disagree')
    if search_record is not None:
        from staged_search import STARTUP_TRIALS
        mode=progress.get('initialization')
        if (mode not in ('random','conditional_warm') or progress.get('startup_trials')!=STARTUP_TRIALS
                or progress.get('selected_stage')!=proposal['stage_contract']['stage']
                or progress.get('plan_sha256')!=proposal['stage_contract']['plan_sha256']):
            raise ValueError('Search initialization, stage or plan identity disagrees with the proposal')
        if mode=='conditional_warm':
            initialization=proposal.get('initialization',{})
            if initialization.get('method')!=mode or initialization.get('failed_random_starts')!=5:
                raise ValueError('Conditional restart is missing its five-failure gate')
            for key,value in initialization['binding'].items():
                if proposal['stage_contract'].get(key)!=value:raise ValueError('Conditional restart source binding changed')
    spirals=joint_geometry(proposal)
    if spirals is None or spirals!=q['spiral_geometries']:
        raise ValueError('Qualified spiral geometry does not match the joint proposal')
    if (q['geometry']!=proposal['geometry'] or q['params']!=proposal['params']
            or provenance['joint_binding_sha256']!=proposal['joint_binding_sha256']
            or provenance['stage_contract']!=proposal.get('stage_contract')):
        raise ValueError('Qualified geometry, circuit parameters or stage contract changed')
    for tag,suffix in (('transformer','.s4p'),('L1','.s2p'),('LB','.s2p')):
        network=qualification/(tag+suffix);gds=qualification/(tag+'.gds')
        metadata=W.read(qualification/(tag+'.json'))
        if (sha(network)!=provenance['network_sha256'][tag] or sha(network)!=metadata['response_sha256']
                or sha(gds)!=metadata['gds_sha256']):
            raise ValueError('A qualified passive network or GDS changed: '+tag)
    import active_constraint_search as A
    import terminal_policy as TP
    import vce_policy as V
    TP.require_markers(proposal);TP.require_integer_geometry(proposal['geometry'])
    values=np.asarray(proposal['constraints'],float)
    if (values.shape!=(16,) or not np.isfinite(values).all() or np.any(values>0)
            or proposal['metrics_surrogate']['bw_ghz']<34.):
        raise ValueError('The proposal fails surrogate acceptance')
    audit=V.audit_op(q['metrics_em']['op'],V.policy_from_pdk(CODE,search_buffer_v=.001))
    if not W.accepted_circuit(proposal['params'],q['metrics_em'],audit):
        raise ValueError('The independently qualified circuit violates its physical limits')
    return proposal,progress,q,provenance


def build(proposal_path,search_record,qualification,output,history_path=None):
    proposal,progress,q,provenance=inputs(proposal_path,search_record,qualification)
    qualification=Path(qualification).resolve();output=Path(output).resolve()
    evidence={name:qualification/name for name in ('initial_proposal.json','initial_design.json','binding.json','history.json')}
    if output.exists():raise FileExistsError('Use a fresh result directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.tia-results-',dir=output.parent))
    try:
        data=temporary/'data';results=temporary/'results';passives=data/'passives'
        passives.mkdir(parents=True);results.mkdir()
        em_metadata={}
        for tag,suffix in (('transformer','.s4p'),('L1','.s2p'),('LB','.s2p')):
            for ext in ('.gds',suffix,'.json'):shutil.copy2(qualification/(tag+ext),passives/(tag+ext))
            em_metadata[tag]=W.read(qualification/(tag+'.json'))
        physical=dict(zip(FEATURE_KEYS,physical14_features(q['geometry'])[0].tolist()))
        for key in ('topology','sb','pb','ps','m','ns','np'):physical[key]=int(physical[key])
        final=dict(q,physical_inputs=physical,permutation=proposal['permutation'],initialization=progress['initialization'],
                   circuit_grid_ghz=.1,stage_contract=proposal.get('stage_contract'),
                   proposal_grid_ghz=proposal['circuit_grid_ghz'],independent_circuit_grid_ghz=.1,
                   qualification_inputs='results/qualification_inputs.json',
                   passives={tag:f'data/passives/{tag}{suffix}' for tag,suffix in
                             (('transformer','.s4p'),('L1','.s2p'),('LB','.s2p'))})
        W.write(data/'final_design.json',final)
        selected=dict(proposal)
        if 'voltage_policy' in selected:
            selected['voltage_policy']=dict(selected['voltage_policy'])
            selected['voltage_policy'].pop('model_card_path',None)
        selected.pop('xmodel',None)
        selected.update(physical_inputs=physical)
        W.write(data/'selected_proposal.json',selected)
        provenance=dict(provenance,proposal_sha256=sha(data/'selected_proposal.json'))
        final['proposal_sha256']=sha(data/'selected_proposal.json')
        W.write(results/'qualification_inputs.json',provenance)
        final['qualification_inputs_sha256']=sha(results/'qualification_inputs.json')
        W.write(data/'final_design.json',final)
        W.write(results/'staged_search.json',progress)
        W.write(results/'em_networks.json',em_metadata)
        history=None
        if search_record is None:
            if history_path is not None:raise ValueError('Submitted-design verification does not consume an optimization history')
        else:
            from optimization_figures import from_report,curves,build as objective_figure
            refined='em_refinement' in proposal
            source=W.read(evidence['initial_proposal.json']) if refined else proposal
            stage=proposal['stage_contract']['stage']
            if history_path is None:
                report_path=Path(search_record).resolve().parent/f'stage_{stage:02d}/result.json'
                report=W.read(report_path)
                history=from_report(report,sha(report_path),selected_trial=source['trial'])
            else:
                history=W.read(history_path);curves(history)
            selected=history['selected_replay']
            if (selected['trial']!=source['trial'] or history['source_checkpoint_sha256']!=proposal['xmodel_sha256']
                    or selected['objective']!=source['objective'] or selected['max_constraint']!=max(source['constraints'])):
                raise ValueError('Objective history does not describe the qualified proposal')
            if refined:
                from em_active_refinement import validate_refinement,validate_network_identity
                initial=W.read(evidence['initial_proposal.json'])
                assessment=W.read(evidence['initial_design.json'])
                binding=W.read(evidence['binding.json'])
                trajectory=W.read(evidence['history.json'])
                validate_refinement(proposal,initial,assessment,binding,trajectory)
                validate_network_identity(qualification,binding)
                for key,filename in (('initial_proposal_sha256','initial_proposal.json'),
                                     ('initial_assessment_sha256','initial_design.json'),
                                     ('binding_sha256','binding.json'),('history_sha256','history.json')):
                    if proposal['em_refinement'][key]!=sha(evidence[filename]):
                        raise ValueError('Refinement evidence changed: '+filename)
                for source_name,destination in (('initial_proposal.json',data/'search_proposal.json'),
                        ('initial_design.json',results/'initial_em_assessment.json'),
                        ('binding.json',results/'refinement_binding.json'),('history.json',results/'refinement_history.json')):
                    shutil.copy2(evidence[source_name],destination)
                if history.get('schema')!='tia-two-phase-objective-history-v1':
                    history=dict(schema='tia-two-phase-objective-history-v1',random_searches=[history],
                        selected_replay=history['selected_replay'],initialization=history['initialization'],
                        source_checkpoint_sha256=history['source_checkpoint_sha256'],
                        refinement=dict(records=trajectory,final_metrics=q['metrics_em']))
            history['packaged_checkpoint_sha256']=proposal['xmodel_sha256']
            history['independently_qualified']=True
            W.write(results/'optimization_history.json',history)
        comparison=dict(method='Fixed-parameter ideal winding-bypass comparison',reoptimized=False,circuit_step_ghz=.1,runs={})
        import tia_sim as T
        for name,xf in (('with_transformer',passives/'transformer.s4p'),('without_transformer',None)):
            response,metrics,audit=W.circuit(q['geometry'],q['params'],xf,passives/'L1.s2p',passives/'LB.s2p')
            if name=='with_transformer':
                for key in ('zt_dbohm','bw_ghz','peak_db','gd_pp_ps','noise_pa','power_mw'):
                    np.testing.assert_allclose(metrics[key],q['metrics_em'][key],rtol=1e-8,atol=1e-9)
                with np.load(qualification/'response.npz',allow_pickle=False) as original:
                    for key in ('f','zt','fn','inoise'):
                        np.testing.assert_allclose(response[key],original[key],rtol=1e-8,atol=1e-10)
            np.savez_compressed(results/(name+'.npz'),**{key:response[key] for key in ('f','zt','fn','inoise')})
            comparison['runs'][name]=dict(metrics=metrics,curve_file=f'results/{name}.npz',
                group_delay_metric_band_ghz=[1.,min(metrics['bw_ghz'],26.)],noise_metric_band_ghz=[1.,metrics['bw_ghz']],
                meets_scalar_specs=bool(T.meets(response)),current_densities_in_range=all(1<=j<=3 for j in metrics['jc']))
        W.write(results/'comparison.json',comparison)
        from output_reflection import build as reflection
        checks=temporary/'reflection_checks';reflection(checks,root=temporary)
        for filename in ('output_reflection.npz','output_reflection.json'):shutil.copy2(checks/filename,results/filename)
        shutil.rmtree(checks)
        from results_figures import build as figures
        figures(temporary/'figures',root=temporary)
        if history is not None:objective_figure(temporary/'figures',history=results/'optimization_history.json')
        study=W.read(temporary/'figures/wireline_eye_study.json')
        W.write(results/'wireline_eye_study.json',study)
        W.write(results/'eye_metrics.json',dict(metrics=study['figure_cases'][-1]['metrics'],settings=study['figure_cases'][-1]['settings']))
        W.write(temporary/'report.json',dict(status='qualified',initialization=progress['initialization'],stage=progress['selected_stage'],
            metrics_em=q['metrics_em'],spiral_geometries=q['spiral_geometries'],
            proposal_sha256=sha(Path(proposal_path)),
            scientific_source_sha256={name:sha(CODE/name) for name in ('qualified_results.py','output_reflection.py','results_figures.py','wireline_eyes.py','workflow.py')}))
        W.write(temporary/'MANIFEST.json',dict(files={str(p.relative_to(temporary)):sha(p) for p in sorted(temporary.rglob('*')) if p.is_file()}))
        temporary.rename(output)
    except Exception as error:
        error.add_note(f'Incomplete result retained for diagnosis: {temporary}')
        raise
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal',type=Path,required=True);parser.add_argument('--search-record',type=Path)
    parser.add_argument('--qualification',type=Path,required=True)
    parser.add_argument('--history',type=Path,help='Optional compact history from the fresh search')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(build(args.proposal,args.search_record,args.qualification,args.output,args.history))
