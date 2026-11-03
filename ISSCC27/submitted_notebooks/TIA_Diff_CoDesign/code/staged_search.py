"""Search 22 variables, then release primary width and winding counts if needed."""
from environment import spiral_domain as active_spiral_domain
from environment import ROOT, CODE, configure
BUDGET=configure()
import hashlib
import json
import uuid
import campaign_history as H
import terminal_policy as TP
from pathlib import Path

import numpy as np

STARTUP_TRIALS=256
STAGES=((22,'initial widths and dimensions'),(23,'independent primary width'),(25,'variable winding counts'))


def healthy_search(report,budget):
    """Distinguish a genuine absence of feasible solutions from execution failure."""
    if report.get('status') not in ('complete','no_candidate'):
        raise RuntimeError('Search did not finish normally')
    rows=report.get('rows',[]);fine=report.get('fine_grid_replays',[])
    if len(rows)!=budget or [row['trial'] for row in rows]!=list(range(budget)):
        raise RuntimeError('Search budget is incomplete or trial records are inconsistent')
    for row in rows+fine:
        if row.get('status')=='failed' and row.get('error'):
            raise RuntimeError('program_error: '+row['error'])
        values=np.asarray(row['constraints'],dtype=float)
        if values.shape!=(16,) or not np.isfinite(values).all():
            raise RuntimeError('Invalid constraint record in completed search')
        expected=row.get('status')=='complete' and bool(np.all(values<=0))
        if row.get('feasible')!=expected:raise RuntimeError('Feasibility flags disagree with signed constraints')
    if not any(row.get('status')=='complete' for row in rows):
        raise RuntimeError('evaluation_failed: no successful circuit evaluations')
    if any(row.get('feasible') for row in rows) and not fine:
        raise RuntimeError('refinement_failed: feasible proposals were not replayed')
    if fine and not any(row.get('status')=='complete' for row in fine):
        raise RuntimeError('refinement_failed: every candidate circuit evaluation failed')
    feasible=[row for row in fine if row.get('status')=='complete' and row.get('feasible')
              and all(value<=0 for value in row['constraints'])]
    if bool(feasible)!=(report['status']=='complete'):
        raise RuntimeError('Search status disagrees with its feasible candidate records')
    return bool(feasible)


def preflight(model,spiral_model):
    """Check tools on an independent random sample, without seeding the optimizer."""
    import torch
    import workflow as W
    import expanded_direct_surrogate_flow as F
    import run_surrogate_vce1p6 as VRun
    import vce_policy as V
    import tia_sim as T
    from joint_passives import SpiralModels,feature_range,GeometryRejected,PredictionRejected
    W.require_circuit_tools();torch.set_num_threads(1)
    prediction=F.DirectPredictor(model)
    if len(prediction.model.xmin)!=14:raise ValueError('Expected the physical fourteen-feature transformer model')
    spirals=SpiralModels(spiral_model,active_spiral_domain())
    base=W.read(ROOT/'data/base_geometry.json')
    domain=F.normalize_domain(W.read(ROOT/'data/search_stage_00.json'),base)
    bounds=F.active_space('123',ROOT/'data/active_search_domain.json')
    bounds.update(F.domain_bounds(domain));bounds.update(spirals.bounds())
    rng=np.random.default_rng(104729)
    def sample(spec):
        if isinstance(spec,dict) and spec['kind']=='choices':return rng.choice(spec['choices']).item()
        kind,low,high=spec if isinstance(spec,tuple) else (spec['kind'],spec['low'],spec['high'])
        if kind=='int':return int(rng.integers(low,high+1))
        if kind=='log':return float(np.exp(rng.uniform(np.log(low),np.log(high))))
        return float(rng.uniform(low,high))
    policy=V.policy_from_pdk(CODE,search_buffer_v=.001)
    original_bv=T.BV_CE;restore=VRun.install_policy_hooks(F,policy)
    try:
        for attempt in range(4096):
            params={key:sample(spec) for key,spec in bounds.items()}
            try:
                geometry=F.geometry_from_params(params,base,domain)
            except ValueError:
                continue
            try:TP.require_integer_geometry(geometry)
            except GeometryRejected:continue
            try:
                with W.independent_geometry():F.validate_physical_candidate(geometry)
            except ValueError:continue
            try:
                feature_range(prediction.model,[geometry])
                geos=spirals.geometries(params);spirals.validate(geos)
            except GeometryRejected:
                continue
            networks=[('sp',prediction.freq,prediction.predict([geometry])[0])]
            try:networks+=[('sp',spirals.freq,s) for s in spirals.predict(geos)]
            except PredictionRejected:continue
            row=F.run_candidate((params,geometry,networks,'123',1.,'tia_sim:run',.2))
            if row['status']=='complete':
                return dict(status='complete',random_seed=104729,attempt=attempt+1,
                            enqueued=False,params=params,spiral_source_basis=spirals.source_basis(geos),
                            metrics=row['metrics_surrogate'],constraints=row['constraints'])
            if row.get('error'):raise RuntimeError('Circuit preflight failed: '+row['error'])
        raise RuntimeError('No successful random-domain preflight evaluation')
    finally:
        restore();T.BV_CE=original_bv


