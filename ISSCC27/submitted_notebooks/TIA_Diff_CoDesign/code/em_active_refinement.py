"""Refine eight active variables using this run's three complete raw EM networks."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import subprocess
import time
import os
import shutil
import argparse
from types import SimpleNamespace

from environment import spiral_domain as active_spiral_domain
from environment import ROOT, CODE, configure
BUDGET = configure()
import numpy as np
import skrf as rf
import torch
from scipy.optimize import minimize
import workflow as W
import expanded_direct_surrogate_flow as F
import active_constraint_search as A
import multiturn_experiment as M
import vce_policy as V
import run_surrogate_vce1p6 as VRun
import tia_sim as T
from em_port_metadata import validate_port_coverage
from joint_passives import SpiralModels

KEYS=('R1','R2','R3','R4','RF','C1','VB','IT')
MAX_CALLS=300
MAX_SECONDS=600


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class BudgetExhausted(RuntimeError):pass
class QualifiedPointFound(RuntimeError):pass


def refine(proposal_path, qualification, output, *, cross_candidates=(), model=None,
           spiral_model=None, max_calls=MAX_CALLS, seconds=MAX_SECONDS):
    if not 3 <= max_calls <= MAX_CALLS or not 0 < seconds <= MAX_SECONDS:
        raise ValueError('Use 3..300 SPICE calls and at most 600 seconds')
    Q, OUT = Path(qualification).resolve(), Path(output).resolve()
    proposal_path = Path(proposal_path).resolve()
    model = Path(model or ROOT/'models/transformer.pt').resolve()
    spiral_model = Path(spiral_model or ROOT/'models/spiral.pt').resolve()
    cross_candidates = [Path(path).resolve() for path in cross_candidates]
    torch.set_num_threads(min(4, BUDGET))
    OUT.mkdir(exist_ok=False)
    original=W.read(proposal_path)
    rejected=W.read(Q/'final_design.json')
    provenance=W.read(Q/'qualification_inputs.json')
    if (rejected['strict_feasible'] or rejected['params']!=original['params']
            or rejected['geometry']!=original['geometry']
            or rejected['spiral_geometries']!=original['spiral_geometries']
            or provenance['proposal_sha256']!=sha(proposal_path)
            or provenance['joint_binding_sha256']!=original['joint_binding_sha256']):
        raise ValueError('Refinement requires this proposal to fail only circuit acceptance')
    if rejected['qualification_inputs_sha256']!=sha(Q/'qualification_inputs.json'):
        raise ValueError('Original qualification provenance changed')
    from joint_passives import joint_geometry
    import terminal_policy as TP
    TP.validate_entry(original, proposal_path, proposal_path.read_bytes())
    if joint_geometry(original) != rejected['spiral_geometries']:
        raise ValueError('Original proposal spiral binding changed')
    if original['xmodel_sha256'] != sha(model) or original['spiral_model_sha256'] != sha(spiral_model):
        raise ValueError('Refinement model weights differ from the original proposal')
    for key in ('network_quality',):
        if not rejected[key]['eligible_for_optimization']:
            raise ValueError('Refinement requires physically eligible raw networks')
    if not all(row['eligible_for_optimization'] for row in rejected['spiral_network_quality'].values()):
        raise ValueError('Refinement requires physically eligible spiral networks')
    raw_paths={};passive_evidence={}
    for tag,nports in (('transformer',4),('L1',2),('LB',2)):
        suffix=f'.s{nports}p';meta=W.read(Q/(tag+'.json'));definition=W.read(Q/(tag+'.ports.json'))
        if (meta['status']!='complete' or meta['nports']!=nports or not meta['all_ports_excited']
                or meta['energy_db']!=-50 or meta['margin_um']!=200
                or sha(Q/(tag+'.gds'))!=meta['gds_sha256']
                or sha(Q/(tag+suffix))!=meta['response_sha256']
                or provenance['network_sha256'][tag]!=meta['response_sha256']
                or sha(Q/(tag+'.ports.json'))!=meta['port_definition_sha256']):
            raise ValueError('Raw EM certificate/GDS/network evidence changed: '+tag)
        validate_port_coverage(Q/(tag+'.gds'),definition)
        net=rf.Network(str(Q/(tag+suffix)))
        if not M.network_quality(net)['eligible_for_optimization']:
            raise ValueError('Raw network is ineligible: '+tag)
        np.testing.assert_allclose(net.f,np.arange(1001)*1e8,rtol=0,atol=1.)
        raw_paths[tag]=Q/(tag+suffix)
        passive_evidence[tag]=dict(certificate_sha256=sha(Q/(tag+'.json')),network_sha256=sha(Q/(tag+suffix)),gds_sha256=sha(Q/(tag+'.gds')))
    policy=V.policy_from_pdk(ROOT/'code',search_buffer_v=.001)
    import campaign_history as H
    files = [CODE/name for name in H.SOURCE_FILES]
    files += [model, spiral_model, ROOT/'data/active_search_domain.json',
              active_spiral_domain(), proposal_path,
              Q/'qualification_inputs.json', Q/'final_design.json',
              Path(policy['model_card_path'])]
    files += cross_candidates
    for tag,nports in (('transformer',4),('L1',2),('LB',2)):
        files += [Q/(tag+suffix) for suffix in ('.json','.ports.json','.gds',f'.s{nports}p')]
    binary = os.environ.get('TIA_NGSPICE_BIN') or shutil.which('ngspice')
    if not binary:raise RuntimeError('The ngspice binary is required')
    files.append(Path(binary))
    bound_files = {str(path):sha(path) for path in files}
    def verify_bound_evidence():
        for path,digest in bound_files.items():
            if sha(path)!=digest:raise ValueError('Refinement source/raw-network evidence changed: '+path)
    started=time.monotonic();deadline=started+seconds
    original_subprocess=T.subprocess
    original_bv=T.BV_CE
    def timed_run(*args,**kwargs):
        remaining=deadline-time.monotonic()
        if remaining<=.5:raise BudgetExhausted('Refinement wall-clock deadline reached')
        kwargs['timeout']=min(float(kwargs.get('timeout',600)),remaining)
        try:return original_subprocess.run(*args,**kwargs)
        except subprocess.TimeoutExpired:
            if time.monotonic()>=deadline-.5:raise BudgetExhausted('Refinement wall-clock deadline reached')
            raise
    bounds=F.active_space('123',ROOT/'data/active_search_domain.json')
    base=copy.deepcopy(original['params']);geometry=original['geometry']
    for key,value in (('N1',2),('N2',2),('N3',3)):
        if base[key]!=value:raise ValueError('Fixed transistor multiplicity changed')
    def pack(params):
        z=[]
        for key in KEYS:
            kind,lo,hi=bounds[key];value=params[key]
            if not lo<=value<=hi:raise ValueError('Active parameter lies outside original bounds')
            z.append((np.log(value/lo)/np.log(hi/lo))if kind=='log'else(value-lo)/(hi-lo))
        return np.asarray(z)
    def unpack(z):
        params=copy.deepcopy(base)
        for key,value in zip(KEYS,np.clip(np.asarray(z),0,1)):
            kind,lo,hi=bounds[key]
            params[key]=float(lo*np.exp(value*np.log(hi/lo))if kind=='log'else lo+value*(hi-lo))
        return params
    raw_nets=[rf.Network(str(raw_paths[tag]))for tag in ('transformer','L1','LB')]
    raw_models=[M.circuit_model(net,[3,2,0,1]if i==0 else None,step_ghz=1.)for i,net in enumerate(raw_nets)]
    predictor=F.DirectPredictor(model)
    spirals=SpiralModels(spiral_model,active_spiral_domain())
    ann_models=[('sp',predictor.freq,predictor.predict([geometry])[0])]
    ann_models += [('sp',spirals.freq,s)for s in spirals.predict(spirals.geometries(base))]
    counts=dict(raw_1GHz=0,ANN_1GHz=0,raw_dense=0)
    history=[];cache={};qualified=None
    binding=dict(method='EM-guided active refinement after current random co-optimization',
        source_proposal_sha256=sha(proposal_path),initial_params_sha256=hashlib.sha256(json.dumps(base,sort_keys=True).encode()).hexdigest(),
        same_random_search_active_cross_replays_sha256=[sha(path) for path in cross_candidates],
        original_failed_qualification_sha256=sha(Q/'final_design.json'),passive_evidence=passive_evidence,
        code_sha256=sha(__file__),active_keys=KEYS,active_bounds={key:bounds[key]for key in KEYS},
        coarse_EM_search_bandwidth_minimum_ghz=32.2,coarse_EM_peaking_maximum_db=.99,
        final_EM_bandwidth_comparison='strictly greater than32GHz',final_ANN_minimum_ghz=34.,
        maximum_total_SPICE_calls=max_calls,ANN_and_EM_evaluations_counted_separately=True,
        wall_clock_limit_seconds=seconds,bound_input_sha256=bound_files,
        fixed_geometry=True,model_weights_unchanged=True,no_new_EM_simulations=True,notebook_updated=False)
    W.write(OUT/'binding.json',binding)
    def save(status):
        W.write(OUT/'progress.json',dict(status=status,counts=counts,total_SPICE_calls=sum(counts.values()),evaluations=len(history),updated_utc=datetime.now(timezone.utc).isoformat()))
        W.write(OUT/'history.json',history)
    def call(params,models,ann):
        if time.monotonic()>=deadline-.5:raise BudgetExhausted('Refinement wall-clock deadline reached')
        if sum(counts.values())>=max_calls:raise BudgetExhausted('Recorded SPICE budget exhausted')
        counts['ANN_1GHz'if ann else'raw_1GHz']+=1
        if ann:
            restore=VRun.install_policy_hooks(F,policy)
            try:row=F.run_candidate((params,geometry,models,'123',1.,'tia_sim:run',.2))
            finally:restore()
        else:
            restore=VRun.install_policy_hooks(F,policy)
            try:row=F.run_candidate((params,geometry,models,'123',1.,'tia_sim:run',0.))
            finally:restore()
        if row['status']=='failed'and row.get('error'):
            if row['error'].startswith('BudgetExhausted:')and time.monotonic()>=deadline-.5:
                raise BudgetExhausted('Refinement wall-clock deadline reached')
            raise RuntimeError(row['error'])
        return row
    def evaluate(z):
        nonlocal qualified
        params=unpack(z);key=json.dumps(params,sort_keys=True,allow_nan=False)
        if key in cache:return cache[key]
        if sum(counts.values())+3>max_calls:raise BudgetExhausted('Reserve one dense verification within the total budget')
        raw=call(params,raw_models,False);ann=call(params,ann_models,True)
        rc=np.asarray(raw['constraints'],float);ac=np.asarray(ann['constraints'],float)
        if raw['status']=='complete':
            rc[1]=(32.2-raw['metrics_surrogate']['bw_ghz'])/5.
            rc[2]=raw['metrics_surrogate']['peak_db']-.99
        if rc.shape!=(16,)or ac.shape!=(16,)or not np.isfinite(np.r_[rc,ac]).all():
            raise ValueError('Invalid paired-constraint record')
        combined=np.maximum(rc,ac)
        row=dict(params=params,z=np.asarray(z).tolist(),raw_1GHz=raw,ANN_1GHz=ann,
            raw_search_constraints=rc.tolist(),joint_constraints=combined.tolist(),
            objective=-raw['metrics_surrogate']['bw_ghz']/32.2 if raw['status']=='complete' else 1e6)
        cache[key]=row;history.append(row);save('refining')
        if np.all(combined<=0)and sum(counts.values())<max_calls:
            counts['raw_dense']+=1
            response,metrics,audit=W.circuit(geometry,params,raw_paths['transformer'],raw_paths['L1'],raw_paths['LB'])
            passed=bool(W.accepted_circuit(params,response,audit))
            row['raw_dense']=dict(metrics=metrics,voltage_audit=audit,passed=passed)
            save('dense_verification')
            if passed:
                verify_bound_evidence()
                np.savez_compressed(OUT/'response.npz',**{k:response[k]for k in ('f','zt','fn','inoise')})
                qualified=dict(status='qualified',params=params,geometry=geometry,spiral_geometries=original['spiral_geometries'],
                    metrics_surrogate=ann['metrics_surrogate'],metrics_em=metrics,voltage_audit=audit,
                    binding_sha256=sha(OUT/'binding.json'),passive_evidence=passive_evidence,
                    independent_complete_raw_networks=True,ANN_final_point_replayed=True,
                    original_proposal_not_claimed_qualified=True,notebook_updated=False)
                W.write(OUT/'final_design.json',qualified);save('qualified')
                raise QualifiedPointFound('Both fresh fidelity checks passed')
        return row
    x0=pack(base)
    save('starting')
    try:
        T.subprocess=SimpleNamespace(run=timed_run)
        evaluate(x0)
        # First reuse only active settings from this same random-search pool;
        # all three geometries and every resulting ANN/raw response stay fixed/replayed.
        for path in cross_candidates[:4]:
            candidate = W.read(path)
            if candidate['stage_contract']['plan_sha256'] != original['stage_contract']['plan_sha256']:
                raise ValueError('Cross-replay candidate belongs to a different random campaign')
            joint_geometry(candidate)
            evaluate(pack(dict(base,**{key:candidate['params'][key]for key in KEYS})))
        def objective(z):return evaluate(z)['objective']
        def constraints(z):return -np.asarray(evaluate(z)['joint_constraints'])
        result=minimize(objective,x0,method='SLSQP',bounds=[(0.,1.)]*8,
            constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=20,eps=1e-3,ftol=1e-8,disp=False))
        W.write(OUT/'optimizer_result.json',dict(success=bool(result.success),status=int(result.status),message=str(result.message),iterations=int(result.nit)))
    except QualifiedPointFound:
        pass
    except BudgetExhausted as error:
        W.write(OUT/'budget_stop.json',dict(reason=str(error),counts=counts))
    finally:
        T.subprocess=original_subprocess
        T.BV_CE=original_bv
    verify_bound_evidence()
    if not qualified:
        save('no_jointly_qualified_point_in_budget')
        return None
    return materialize(proposal_path, Q, OUT, original, rejected, provenance, qualified)


def materialize(proposal_path, qualification, output, original, rejected, provenance, result):
    """Keep the initial rejection separate and bind a new final proposal."""
    from joint_passives import proposal_binding, joint_geometry
    import terminal_policy as TP
    history = W.read(output/'history.json')
    matching = [row for row in history if row['params']==result['params'] and row.get('raw_dense',{}).get('passed')]
    if len(matching)!=1:raise ValueError('Missing unique final paired replay')
    ann = matching[0]['ANN_1GHz']
    if any(result['params'][key]!=value for key,value in original['params'].items() if key not in KEYS):
        raise ValueError('Refinement changed a passive geometry or fixed device size')
    shutil.copy2(proposal_path, output/'initial_proposal.json')
    shutil.copy2(qualification/'final_design.json', output/'initial_design.json')
    metadata = dict(schema='tia-em-active-refinement-v1',
        initial_proposal_sha256=sha(output/'initial_proposal.json'),
        initial_assessment_sha256=sha(output/'initial_design.json'),
        binding_sha256=sha(output/'binding.json'),history_sha256=sha(output/'history.json'),
        changed_variables=list(KEYS),source_trial=original.get('trial'))
    proposal = copy.deepcopy(original)
    for key in ('sampler_trial','evaluation_id','origin_stage'):
        proposal.pop(key,None)
    proposal.update(params=result['params'],metrics_surrogate=ann['metrics_surrogate'],
        constraints=ann['constraints'],objective=ann['objective'],feasible=True,violation=0.,
        voltage_audit=result['voltage_audit'],source='paired_ANN_EM_active_refinement',
        candidate_origin='EM_guided_active_refinement',trial=None,em_refinement=metadata)
    proposal.update(TP.markers())
    proposal['joint_binding_sha256']=proposal_binding(proposal)
    joint_geometry(proposal)
    W.write(output/'qualified_proposal.json',proposal)
    for tag,nports in (('transformer',4),('L1',2),('LB',2)):
        for suffix in ('.gds',f'.s{nports}p','.json','.ports.json','.geometry.json','.log','.em.log'):
            path=qualification/(tag+suffix)
            if path.is_file():shutil.copy2(path,output/path.name)
    validate_network_identity(output,W.read(output/'binding.json'))
    inputs=copy.deepcopy(provenance)
    inputs.update(params=result['params'],proposal_sha256=sha(output/'qualified_proposal.json'),
        joint_binding_sha256=proposal['joint_binding_sha256'],em_refinement=metadata,
        qualification_code_sha256=sha(__file__))
    W.write(output/'qualification_inputs.json',inputs)
    final=dict(rejected,params=result['params'],metrics_em=result['metrics_em'],
        metrics_surrogate=result['metrics_surrogate'],voltage_audit=result['voltage_audit'],
        strict_feasible=True,em_refinement=metadata,
        qualification_inputs_sha256=sha(output/'qualification_inputs.json'))
    W.write(output/'final_design.json',final)
    return dict(proposal=output/'qualified_proposal.json',qualification=output)


def validate_network_identity(directory,binding):
    """Refinement must reuse the exact three certified raw networks and GDSs."""
    directory=Path(directory)
    for tag,nports in (('transformer',4),('L1',2),('LB',2)):
        expected=binding['passive_evidence'][tag]
        for suffix,key in (('.json','certificate_sha256'),('.gds','gds_sha256'),
                           (f'.s{nports}p','network_sha256')):
            if sha(directory/(tag+suffix))!=expected[key]:
                raise ValueError('Refinement replaced a certified passive: '+tag+suffix)


def validate_refinement(proposal, initial, assessment, binding, history):
    """Check identities and paired metrics without running a circuit."""
    from joint_passives import joint_geometry
    import terminal_policy as TP
    TP.require_markers(proposal)
    TP.require_integer_geometry(proposal['geometry'])
    if proposal.get('trial') is not None or proposal.get('candidate_origin')!='EM_guided_active_refinement':
        raise ValueError('The refined point must have a separate identity from a TPE trial')
    if tuple(proposal['em_refinement']['changed_variables'])!=KEYS:
        raise ValueError('Refinement variable set changed')
    if (binding['source_proposal_sha256']!=proposal['em_refinement']['initial_proposal_sha256']
            or binding['original_failed_qualification_sha256']!=proposal['em_refinement']['initial_assessment_sha256']):
        raise ValueError('Refinement binding refers to different source evidence')
    for key in ('geometry','spiral_geometries','permutation','xmodel_sha256','spiral_model_sha256'):
        if proposal[key]!=initial[key]:raise ValueError('A passive/model identity changed: '+key)
    if any(proposal['params'].get(key)!=value for key,value in initial['params'].items() if key not in KEYS):
        raise ValueError('A fixed device or passive variable changed')
    if (assessment['params']!=initial['params'] or assessment['strict_feasible'] is not False
            or assessment['geometry']!=initial['geometry']
            or assessment['spiral_geometries']!=initial['spiral_geometries']):
        raise ValueError('The preserved original assessment is not the rejected proposal')
    joint_geometry(proposal)
    rows=[row for row in history if row['params']==proposal['params'] and row.get('raw_dense',{}).get('passed')]
    if len(rows)!=1:raise ValueError('Missing unique paired final-point replay')
    row=rows[0];ann=row['ANN_1GHz'];dense=row['raw_dense']['metrics']
    values=np.asarray(ann['constraints'],float)
    if (values.shape!=(16,) or not np.isfinite(values).all() or np.any(values>0)
            or not ann['feasible'] or ann['metrics_surrogate']['bw_ghz']<34.
            or proposal['params']!=row['raw_1GHz']['params']
            or proposal['params']!=ann['params']
            or proposal['metrics_surrogate']!=ann['metrics_surrogate']
            or proposal['constraints']!=ann['constraints']):
        raise ValueError('The final ANN/raw pair disagrees with the refined proposal')
    if not A.feasible(proposal['params'],dense) or dense['bw_ghz']<=32.:
        raise ValueError('The dense final point violates a physical circuit limit')
    if not row['raw_dense']['voltage_audit']['qualified']:
        raise ValueError('The dense final operating point fails VCE checks')
    if (tuple(binding['active_keys'])!=KEYS or not binding['fixed_geometry']
            or not binding['model_weights_unchanged']):
        raise ValueError('Refinement did not preserve the fixed-geometry contract')
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposal',type=Path,required=True)
    parser.add_argument('--qualification',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if refine(args.proposal,args.qualification,args.output) is None:raise SystemExit(2)
