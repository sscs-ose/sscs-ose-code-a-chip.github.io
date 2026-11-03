"""Permit one warm-started joint search only after five normal random searches fail."""
from environment import spiral_domain as active_spiral_domain
from environment import ROOT,CODE,configure
BUDGET=configure()
from contextlib import contextmanager
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import optuna
import campaign_history as H
import expanded_direct_surrogate_flow as F
import staged_search as S
import workflow as W
import terminal_policy as TP
import vce_policy as V
from joint_passives import SpiralModels,feature_range,proposal_binding


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def failed_campaigns(registry,expected_trials=6000,*,model=None,spiral_model=None):
    """Validate all five terminal runs before reading any initial candidate."""
    registry=Path(registry).resolve();record=W.read(registry);attempts=record.get('attempts',[])
    if (record.get('status') not in ('five_random_searches_failed','five_random_searches_failed_after_em')
            or len(attempts)!=5 or sorted(a.get('index',-1) for a in attempts)!=list(range(5))
            or len({a.get('seed') for a in attempts})!=5 or len({a.get('directory') for a in attempts})!=5):
        raise ValueError('Five distinct random starts are required before a conditional restart')
    if any(a.get('status') not in ('no_feasible_proposal','qualification_failed') for a in attempts):
        raise ValueError('A random start is unfinished, qualified, awaiting EM or failed to execute')
    policy=V.policy_from_pdk(CODE,search_buffer_v=.001)
    identities=dict(source_sha256={name:sha(CODE/name) for name in H.SOURCE_FILES},
        model_sha256=dict(transformer=sha(model or ROOT/'models/transformer.pt'),spiral=sha(spiral_model or ROOT/'models/spiral.pt')),
        active_domain_sha256=sha(ROOT/'data/active_search_domain.json'),spiral_domain_sha256=sha(active_spiral_domain()),
        base_geometry_sha256=sha(ROOT/'data/base_geometry.json'),pdk_model_card_sha256=policy['model_card_sha256'])
    sources=[];ids=set();summary=[]
    for attempt in attempts:
        pool_proof=None
        directory=Path(attempt['directory']);folder=(directory if directory.is_absolute() else registry.parent/directory).resolve()
        if not folder.is_relative_to(registry.parent):raise ValueError('Random-start directory escapes the registry')
        campaign=W.read(folder/'campaign.json');progress=W.read(folder/'staged_search.json')
        if (campaign.get('campaign_id') in ids or campaign.get('seed')!=attempt['seed']
                or campaign.get('trials_per_stage')!=expected_trials
                or any(campaign.get(k)!=v for k,v in identities.items())
                or progress.get('campaign_id')!=campaign['campaign_id'] or progress.get('initialization')!='random'):
            raise ValueError('Random-search campaign, evaluator, model, PDK or domain identity changed')
        ids.add(campaign['campaign_id']);stages=progress.get('stages',[])
        if not stages or len(stages)>3:raise ValueError('Incomplete variable-release schedule')
        if attempt['status']=='no_feasible_proposal' and (progress['status']!='no_feasible_proposal' or len(stages)!=3):
            raise ValueError('The full randomized search budget has not completed')
        if attempt['status']=='qualification_failed':
            from qualification_candidates import require_exhausted
            pool=Path(attempt['qualification_pool'])
            pool=(pool if pool.is_absolute() else registry.parent/pool).resolve()
            if not pool.is_relative_to(folder):raise ValueError('Qualification pool escapes its random search')
            pool_proof=require_exhausted(pool,registry.parent)
            if progress['status']!='awaiting_independent_em':raise ValueError('No selected random proposal was qualified')
            directory=Path(attempt['qualification']);qpath=(directory if directory.is_absolute() else registry.parent/directory).resolve()
            if not qpath.is_relative_to(registry.parent):raise ValueError('Qualification escapes its search registry')
            q=W.read(qpath/'final_design.json');provenance=W.read(qpath/'qualification_inputs.json')
            proposal=W.read(folder/'best.json')
            if (proposal.get('joint_binding_sha256')!=proposal_binding(proposal)
                    or provenance.get('joint_binding_sha256')!=proposal['joint_binding_sha256']
                    or q.get('params')!=proposal['params'] or q.get('geometry')!=proposal['geometry']
                    or q.get('spiral_geometries')!=proposal['spiral_geometries']):
                raise ValueError('Rejected qualification and random proposal parameters disagree')
            if (q.get('strict_feasible') is not False or q['qualification_inputs_sha256']!=sha(qpath/'qualification_inputs.json')
                    or provenance['proposal_sha256']!=sha(folder/'best.json')):
                raise ValueError('A pending, interrupted or successful qualification cannot enable a warm start')
            for tag,suffix in (('transformer','.s4p'),('L1','.s2p'),('LB','.s2p')):
                metadata=W.read(qpath/(tag+'.json'))
                if (metadata.get('status')!='complete' or sha(qpath/(tag+suffix))!=metadata['response_sha256']
                        or sha(qpath/(tag+'.gds'))!=metadata['gds_sha256']
                        or provenance['network_sha256'][tag]!=metadata['response_sha256']):
                    raise ValueError('All three independent EM networks must finish before scientific rejection')
            if not (qpath/'response.npz').is_file():raise ValueError('The qualification circuit evaluation is incomplete')
        stage_records=[]
        for index,stage in enumerate(stages):
            if stage.get('stage')!=index or stage.get('variables')!=(22,23,25)[index] or stage.get('trials')!=expected_trials:
                raise ValueError('Random-search stage budget or variable count changed')
            path=folder/f'stage_{index:02d}'/'result.json'
            if not path.resolve().is_relative_to(folder):raise ValueError('Stage result escapes its campaign')
            report=W.read(path)
            if (report.get('initialization')!=dict(method='random',startup_trials=S.STARTUP_TRIALS,prior_design=None)
                    or report.get('within_campaign',{}).get('campaign_id')!=campaign['campaign_id']
                    or (index==0 and report.get('within_campaign',{}).get('count')!=0)
                    or report.get('input_hashes',{}).get('source')!=identities['source_sha256']
                    or report.get('input_hashes',{}).get('active_domain')!=identities['active_domain_sha256']
                    or report.get('input_hashes',{}).get('spiral_domain')!=identities['spiral_domain_sha256']
                    or report.get('input_hashes',{}).get('data_domain')!=sha(ROOT/'data'/f'search_stage_{index:02d}.json')
                    or report.get('input_hashes',{}).get('geometry')!=identities['base_geometry_sha256']
                    or report.get('input_hashes',{}).get('campaign_record')!=sha(folder/'campaign.json')
                    or report.get('input_hashes',{}).get('passives',{}).get('spiral_checkpoint')!=identities['model_sha256']['spiral']
                    or report.get('voltage_policy',{}).get('model_card_sha256')!=identities['pdk_model_card_sha256']
                    or report.get('xmodel_sha256')!=identities['model_sha256']['transformer']):
                raise ValueError('A stage is not a compatible random-start evaluation')
            feasible=S.healthy_search(report,expected_trials)
            if feasible and not (attempt['status']=='qualification_failed' and index==len(stages)-1):
                raise ValueError('A feasible random proposal still needs independent qualification')
            stage_records.append(dict(stage=index,path=str(path.relative_to(registry.parent)),sha256=sha(path)))
            sources.append((attempt['index'],index,path))
        summary.append(dict(index=attempt['index'],seed=attempt['seed'],campaign_id=campaign['campaign_id'],
            status=attempt['status'],stage_reports=stage_records,qualification_pool=pool_proof))
    return dict(registry_sha256=sha(registry),random_starts=5,trials_per_stage=expected_trials,identities=identities,attempts=summary),sources


