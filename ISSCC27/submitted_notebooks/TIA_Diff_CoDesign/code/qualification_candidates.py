"""Independently screen the fixed feasible candidate pool of a completed search."""
from environment import spiral_domain as active_spiral_domain
from environment import ROOT,CODE,configure
configure()
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import workflow as W
import campaign_history as H
import vce_policy as V
from expanded_direct_surrogate_flow import CANDIDATE_REPLAY_STEP_GHZ
from joint_passives import SPIRAL_KEYS,joint_geometry,proposal_binding


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(search,output=None,introduced_after_initial_failure=False,*,model=None,spiral_model=None):
    model=Path(model or ROOT/'models/transformer.pt')
    spiral_model=Path(spiral_model or ROOT/'models/spiral.pt')
    search=Path(search).resolve();output=Path(output or search/'qualification_pool').resolve()
    if output.exists():raise FileExistsError('Qualification pools are immutable; choose a fresh directory')
    progress=W.read(search/'staged_search.json');original=W.read(search/'best.json')
    if progress.get('status')!='awaiting_independent_em':raise ValueError('No completed candidate candidate pool')
    stage=progress['selected_stage'];report_path=search/f'stage_{stage:02d}/result.json';report=W.read(report_path)
    hashes=report['input_hashes'];policy=V.policy_from_pdk(CODE,search_buffer_v=.001)
    expected=dict(source={name:sha(CODE/name) for name in H.SOURCE_FILES},
        data_domain=sha(ROOT/'data'/f'search_stage_{stage:02d}.json'),
        active_domain=sha(ROOT/'data/active_search_domain.json'),spiral_domain=sha(active_spiral_domain()))
    if (any(hashes.get(k)!=v for k,v in expected.items())
            or report['xmodel_sha256']!=sha(model)
            or hashes['passives']['spiral_checkpoint']!=sha(spiral_model)
            or report['voltage_policy']['model_card_sha256']!=policy['model_card_sha256']
            or original['stage_contract']['stage']!=stage or original['circuit_grid_ghz']!=CANDIDATE_REPLAY_STEP_GHZ
            or original['stage_contract']['plan_sha256']!=progress['plan_sha256']):
        raise ValueError('Qualification pool evaluator, model, PDK or domain changed')
    joint_geometry(original)
    rows=sorted((r for r in report['fine_grid_replays'] if r['feasible']),key=lambda r:r['objective'])
    if not 1<=len(rows)<=5 or report['fine_grid_replay']!=rows[0]:raise ValueError('Expected the original bounded candidate pool')
    for key,value in rows[0].items():
        if original.get(key)!=value:raise ValueError('Original proposal and selected candidate replay disagree')
    identity=dict(source_report_sha256=sha(report_path),original_proposal_sha256=sha(search/'best.json'),
        materializer_sha256=sha(__file__),trial_order=[r['trial'] for r in rows])
    pool_id=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    proposals=[]
    for rank,row in enumerate(rows):
        values=np.asarray(row['constraints'],float);metrics=row.get('metrics_surrogate')
        if (row['status']!='complete' or values.shape!=(16,) or not np.isfinite(values).all() or np.any(values>0)
                or not metrics or any(not np.isfinite(metrics[k]) for k in ('bw_ghz','zt_dbohm','gd_pp_ps','power_mw','noise_pa','peak_db'))
                or not np.isclose(row['objective'],-metrics['bw_ghz'],rtol=0,atol=1e-10)):
            raise ValueError('A candidate pool entry is not a valid feasible circuit evaluation')
        audit=V.audit_op(metrics['op'],policy)
        if not audit['search_passed'] or not audit['qualified']:raise ValueError('Pool candidate fails the recorded voltage policy')
        proposal=copy.deepcopy(original);proposal.update(copy.deepcopy(row))
        proposal['voltage_audit']=audit
        proposal['spiral_geometries']={tag:[row['params'][f'{tag.lower()}_{key}'] for key in SPIRAL_KEYS] for tag in ('L1','LB')}
        if rank:
            provenance=dict(pool_id=pool_id,rank=rank,trial=row['trial'],**identity)
            proposal['qualification_replay']=provenance
            proposal['stage_contract']=dict(proposal['stage_contract'],qualification_replay=provenance)
        proposal['joint_binding_sha256']=proposal_binding(proposal);joint_geometry(proposal)
        if rank==0:
            # Preserve exact bytes so a completed initial qualification can be reused by identity.
            if proposal['voltage_audit']!=original['voltage_audit']:raise ValueError('Original voltage audit differs from replay OP')
            proposals.append((rank,row['trial'],(search/'best.json').read_bytes()))
        else:proposals.append((rank,row['trial'],(json.dumps(proposal,indent=2,allow_nan=False)+'\n').encode()))
    output.mkdir(parents=True,exist_ok=False);entries=[]
    for rank,trial,raw in proposals:
        path=output/f'proposal_{rank:02d}.json';path.write_bytes(raw)
        entries.append(dict(rank=rank,trial=trial,proposal=path.name,proposal_sha256=sha(path)))
    record=dict(schema_version=1,pool_id=pool_id,maximum_candidates=5,
        order='descending original candidate predicted bandwidth',source_report=f'stage_{stage:02d}/result.json',
        introduced_after_initial_qualification_failure=introduced_after_initial_failure,**identity,entries=entries)
    W.write(output/'pool.json',record);W.write(output/'outcomes.json',dict(pool_sha256=sha(output/'pool.json'),entries=[]))
    return output


