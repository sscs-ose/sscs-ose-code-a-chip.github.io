"""Portable entrypoints for data generation, surrogate fitting and TIA verification."""
from environment import spiral_domain as active_spiral_domain
from environment import ROOT, CODE, configure
BUDGET = configure()
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import terminal_policy as TP


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def canonical(geometry):
    import xfmr_schema as XG
    return json.dumps(XG.normalize(geometry),sort_keys=True,separators=(',',':'))


@contextmanager
def independent_geometry():
    import expanded_direct_surrogate_flow as F
    manifest=read(ROOT/'data/training_manifest.json')
    used={row['canonical_key'] for row in manifest['samples'] if row['split'] in ('train','val','test')}
    original=F.validate_physical_candidate
    def checked(geometry):
        if canonical(geometry) in used:
            raise ValueError('Candidate geometry belongs to a model partition')
        return original(geometry)
    F.validate_physical_candidate=checked
    try:
        yield
    finally:
        F.validate_physical_candidate=original


def optimize(output, model=None, trials=6000, jobs=4, seed=0, *, domain=None,
             spiral_model=None, spiral_domain=None, active_domain=None, startup_trials=256, campaign_record=None, stage_index=None, allow_no_candidate=False):
    import torch
    import run_surrogate_vce1p6 as wrapper
    if not 1<=jobs<=BUDGET or trials<1:
        raise ValueError(f'Use positive trials and at most {BUDGET} circuit workers')
    model=Path(model or ROOT/'models/transformer.pt').resolve()
    checkpoint=torch.load(model,map_location='cpu',weights_only=False)
    if (checkpoint.get('feature_version')!=3 or len(checkpoint['xmin'])!=14
            or checkpoint.get('augmentation') is not None):
        raise ValueError('Optimization requires the unaugmented fourteen-input checkpoint')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    arguments=['--root',str(CODE),'--xmodel',str(model),
               '--domain',str(domain or ROOT/'data/search_domain.json'),
               '--geometry',str(ROOT/'data/base_geometry.json'),
               '--active-domain',str(active_domain or ROOT/'data/active_search_domain.json'),
               '--startup-trials',str(startup_trials),
               '--work-dir',str(output),'--trials',str(trials),'--jobs',str(jobs),'--seed',str(seed),
               '--optimization-step-ghz','1','--gain-margin-db','0.2','--permutation','3,2,0,1',
               '--voltage-policy',str(output/'voltage_policy.json')]
    arguments+=['--optimize-spirals','--smodel',str(spiral_model or ROOT/'models/spiral.pt'),
                '--spiral-domain',str(active_spiral_domain(spiral_domain))]
    if campaign_record is not None:
        arguments+=['--campaign-record',str(campaign_record),'--stage-index',str(stage_index)]
    original_argv=sys.argv
    sys.argv=['run_surrogate_vce1p6.py']+arguments
    try:
        with independent_geometry():
            status=wrapper.main()
        result=read(output/'result.json')
        if status and not (allow_no_candidate and status==2 and result.get('status')=='no_candidate'):
            raise RuntimeError('The search produced no feasible candidate proposal')
        return result
    finally:
        sys.argv=original_argv


def require_circuit_tools():
    installed=os.environ.get('TIA_NGSPICE_BIN') or shutil.which('ngspice')
    if not installed or not Path(installed).is_file():
        raise RuntimeError('Install ngspice with XSPICE/OSDI, or set TIA_NGSPICE_BIN')
    from environment import pdk_root
    model_root=pdk_root()/'ihp-sg13g2/libs.tech/ngspice/osdi'
    required=('psp103','psp103_nqs','r3_cmc','mosvar','cap_cmomi','cap_cmomf')
    if any(not (model_root/(name+'.osdi')).is_file() for name in required):
        raise RuntimeError('Compile the installed PDK models with tools/compile_models.sh')