def run(output,trials=6000,jobs=4,seed=0,model=None,spiral_model=None):
    import workflow as W
    from joint_passives import proposal_binding
    if trials<1 or not 1<=jobs<=BUDGET or seed<0:raise ValueError('Invalid stage budget, worker count or seed')
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Use a fresh directory for a staged experiment')
    model=Path(model or ROOT/'models/transformer.pt').resolve()
    spiral_model=Path(spiral_model or ROOT/'models/spiral.pt').resolve()
    files=[model,spiral_model,ROOT/'data/base_geometry.json',ROOT/'data/active_search_domain.json',
           active_spiral_domain()]
    files += [ROOT/'data'/f'search_stage_{index:02d}.json' for index in range(len(STAGES))]
    files += [CODE/name for name in H.SOURCE_FILES]
    inputs={str(index):hashlib.sha256(path.read_bytes()).hexdigest() for index,path in enumerate(files)}
    initial_check=preflight(model,spiral_model)
    import expanded_direct_surrogate_flow as F
    from joint_passives import SpiralModels
    spirals=SpiralModels(spiral_model,active_spiral_domain())
    active=F.active_space('123',ROOT/'data/active_search_domain.json')
    active_count=sum(low!=high for _,low,high in active.values())
    for index,(expected,_) in enumerate(STAGES):
        domain=F.normalize_domain(W.read(ROOT/'data'/f'search_stage_{index:02d}.json'))
        if len(F.domain_bounds(domain))+len(spirals.bounds())+active_count!=expected:
            raise ValueError('Configured stage variable count disagrees with its contract')
    binding=hashlib.sha256(json.dumps(dict(inputs=inputs,trials=trials,jobs=jobs,seed=seed),sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True,exist_ok=False)
    import vce_policy as V
    campaign=dict(schema_version=1,campaign_id=uuid.uuid4().hex,plan_sha256=binding,seed=seed,jobs=jobs,
        trials_per_stage=trials,source_sha256={name:hashlib.sha256((CODE/name).read_bytes()).hexdigest() for name in H.SOURCE_FILES},
        model_sha256=dict(transformer=hashlib.sha256(model.read_bytes()).hexdigest(),spiral=hashlib.sha256(spiral_model.read_bytes()).hexdigest()),
        active_domain_sha256=hashlib.sha256((ROOT/'data/active_search_domain.json').read_bytes()).hexdigest(),
        spiral_domain_sha256=hashlib.sha256((active_spiral_domain()).read_bytes()).hexdigest(),
        base_geometry_sha256=hashlib.sha256((ROOT/'data/base_geometry.json').read_bytes()).hexdigest(),
        pdk_model_card_sha256=V.policy_from_pdk(CODE,search_buffer_v=.001)['model_card_sha256'])
    W.write(output/'campaign.json',campaign)
    W.write(output/'preflight.json',initial_check)
    progress=dict(schema_version=1,status='searching',initialization='random',startup_trials=STARTUP_TRIALS,
                  campaign_id=campaign['campaign_id'],shared_observations=True,
                  plan_sha256=binding,trials_per_stage=trials,
                  maximum_trials=len(STAGES)*trials,stages=[])
    W.write(output/'staged_search.json',progress)
    for index,(variables,description) in enumerate(STAGES):
        if any(hashlib.sha256(path.read_bytes()).hexdigest()!=inputs[str(i)] for i,path in enumerate(files)):
            raise RuntimeError('Staged-search inputs or source files changed')
        domain=ROOT/'data'/f'search_stage_{index:02d}.json'
        try:
            report=W.optimize(output/f'stage_{index:02d}',model,trials,jobs,seed+index,
                domain=domain,spiral_model=spiral_model,spiral_domain=active_spiral_domain(),
                active_domain=ROOT/'data/active_search_domain.json',startup_trials=STARTUP_TRIALS,
                campaign_record=output/'campaign.json',stage_index=index,allow_no_candidate=True)
            feasible=healthy_search(report,trials)
        except Exception as error:
            progress.update(status='execution_failed',failed_stage=index,error=f'{type(error).__name__}: {error}')
            W.write(output/'staged_search.json',progress)
            raise
        progress['stages'].append(dict(stage=index,variables=variables,description=description,
            trials=trials,status='feasible_proposal' if feasible else 'healthy_no_candidate'))
        W.write(output/'staged_search.json',progress)
        if feasible:
            best=W.read(output/f'stage_{index:02d}/best.json')
            best['stage_contract']=dict(stage=index,variables=variables,plan_sha256=binding,
                domain_file=f'data/search_stage_{index:02d}.json',trials=trials,campaign_id=campaign['campaign_id'],
                inherited_evaluations=report['within_campaign']['count'],**TP.markers())
            best['joint_binding_sha256']=proposal_binding(best)
            W.write(output/'best.json',best)
            progress.update(status='awaiting_independent_em',selected_stage=index)
            W.write(output/'staged_search.json',progress)
            print(f'Stage {index}: feasible proposal; independent EM qualification is required')
            return progress
        # Active and spiral bounds stay unchanged when transformer variables are released.
    progress['status']='no_feasible_proposal'
    W.write(output/'staged_search.json',progress)
    print('All stage budgets completed without a feasible candidate proposal')
    return progress