def validate_pool(pool):
    pool=Path(pool).resolve();record=W.read(pool/'pool.json');search=pool.parent
    if (record['source_report_sha256']!=sha(search/record['source_report'])
            or record['original_proposal_sha256']!=sha(search/'best.json')
            or record['materializer_sha256']!=sha(__file__) or record['maximum_candidates']!=5):
        raise ValueError('Frozen qualification pool changed')
    rows=sorted((r for r in W.read(search/record['source_report'])['fine_grid_replays'] if r['feasible']),key=lambda r:r['objective'])
    if record['trial_order']!=[r['trial'] for r in rows] or len(record['entries'])!=len(rows):raise ValueError('Qualification pool was expanded or reordered')
    for rank,(entry,row) in enumerate(zip(record['entries'],rows)):
        path=(pool/entry['proposal']).resolve()
        if not path.is_relative_to(pool) or entry['rank']!=rank or entry['trial']!=row['trial'] or sha(path)!=entry['proposal_sha256']:
            raise ValueError('Qualification pool proposal identity changed')
        proposal=W.read(path);joint_geometry(proposal)
        if any(proposal.get(k)!=v for k,v in row.items()):raise ValueError('Qualification proposal differs from its source replay')
        if rank and proposal['qualification_replay']['pool_id']!=record['pool_id']:raise ValueError('Qualification pool identity changed')
    return record


def qualification(pool,rank,directory,allowed_root=None):
    pool=Path(pool).resolve();record=validate_pool(pool);entry=record['entries'][rank]
    directory=Path(directory).resolve()
    if allowed_root is not None and not directory.is_relative_to(Path(allowed_root).resolve()):raise ValueError('Qualification path escapes its run')
    proposal=W.read(pool/entry['proposal']);q=W.read(directory/'final_design.json');inputs=W.read(directory/'qualification_inputs.json')
    if (q.get('strict_feasible') not in (True,False) or q['qualification_inputs_sha256']!=sha(directory/'qualification_inputs.json')
            or inputs['proposal_sha256']!=entry['proposal_sha256'] or inputs['joint_binding_sha256']!=proposal['joint_binding_sha256']
            or inputs['stage_contract']!=proposal['stage_contract'] or q['params']!=proposal['params']
            or q['geometry']!=proposal['geometry'] or q['spiral_geometries']!=proposal['spiral_geometries']
            or not (directory/'response.npz').is_file()):raise ValueError('Qualification is incomplete or differs from its exact proposal')
    for tag,suffix in (('transformer','.s4p'),('L1','.s2p'),('LB','.s2p')):
        metadata=W.read(directory/(tag+'.json'))
        if (metadata.get('status')!='complete' or sha(directory/(tag+suffix))!=metadata['response_sha256']
                or sha(directory/(tag+'.gds'))!=metadata['gds_sha256']
                or inputs['network_sha256'][tag]!=metadata['response_sha256']):
            raise ValueError('All three independent EM networks must be complete and unchanged')
    return q