def circuit(geometry,params,transformer_path=None,l1_path=None,lb_path=None):
    import skrf as rf
    import tia_sim as T
    import multiturn_experiment as M
    import vce_policy as V
    from expanded_direct_surrogate_flow import circuit_grid
    if l1_path is None or lb_path is None:
        raise ValueError('Circuit replay requires explicit L1 and Lb networks.')
    require_circuit_tools()
    policy=V.policy_from_pdk(CODE,search_buffer_v=.001)
    V.apply_voltage_policy(T,policy)
    xf=None if transformer_path is None else M.circuit_model(rf.Network(str(transformer_path)),[3,2,0,1])
    l1=M.circuit_model(rf.Network(str(l1_path)))
    lb=M.circuit_model(rf.Network(str(lb_path)))
    with circuit_grid(.1):
        result=T.run(params,xf,l1,lb,'123')
    if result is None or not all(np.isfinite(result[key]) for key in T.SPEC):
        raise RuntimeError('Circuit evaluation failed or returned nonfinite metrics')
    return result,M.measured_metrics(T,params,result),V.audit_op(result['op'],policy)




def layouts(output, geometry=None):
    import direct_generator_snapshot as G
    import multiturn_experiment as M
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    final=read(ROOT/'data/final_design.json')
    G.save_geometry(geometry or final['geometry'],output/'transformer.gds')
    for name in ('L1','LB'):
        M.make_spiral(output/(name+'.gds'),name,final['spiral_geometries'][name])
    print('Generated transformer, L1 and Lb GDS layouts')


def dataset(kind, output, limit=None):
    import direct_generator_snapshot as G
    import multiturn_experiment as M
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    if kind=='transformer':
        rows=read(ROOT/'data/training_manifest.json')['samples']
        selected=rows if limit is None else rows[:limit]
        for row in selected:
            G.save_geometry(row['geometry'],output/(str(row['index'])+'.gds'))
    else:
        rows=read(ROOT/'data/spiral_geometry.json')['samples']
        selected=rows if limit is None else rows[:limit]
        for row in selected:
            M.make_spiral(output/(str(row['index'])+'.gds'),row['index'],row['geometry'])
    print(f'Generated {len(selected)} checked {kind} layouts')


def em(gds, output, nports=4, threads=16, port_metal=None):
    if not 1<=threads<=BUDGET:
        raise ValueError(f'EM threads must be in 1..{BUDGET}')
    gds=Path(gds).resolve();output=Path(output).resolve()
    if output.exists():
        raise FileExistsError('Preserve existing EM results and choose a fresh output file')
    from em_port_metadata import resolve_port_metadata,validate_port_coverage,preserve_geometry_metadata
    receipt=output.with_suffix('.ports.json')
    if receipt.exists() or output.with_suffix('.json').exists() and output.with_suffix('.json')!=gds.with_suffix('.json'):
        raise FileExistsError('Preserve existing EM metadata and choose a fresh output file')
    preserve_geometry_metadata(gds,output)
    definition=resolve_port_metadata(gds,CODE,port_metal,nports)
    definition['ports']=validate_port_coverage(gds,definition)
    output.parent.mkdir(parents=True,exist_ok=True)
    write(receipt,definition)
    try:
        import openEMS,CSXCAD
    except ImportError as error:
        raise RuntimeError('Install openEMS/CSXCAD with tools/setup_environment.sh') from error
    name='submission_'+hashlib.sha256((gds.name+str(output)).encode()).hexdigest()[:12]
    env=dict(os.environ,OPENEMS_THREADS=str(threads),EM_SKIP_PORT='0',EM_ENERGY='-50',EM_MARGIN='200')
    command=[sys.executable,str(CODE/'simulator_openems.py'),'-g',str(gds),'-s',str(output),
             '-x',str(CODE/'SG13G2.xml'),'-m',name,'-r',str(CODE),'--nports',str(nports),
             '--port-metal',definition['port_layers'][0]]
    em_log=output.with_suffix('.em.log')
    with em_log.open('w') as stream:
        subprocess.run(command,cwd=CODE,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    import multiturn_experiment as M
    M.validate_network(output,nports)
    write(output.with_suffix('.json'),dict(status='complete',nports=nports,all_ports_excited=True,
        frequency_ghz=[0,100],frequency_step_ghz=.1,energy_db=-50,margin_um=200,threads=threads,
        gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),
        port_layers=definition['port_layers'],reference_layer='Metal4',
        port_definition_file=receipt.name,port_definition_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
        em_log_file=em_log.name,
        response_sha256=hashlib.sha256(output.read_bytes()).hexdigest()))
    print(f'Completed independent {nports}-port EM evaluation')