def choose_initial(sources,*,model=None,spiral_model=None):
    """Rank valid recorded candidates by constraint violation, then bandwidth."""
    best=None
    for attempt,stage,path in sources:
        report=W.read(path);fine={row['trial']:row for row in report.get('fine_grid_replays',[])}
        for coarse in report['rows']:
            row=fine.get(coarse['trial'],coarse)
            if row['status']!='complete':continue
            values=np.asarray(row['constraints'],float)
            if values.shape!=(16,) or not np.isfinite(values).all() or not np.isfinite(row['objective']):
                raise ValueError('A completed candidate has invalid labels')
            rank=(float(np.maximum(values,0).sum()),float(row['objective']))
            if best is None or rank<best['rank']:
                best=dict(rank=rank,attempt=attempt,stage=stage,trial=row['trial'],
                    grid_ghz=float(report['final_grid_ghz'] if row is not coarse else report['config']['optimization_step_ghz']),
                    row=copy.deepcopy(row),source_sha256=sha(path))
    if best is None:raise RuntimeError('The five searches contain no valid evaluated candidate')
    base=W.read(ROOT/'data/base_geometry.json');domain=F.normalize_domain(W.read(ROOT/'data/search_stage_02.json'),base)
    spirals=SpiralModels(spiral_model or ROOT/'models/spiral.pt',active_spiral_domain())
    bounds=F.active_space('123',ROOT/'data/active_search_domain.json');bounds.update(F.domain_bounds(domain));bounds.update(spirals.bounds())
    row=best['row'];point={}
    for key,spec in bounds.items():
        value=row['params'].get(key)
        if value is None and key.startswith('x_'):value=row['geometry'][key[2:]]
        if value is None or isinstance(value,bool) or not np.isfinite(value):raise ValueError('Incomplete restart coordinate: '+key)
        if isinstance(spec,tuple):
            kind,low,high=spec
            if not low<=value<=high:raise ValueError('Restart coordinate lies outside the declared domain')
            if kind=='int' and value!=int(value):raise ValueError('Restart integer is not integral')
        elif not F.domain_contains(spec,value):raise ValueError('Restart geometry lies outside the declared domain')
        point[key]=int(value) if (spec[0]=='int' if isinstance(spec,tuple) else spec['kind']=='int') else float(value)
    geometry=F.geometry_from_params(point,base,domain)
    if F.XG.normalize(geometry)!=F.XG.normalize(row['geometry']):raise ValueError('Restart mapping changed the selected geometry')
    with W.independent_geometry():F.validate_physical_candidate(geometry)
    predictor=F.DirectPredictor(model or ROOT/'models/transformer.pt');feature_range(predictor.model,[geometry])
    spirals.validate(spirals.geometries(point))
    # Only coordinates initialize the new study. Every objective/constraint is evaluated again.
    selection=dict(attempt=best['attempt'],stage=best['stage'],trial=best['trial'],source_grid_ghz=best['grid_ghz'],
        source_sha256=best['source_sha256'],selection_rule='minimum positive normalized constraint sum; then maximum bandwidth',
        source_violation=best['rank'][0],source_objective=best['rank'][1])
    return point,geometry,selection