def record_outcome(pool,rank,directory,allowed_root=None):
    pool=Path(pool).resolve();q=qualification(pool,rank,directory,allowed_root)
    result=W.read(pool/'outcomes.json')
    if result['pool_sha256']!=sha(pool/'pool.json') or any(e['rank']==rank for e in result['entries']):raise ValueError('Qualification outcome already recorded or pool changed')
    import os
    result['entries'].append(dict(rank=rank,status='qualified' if q['strict_feasible'] else 'qualification_failed',
        directory=os.path.relpath(Path(directory).resolve(),pool),final_design_sha256=sha(Path(directory)/'final_design.json')))
    W.write(pool/'outcomes.json',result)
    return q['strict_feasible']


def require_exhausted(pool,allowed_root):
    pool=Path(pool).resolve();record=validate_pool(pool);outcomes=W.read(pool/'outcomes.json')
    if outcomes.get('refinements'):raise ValueError('A qualified refinement prevents a restart')
    if (outcomes['pool_sha256']!=sha(pool/'pool.json') or len(outcomes['entries'])!=len(record['entries'])
            or sorted(e['rank'] for e in outcomes['entries'])!=list(range(len(record['entries'])))):
        raise ValueError('Qualification pool still contains pending candidates')
    for entry in outcomes['entries']:
        path=(pool/entry['directory']).resolve()
        if entry['status']!='qualification_failed' or entry['final_design_sha256']!=sha(path/'final_design.json'):
            raise ValueError('A qualified, changed or incomplete pool candidate prevents a conditional restart')
        if qualification(pool,entry['rank'],path,allowed_root)['strict_feasible'] is not False:
            raise ValueError('A qualified design prevents a conditional restart')
    return dict(pool_sha256=sha(pool/'pool.json'),outcomes_sha256=sha(pool/'outcomes.json'),candidates=len(record['entries']))


def record_refinement(pool,rank,initial_directory,refined):
    """Add a passing refinement without replacing the original pool rejection."""
    from em_active_refinement import validate_refinement,validate_network_identity
    pool=Path(pool).resolve();record=validate_pool(pool)
    entry=record['entries'][rank]
    initial=qualification(pool,rank,initial_directory,pool.parent.parent)
    if initial['strict_feasible'] is not False:raise ValueError('A refinement must preserve an original rejection')
    directory=Path(refined['qualification']).resolve()
    if not directory.is_relative_to(Path(initial_directory).resolve()):
        raise ValueError('Refinement directory escapes its original qualification')
    proposal_path=Path(refined['proposal']);proposal=W.read(proposal_path)
    metadata=proposal['em_refinement']
    for key,name in (('initial_proposal_sha256','initial_proposal.json'),
                     ('initial_assessment_sha256','initial_design.json'),
                     ('binding_sha256','binding.json'),('history_sha256','history.json')):
        if metadata[key]!=sha(directory/name):raise ValueError('Refinement evidence changed: '+name)
    if sha(directory/'initial_proposal.json')!=entry['proposal_sha256']:
        raise ValueError('Refinement belongs to a different pool proposal')
    row=validate_refinement(proposal,W.read(directory/'initial_proposal.json'),
        W.read(directory/'initial_design.json'),W.read(directory/'binding.json'),W.read(directory/'history.json'))
    validate_network_identity(directory,W.read(directory/'binding.json'))
    final=W.read(directory/'final_design.json')
    if final['strict_feasible'] is not True or final['params']!=proposal['params'] or final['metrics_em']!=row['raw_dense']['metrics']:
        raise ValueError('Refinement result is not independently qualified')
    for tag,suffix in (('transformer','.s4p'),('L1','.s2p'),('LB','.s2p')):
        certificate=W.read(directory/(tag+'.json'))
        if (sha(directory/(tag+suffix))!=certificate['response_sha256']
                or sha(directory/(tag+'.gds'))!=certificate['gds_sha256']
                or sha(directory/(tag+suffix))!=sha(Path(initial_directory)/(tag+suffix))
                or sha(directory/(tag+'.gds'))!=sha(Path(initial_directory)/(tag+'.gds'))
                or sha(directory/(tag+'.json'))!=sha(Path(initial_directory)/(tag+'.json'))):
            raise ValueError('Refined raw network differs from its certificate')
    outcomes=W.read(pool/'outcomes.json')
    outcomes.setdefault('refinements',[]).append(dict(rank=rank,status='qualified',
        proposal_sha256=sha(proposal_path),final_design_sha256=sha(directory/'final_design.json')))
    W.write(pool/'outcomes.json',outcomes)