def accepted_circuit(params,metrics,audit):
    import active_constraint_search as A
    return bool(A.feasible(params,metrics) and metrics['bw_ghz']>A.LIMITS['bw_ghz'] and audit['qualified'])


def replay_submitted(proposal,model,spiral_model,domain):
    """Recompute the submitted point's ANN circuit response without archived files."""
    import expanded_direct_surrogate_flow as F
    import run_surrogate_vce1p6 as R
    import vce_policy as V
    from joint_passives import SpiralModels
    require_circuit_tools()
    predictor=F.DirectPredictor(model)
    spirals=SpiralModels(spiral_model,domain)
    models=[('sp',predictor.freq,predictor.predict([proposal['geometry']])[0])]
    models += [('sp',spirals.freq,s) for s in spirals.predict(spirals.geometries(proposal['params']))]
    policy=V.policy_from_pdk(CODE,search_buffer_v=.001)
    import tia_sim as T
    old_bv=T.BV_CE;restore=R.install_policy_hooks(F,policy)
    try:
        row=F.run_candidate((proposal['params'],proposal['geometry'],models,'123',1.,'tia_sim:run',.2))
    finally:
        restore();T.BV_CE=old_bv
    if row['status']!='complete' or not row['feasible']:
        raise RuntimeError('The submitted point failed its fresh ANN circuit replay')
    for key in ('bw_ghz','zt_dbohm','peak_db','gd_pp_ps','noise_pa','power_mw'):
        np.testing.assert_allclose(row['metrics_surrogate'][key],proposal['metrics_surrogate'][key],rtol=1e-7,atol=1e-8)
    return row