@contextmanager
def initialization(point,metadata,binding,binding_paths=None):
    """Use one official Optuna queued point and bind its true mode to every checkpoint."""
    create,save,hashes=optuna.create_study,F.atomic_json,F.input_hashes
    calls=[]
    def study(*args,**kwargs):
        if calls:raise RuntimeError('A conditional restart must create exactly one fresh study')
        result=create(*args,**kwargs);result.enqueue_trial(dict(point));calls.append(result);return result
    def write(path,value):
        if Path(path).name in ('trials.json','result.json','best.json') and isinstance(value,dict):
            value=dict(value,initialization=copy.deepcopy(metadata))
        return save(path,value)
    def identity(args):
        current=dict(binding)
        current.update({key:sha(path) for key,path in (binding_paths or {}).items()})
        return dict(hashes(args),conditional_restart=current)
    optuna.create_study,F.atomic_json,F.input_hashes=study,write,identity
    try:yield calls
    finally:optuna.create_study,F.atomic_json,F.input_hashes=create,save,hashes


def run(registry,output,trials=6000,jobs=8,seed=5,random_trials=6000,*,model=None,spiral_model=None,expected_initial_sha256=None):
    gate,sources=failed_campaigns(registry,random_trials,model=model,spiral_model=spiral_model)
    import torch
    torch.set_num_threads(1)
    point,geometry,selection=choose_initial(sources,model=model,spiral_model=spiral_model)
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Use a fresh conditional restart directory; existing checkpoints are protected')
    output.mkdir(parents=True,exist_ok=False)
    W.write(output/'restart_gate.json',gate);W.write(output/'initial_point.json',dict(params=point,geometry=geometry,source=selection))
    if expected_initial_sha256 is not None and sha(output/'initial_point.json')!=expected_initial_sha256:
        raise ValueError('Warm restart initial point differs from the frozen best-of-five point')
    binding=dict(adapter_sha256=sha(__file__),gate_sha256=sha(output/'restart_gate.json'),initial_point_sha256=sha(output/'initial_point.json'))
    metadata=dict(method='conditional_warm',failed_random_starts=5,startup_trials=S.STARTUP_TRIALS,
                  queued_initial_points=1,random_startup_trials=min(S.STARTUP_TRIALS-1,max(0,trials-1)),source=selection,binding=binding)
    binding_paths=dict(adapter_sha256=Path(__file__),gate_sha256=output/'restart_gate.json',initial_point_sha256=output/'initial_point.json')
    with initialization(point,metadata,binding,binding_paths) as calls:
        report=W.optimize(output/'stage_02',model=model,trials=trials,jobs=jobs,seed=seed,domain=ROOT/'data/search_stage_02.json',
            spiral_model=spiral_model or ROOT/'models/spiral.pt',spiral_domain=active_spiral_domain(),startup_trials=S.STARTUP_TRIALS,allow_no_candidate=True)
    if len(calls)!=1 or report['rows'][0]['params']!=point:raise ValueError('The recorded first trial is not the selected restart point')
    feasible=S.healthy_search(report,trials)
    plan=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()
    progress=dict(schema_version=1,status='awaiting_independent_em' if feasible else 'no_feasible_proposal',
        initialization='conditional_warm',startup_trials=S.STARTUP_TRIALS,random_starts=5,plan_sha256=plan,
        trials_per_stage=trials,maximum_trials=trials,
        stages=[dict(stage=2,variables=25,description='conditional restart from best candidate of five random searches',
                     trials=trials,status='feasible_proposal' if feasible else 'healthy_no_candidate')])
    if feasible:
        best=W.read(output/'stage_02/best.json');best['stage_contract']=dict(stage=2,variables=25,plan_sha256=plan,
            domain_file='data/search_stage_02.json',trials=trials,initialization='conditional_warm',**binding,**TP.markers())
        best['joint_binding_sha256']=proposal_binding(best);W.write(output/'best.json',best);progress['selected_stage']=2
    W.write(output/'staged_search.json',progress)
    return progress


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--trials',type=int,default=6000);parser.add_argument('--jobs',type=int,default=8);parser.add_argument('--seed',type=int,default=5)
    parser.add_argument('--random-trials',type=int,default=6000)
    parser.add_argument('--model',type=Path);parser.add_argument('--spiral-model',type=Path)
    args=parser.parse_args();print(json.dumps(run(args.registry,args.output,args.trials,args.jobs,args.seed,args.random_trials,model=args.model,spiral_model=args.spiral_model),indent=2))
