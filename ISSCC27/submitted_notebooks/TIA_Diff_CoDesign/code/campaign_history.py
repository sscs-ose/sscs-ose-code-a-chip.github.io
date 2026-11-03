"""Carry verified observations between variable-release stages of one random-start search."""
import hashlib
import json
from pathlib import Path

import numpy as np

SOURCE_FILES=('terminal_policy.py','expanded_direct_surrogate_flow.py','active_constraint_search.py','tia_sim.py',
              'xfmr_schema.py','run_ngspice.sh','.spiceinit','surrogate.py','direct_generator_snapshot.py',
              'joint_passives.py','spiral_gen.py','features14.py','section21_parameters.py',
              'multiturn_experiment.py','run_surrogate_vce1p6.py','vce_policy.py','campaign_history.py','environment.py','workflow.py','staged_search.py','em_active_refinement.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distributions(bounds):
    from optuna.distributions import IntDistribution,FloatDistribution,CategoricalDistribution
    result={}
    for key,spec in bounds.items():
        if isinstance(spec,tuple):kind,low,high=spec;step=1
        else:
            kind=spec['kind'];step=spec.get('step',1)
            if kind=='choices':result[key]=CategoricalDistribution(spec['choices']);continue
            low,high=spec['low'],spec['high']
        result[key]=(IntDistribution(int(low),int(high),step=int(step)) if kind=='int'
                     else FloatDistribution(low,high,log=kind=='log',step=None if isinstance(spec,tuple) else spec.get('step')))
    return result


def report_hashes(args):
    if args.campaign_record is None:return {}
    record=Path(args.campaign_record).resolve();out=Path(args.output).resolve();index=args.stage_index
    if index not in (0,1,2) or record.parent!=out.parent or out.name!=f'stage_{index:02d}':
        raise ValueError('Earlier-stage observations must belong to this campaign directory')
    result={}
    for stage in range(index):
        path=record.parent/f'stage_{stage:02d}'/'result.json'
        if path.resolve().parent.parent!=record.parent:raise ValueError('Earlier-stage path escapes its campaign')
        result[str(path.relative_to(record.parent))]=sha(path)
    return result


def observations(args,bounds,base,domain,hashes):
    """Accept only genuine coarse evaluations produced earlier in the same fresh campaign."""
    import expanded_direct_surrogate_flow as F
    import vce_policy as V
    from optuna.distributions import IntDistribution,CategoricalDistribution
    if args.campaign_record is None:
        if args.stage_index is not None:raise ValueError('A stage index requires a campaign record')
        return [],dict(count=0,campaign_id=None,stage_index=None,source_reports={})
    campaign_path=Path(args.campaign_record).resolve();out=Path(args.output).resolve()
    index=args.stage_index
    if (index not in (0,1,2) or out.name!=f'stage_{index:02d}' or campaign_path.parent!=out.parent
            or campaign_path.name!='campaign.json'):
        raise ValueError('Campaign history is restricted to its own stage directories')
    campaign=json.loads(campaign_path.read_text());code=Path(F.__file__).parent
    expected=dict(source_sha256={name:sha(code/name) for name in SOURCE_FILES},
                  model_sha256=dict(transformer=sha(args.xmodel),spiral=sha(args.smodel)),
                  active_domain_sha256=sha(args.active_domain),spiral_domain_sha256=sha(args.spiral_domain),
                  base_geometry_sha256=sha(args.geometry),
                  pdk_model_card_sha256=V.policy_from_pdk(code,search_buffer_v=.001)['model_card_sha256'])
    if any(campaign.get(key)!=value for key,value in expected.items()):
        raise ValueError('Campaign evaluator, model, PDK or domain identities changed')
    if (campaign.get('schema_version')!=1 or not isinstance(campaign.get('campaign_id'),str)
            or len(campaign['campaign_id'])!=32 or args.seed!=campaign['seed']+index
            or args.trials!=campaign['trials_per_stage'] or args.jobs!=campaign['jobs']
            or args.optimization_step_ghz!=1. or args.gain_margin_db!=.2 or not args.optimize_spirals):
        raise ValueError('Campaign sampling or evaluation contract changed')
    dists=distributions(bounds);items=[];seen_ids=set();seen_points={};sources={}
    for stage in range(index):
        path=campaign_path.parent/f'stage_{stage:02d}'/'result.json'
        if path.resolve().parent.parent!=campaign_path.parent:raise ValueError('Campaign stage path escapes its directory')
        old=json.loads(path.read_text());identity=old.get('within_campaign',{})
        if (old.get('status')!='no_candidate' or old.get('completed') is not True
                or identity.get('campaign_id')!=campaign['campaign_id'] or identity.get('stage_index')!=stage
                or old.get('xmodel_sha256')!=sha(args.xmodel)
                or old.get('voltage_policy',{}).get('model_card_sha256')!=campaign['pdk_model_card_sha256']
                or old.get('config',{}).get('optimization_step_ghz')!=args.optimization_step_ghz):
            raise ValueError('Earlier campaign stage is incomplete or has a different evaluation identity')
        for key,value in hashes.items():
            if key not in ('data_domain','stage_observations') and old['input_hashes'].get(key)!=value:
                raise ValueError('Earlier stage and current scientific inputs disagree: '+key)
        rows=old['rows']
        if len(rows)!=campaign['trials_per_stage'] or [r['trial'] for r in rows]!=list(range(len(rows))):
            raise ValueError('Earlier stage has an incomplete proposal budget')
        relative=str(path.relative_to(campaign_path.parent));sources[relative]=sha(path)
        if sources[relative]!=hashes['stage_observations'][relative]:raise ValueError('Earlier observations changed during loading')
        for row in rows:
            if row['status']!='complete':continue
            evaluation_id=f"{campaign['campaign_id']}:{stage}:{row['trial']}"
            if row.get('evaluation_id')!=evaluation_id or row.get('origin_stage')!=stage:
                raise ValueError('An inherited observation has the wrong origin')
            if evaluation_id in seen_ids:raise ValueError('A campaign evaluation was imported twice')
            seen_ids.add(evaluation_id)
            constraints=np.asarray(row['constraints'],dtype=float)
            if (constraints.shape!=(16,) or not np.isfinite(constraints).all()
                    or row['feasible']!=bool(np.all(constraints<=0))
                    or not np.isclose(row['objective'],-row['metrics_surrogate']['bw_ghz'],rtol=0,atol=1e-10)):
                raise ValueError('Earlier coarse-grid objective or constraint labels are inconsistent')
            params={}
            for key,spec in bounds.items():
                value=row['params'].get(key)
                if value is None and key.startswith('x_'):value=row['geometry'][key[2:]]
                dist=dists[key]
                if value is None or isinstance(value,bool) or not np.isfinite(value):raise ValueError('Missing mapped parameter: '+key)
                if isinstance(dist,IntDistribution):
                    if value!=int(value) or not dist.low<=value<=dist.high or (int(value)-dist.low)%dist.step:
                        raise ValueError('Mapped integer lies outside the expanded domain: '+key)
                    value=int(value)
                elif isinstance(dist,CategoricalDistribution):
                    if value not in dist.choices:raise ValueError('Mapped choice lies outside the expanded domain')
                elif not dist.low<=value<=dist.high:raise ValueError('Mapped parameter lies outside the expanded domain: '+key)
                params[key]=value
            geometry=F.geometry_from_params(params,base,domain)
            if F.XG.normalize(geometry)!=F.XG.normalize(row['geometry']):
                raise ValueError('Variable release changed an inherited physical geometry')
            key=json.dumps(params,sort_keys=True,allow_nan=False)
            if key in seen_points:
                previous=seen_points[key]
                np.testing.assert_allclose(previous['constraints'],constraints,rtol=0,atol=1e-10)
                np.testing.assert_allclose(previous['objective'],row['objective'],rtol=0,atol=1e-10)
                continue
            item=dict(evaluation_id=evaluation_id,origin_stage=stage,params=params,
                      constraints=constraints.tolist(),objective=row['objective'])
            seen_points[key]=item;items.append(item)
    return items,dict(count=len(items),campaign_id=campaign['campaign_id'],stage_index=index,source_reports=sources)


def add_observations(study,items,bounds):
    from optuna.trial import create_trial
    dists=distributions(bounds)
    for item in items:
        trial=create_trial(value=item['objective'],params=item['params'],distributions=dists,
            user_attrs=dict(constraints=item['constraints'],evaluation_id=item['evaluation_id'],origin_stage=item['origin_stage']),
            constraints={str(i):float(value) for i,value in enumerate(item['constraints'])})
        study.add_trial(trial)