def qualify(proposal,output,threads=16,model=None,spiral_model=None,spiral_domain=None):
    import active_constraint_search as A
    import direct_generator_snapshot as G
    import multiturn_experiment as M
    import skrf as rf
    proposal_path=Path(proposal)
    proposal_bytes=proposal_path.read_bytes()
    proposal=json.loads(proposal_bytes)
    TP.validate_entry(proposal,proposal_path,proposal_bytes)
    from joint_passives import joint_geometry,SpiralModels
    spiral_geometry=joint_geometry(proposal)
    if spiral_geometry is None:raise ValueError('Qualification requires a joint transformer/L1/Lb proposal')
    smodel=Path(spiral_model or ROOT/'models/spiral.pt')
    sdomain=active_spiral_domain(spiral_domain)
    if (proposal['spiral_model_sha256']!=hashlib.sha256(smodel.read_bytes()).hexdigest()
            or proposal['spiral_domain_sha256']!=hashlib.sha256(sdomain.read_bytes()).hexdigest()):
        raise ValueError('Joint proposal and spiral model/domain do not match')
    spiral_predictor=SpiralModels(smodel,sdomain)
    geometries=spiral_predictor.geometries(proposal['params'])
    if geometries!=[spiral_geometry[tag] for tag in ('L1','LB')]:raise ValueError('Spiral parameter and geometry mismatch')
    spiral_predictor.validate(geometries)
    if proposal.get('spiral_source_basis')!=spiral_predictor.source_basis(geometries):
        raise ValueError('Proposal ANN extrapolation source basis changed')
    if 'stage_contract' in proposal:
        contract=proposal['stage_contract'];index=contract['stage']
        if index not in (0,1,2) or contract['variables']!=(22,23,25)[index]:
            raise ValueError('Unknown staged-search variable set')
        expected=f'data/search_stage_{index:02d}.json'
        if (contract['domain_file']!=expected
                or proposal['data_domain_sha256']!=hashlib.sha256((ROOT/expected).read_bytes()).hexdigest()):
            raise ValueError('Proposal and transformer stage domain do not match')
    model=Path(model or ROOT/'models/transformer.pt')
    if proposal.get('xmodel_sha256')!=hashlib.sha256(model.read_bytes()).hexdigest():
        raise ValueError('Proposal and transformer checkpoint do not match')
    if not proposal.get('feasible') or proposal.get('permutation')!=[3,2,0,1]:
        raise ValueError('Qualification requires a feasible proposal with the recorded circuit port order')
    constraints=np.asarray(proposal.get('constraints',[]),dtype=float)
    if constraints.shape!=(16,) or not np.isfinite(constraints).all() or np.any(constraints>0):
        raise ValueError('Qualification requires all sixteen surrogate constraints to pass')
    if proposal.get('proposal_role')=='submitted_final_design':
        replay_submitted(proposal,model,smodel,sdomain)
    with independent_geometry():
        import expanded_direct_surrogate_flow as F
        F.validate_physical_candidate(proposal['geometry'])
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    G.save_geometry(proposal['geometry'],output/'transformer.gds')
    terminal_check=TP.verify_new_layout(proposal['geometry'],output/'transformer.gds')
    from xfmr_schema import port_layers
    layers=port_layers(proposal['geometry'])
    if len(set(layers))!=1:raise ValueError('Mixed transformer port landing metals are unsupported')
    spiral_quality={}
    if not 3<=threads<=BUDGET:raise ValueError('Parallel joint qualification requires 3..16 shared cores')
    for tag in ('L1','LB'):
        M.make_spiral(output/(tag+'.gds'),tag,spiral_geometry[tag])
    import openEMS,CSXCAD
    from concurrent.futures import ThreadPoolExecutor
    coil_threads=max(1,threads//4)
    jobs=[(output/'transformer.gds',output/'transformer.s4p',4,threads-2*coil_threads,layers[0])]
    jobs += [(output/(tag+'.gds'),output/(tag+'.s2p'),2,coil_threads,'TopMetal2') for tag in ('L1','LB')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(em,*job) for job in jobs]
        for future in futures:future.result()
    for tag in ('L1','LB'):
        spiral_quality[tag]=M.network_quality(rf.Network(str(output/(tag+'.s2p'))))
    l1_path,lb_path=output/'L1.s2p',output/'LB.s2p'
    network_paths=dict(transformer=output/'transformer.s4p',L1=l1_path,LB=lb_path)
    inputs=dict(schema_version=1,
        bandwidth_targets_ghz=dict(surrogate=34.,EM=A.LIMITS['bw_ghz']),
        acceptance_evaluator_sha256={name:hashlib.sha256((CODE/name).read_bytes()).hexdigest() for name in ('active_constraint_search.py','tia_sim.py')},
        spiral_source_basis=proposal.get('spiral_source_basis'),terminal_positions=terminal_check,
        terminal_policy_mode=TP.SCHEMA,
        terminal_policy_source_sha256=hashlib.sha256(Path(TP.__file__).read_bytes()).hexdigest(),
        proposal_schema=proposal.get('proposal_schema'),terminal_position_policy=proposal.get('terminal_position_policy'),
        proposal_sha256=hashlib.sha256(proposal_bytes).hexdigest(),
        joint_binding_sha256=proposal.get('joint_binding_sha256'),stage_contract=proposal.get('stage_contract'),
        geometry=proposal['geometry'],spiral_geometries=spiral_geometry,params=proposal['params'],
        model_sha256=dict(transformer=proposal['xmodel_sha256'],spiral=proposal.get('spiral_model_sha256')),
        domain_sha256=dict(transformer=proposal.get('data_domain_sha256'),spiral=proposal.get('spiral_domain_sha256')),
        transformer_port_order=proposal['permutation'],spiral_port_order=[0,1],
        network_sha256={tag:hashlib.sha256(path.read_bytes()).hexdigest() for tag,path in network_paths.items()},
        qualification_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(output/'qualification_inputs.json',inputs)
    response,metrics,audit=circuit(proposal['geometry'],proposal['params'],output/'transformer.s4p',l1_path,lb_path)
    quality=M.network_quality(rf.Network(str(output/'transformer.s4p')))
    qualified=bool(accepted_circuit(proposal['params'],response,audit) and quality['eligible_for_optimization']
                   and all(item['eligible_for_optimization'] for item in spiral_quality.values()))
    np.savez_compressed(output/'response.npz',**{k:response[k] for k in ('f','zt','fn','inoise')})
    write(output/'final_design.json',dict(geometry=proposal['geometry'],params=proposal['params'],metrics_em=metrics,
        spiral_source_basis=proposal.get('spiral_source_basis'),
        passive_final_basis='three_new_raw_EM_networks',
        voltage_audit={k:v for k,v in audit.items() if 'sha256' not in k},network_quality=quality,
        spiral_geometries=spiral_geometry,spiral_network_quality=spiral_quality,strict_feasible=qualified,
        qualification_inputs='qualification_inputs.json',
        qualification_inputs_sha256=hashlib.sha256((output/'qualification_inputs.json').read_bytes()).hexdigest()))
    if not qualified:raise RuntimeError('The new proposal did not pass independent qualification')
    print('PASS: independent physical-network, circuit, bias and VCE checks')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='stage',required=True)
    check=sub.add_parser('check')
    mode=check.add_mutually_exclusive_group()
    mode.add_argument('--deep',action='store_true')
    mode.add_argument('--package-only',action='store_true')
    result=sub.add_parser('results');result.add_argument('--output',type=Path,default=ROOT/'runs/figures')
    result.add_argument('--result-root',type=Path,required=True)
    gen=sub.add_parser('layouts');gen.add_argument('--output',type=Path,required=True)
    data=sub.add_parser('dataset');data.add_argument('--kind',choices=('transformer','spiral'),required=True)
    data.add_argument('--output',type=Path,required=True);data.add_argument('--limit',type=int)
    opt=sub.add_parser('optimize');opt.add_argument('--output',type=Path,required=True)
    opt.add_argument('--model',type=Path);opt.add_argument('--trials',type=int,default=6000)
    opt.add_argument('--jobs',type=int,default=4);opt.add_argument('--seed',type=int,default=0)
    opt.add_argument('--domain',type=Path);opt.add_argument('--spiral-model',type=Path)
    opt.add_argument('--spiral-domain',type=Path);opt.add_argument('--active-domain',type=Path)
    opt.add_argument('--startup-trials',type=int,default=256)
    staged=sub.add_parser('optimize-staged');staged.add_argument('--output',type=Path,required=True)
    staged.add_argument('--trials',type=int,default=6000);staged.add_argument('--jobs',type=int,default=4)
    staged.add_argument('--seed',type=int,default=0);staged.add_argument('--model',type=Path)
    staged.add_argument('--spiral-model',type=Path)
    full=sub.add_parser('qualify');full.add_argument('--proposal',type=Path,required=True)
    full.add_argument('--output',type=Path,required=True);full.add_argument('--threads',type=int,default=min(16,BUDGET))
    full.add_argument('--model',type=Path)
    full.add_argument('--spiral-model',type=Path);full.add_argument('--spiral-domain',type=Path)
    field=sub.add_parser('em');field.add_argument('--gds',type=Path,required=True)
    field.add_argument('--output',type=Path,required=True);field.add_argument('--nports',type=int,choices=(2,4),default=4)
    field.add_argument('--threads',type=int,default=min(16,BUDGET))
    field.add_argument('--port-metal',choices=('TopMetal1','TopMetal2'))
    args=parser.parse_args()
    if args.stage=='check':
        from validate_submission import check
        check(args.deep,package_only=args.package_only)
    elif args.stage=='results':
        from results_figures import build
        build(args.output,root=args.result_root);print('Reconstructed response, eye and GDS figures')
    elif args.stage=='layouts':layouts(args.output)
    elif args.stage=='dataset':dataset(args.kind,args.output,args.limit)
    elif args.stage=='optimize':optimize(args.output,args.model,args.trials,args.jobs,args.seed,
        domain=args.domain,spiral_model=args.spiral_model,spiral_domain=args.spiral_domain,active_domain=args.active_domain,startup_trials=args.startup_trials)
    elif args.stage=='optimize-staged':
        from staged_search import run
        result=run(args.output,args.trials,args.jobs,args.seed,args.model,args.spiral_model)
        if result['status']!='awaiting_independent_em':raise SystemExit(2)
    elif args.stage=='em':em(args.gds,args.output,args.nports,args.threads,args.port_metal)
    elif args.stage=='qualify':qualify(args.proposal,args.output,args.threads,args.model,args.spiral_model,args.spiral_domain)


if __name__=='__main__':main()
