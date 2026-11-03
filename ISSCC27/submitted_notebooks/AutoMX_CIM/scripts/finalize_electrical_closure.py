"""Publish a completely executed, scoped prototype after current-run audits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,subprocess,sys
import nbformat

def finalize(root):
    root=Path(root).resolve();folder=root/'experiments/closure_20261028'
    def read(path):return json.loads(Path(path).read_text())
    execution=read(folder/'notebook_execution.json')
    assert execution['status']=='ALL_CODE_CELLS_EXECUTED'
    assert execution['executed_cells']==execution['code_cells'] and not execution['errors'] and not execution['empty_output_cells']
    from scripts.refresh_verified_notebook_frontmatter import refresh
    refresh(root)
    candidate=Path(execution['output']);book=nbformat.read(candidate,4)
    previous=nbformat.read(root/'AutoMX_CIM_Code_a_Chip.ipynb',4)
    assert {c.id for c in previous.cells}<={c.id for c in book.cells}
    retained=root/'data/intermediate_notebook_cell_ids.json'
    if retained.is_file():assert set(read(retained))<={c.id for c in book.cells},'Intermediate laboratory cells must remain'
    assert all(c.execution_count is not None and c.outputs for c in book.cells if c.cell_type=='code')
    assert not any(o.output_type=='error' for c in book.cells if c.cell_type=='code' for o in c.outputs)
    run=max((root/'runs').glob('fresh_*'));work=run/'electrical_closure';app=run/'priority_application'
    started=datetime.strptime(run.name.removeprefix('fresh_'),'%Y%m%d_%H%M%S_%f').replace(tzinfo=timezone.utc).timestamp()
    reports={name:read(work/path) for name,path in {
        'pulse':'pwm_final/verification.json','native':'electrical/verification.json',
        'replay':'native_replay/verification.json','convergence':'numerical_convergence/verification.json',
        'clock':'clock_activity/verification.json','power':'clock_aware_power/verification.json',
        'area':'controller_adc_area/verification.json','service':'application_service/verification.json',
        'second_configuration':'second_configuration/verification.json','quick':'quick_review/verification.json',
        'clean':'clean_environment/verification.json','presentation':'presentation.json'}.items()}
    pulse=reports['pulse'];assert len(pulse['measurements'])==64
    pulse_keys=('zero_code_ok','nonzero_full_swing','single_pulse_ok','unselected_lines_quiet','strict_width_order','strict_bitline_order','bitline_polarity_ok')
    failed_pulse_checks=[key for key in pulse_keys if not pulse[key]]
    assert len({(r['row'],r['negative'],r['magnitude']) for r in pulse['measurements']})==64
    assert all(Path(r['folder']).is_relative_to(run) for r in pulse['measurements'])
    native=reports['native'];assert native['status']=='PASS' and len(native['frames'])==6 and native['logical_conversions']==384
    assert native['nominal_matched_sum_wrong']==native['partial_decode_mismatches']==0
    routed=native['contract']['stimulus']=='routed measured PWM'
    if routed:
        assert not failed_pulse_checks,failed_pulse_checks
        core=read(work/'physical_range_core/routing_views/verification.json')
        assert core['magic_drc']==0 and core['transistor_lvs']=='PASS' and core['ground_access_gds_coverage']
        assert core['native_compaction_verification']['status']=='PASS'
        parent=read(work/'physical_parent/verification.json');assert parent['status']=='PASS'
        timing=parent['outputs']['nominal_timing'];assert min(timing['setup_slack_ns'],timing['hold_slack_ns'])>=0
        assert all(g['unresolved']==0 for g in read(work/'electrical/pvt.json')['groups'])
        selected=next(g for g in read(work/'electrical/settling.json') if g['settle_clocks']==16)
        assert selected['wrong']==selected['unresolved']==0
    else:
        assert native['contract']['stimulus']=='ideal 50ps unit; analog/timing diagnostic only'
    replay=reports['replay'];assert replay['status']=='PASS' and replay['frames']==6 and replay['native_adc_transactions']==384
    assert replay['max_control_timing_error_ns']==0 and replay['mismatches']==0
    assert reports['convergence']['status']=='PASS'
    power=reports['power'];assert power['status']=='PASS' and len(power['results'])==5
    assert all(r['gate_output_mismatches']==0 for r in power['results'])
    for name in ('area','service','second_configuration','quick','clean','presentation'):assert reports[name]['status']=='PASS',name
    render=read(work/'final_top_render/verification.json')
    assert render['status']=='PASS' and render['overview_repeat_pixel_equal']
    wake=read(work/'idle_wake_service/verification.json');idle=read(work/'idle_boot/verification.json')
    assert wake['status']==idle['status']=='PASS'
    assert reports['clock']['status']=='PASS'
    assert power['gating_child_energy_reduction_percent']>15
    enable=read(work/'icg_enable_timing/verification.json')
    assert enable['status']=='PASS' and min(enable['setup_slack_ns'],enable['hold_slack_ns'])>=0
    figures=reports['presentation']['figures'];assert len(figures)==6 and len(reports['presentation']['tables'])==4
    for path in [*(work/'pwm_final').glob('row*/measured.json'),work/'electrical/verification.json',*(Path(p) for p in figures)]:
        assert path.resolve().is_relative_to(run) and path.stat().st_mtime>=started-2,path
    evaluation=None
    if (work/'margin_budget.json').exists():
        budget=read(work/'margin_budget.json')
        assert len(budget['banks'])==8
        assert all(r['wrong']==r['unresolved']==0 for r in budget['banks'])
        programming=next(r for r in idle['digital'] if r['window']=='programming')
        assert programming['readout_j']>0 and programming['duration_s']>0
    evaluated=work/'evaluated_candidate'
    if (evaluated/'native/verification.json').exists():
        evaluation=read(evaluated/'native/verification.json')
        assert evaluation['native_unresolved']==0 and evaluation['native_conversions']==28
        assert not evaluation['adopted']
        evaluated_core=read(evaluated/'physical_range_core/routing_views/verification.json')
        assert evaluated_core['magic_drc']==0 and evaluated_core['transistor_lvs']=='PASS'
        evaluated_parent=read(evaluated/'physical_parent/verification.json')
        assert evaluated_parent['status']=='PASS'
        evaluated_timing=evaluated_parent['outputs']['nominal_timing']
        assert min(evaluated_timing['setup_slack_ns'],evaluated_timing['hold_slack_ns'])>=0
        evaluated_render=read(evaluated/'render/verification.json')
        assert evaluated_render['status']=='PASS' and evaluated_render['overview_repeat_pixel_equal']
        evaluated_pulse=read(evaluated/'pwm/verification.json')
        assert len(evaluated_pulse['measurements'])==64
        assert all(Path(row['folder']).is_relative_to(run) for row in evaluated_pulse['measurements'])
    # The executed candidate becomes the source only after all code and electrical audits pass.
    backup=folder/('prepublication_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(exist_ok=False)
    for name in ('AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb','standalone_execution.json'):
        if (root/name).is_file():shutil.copy2(root/name,backup/name)
    for name in ('AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb'):
        if candidate.resolve()!=(root/name).resolve():shutil.copy2(candidate,root/name)
    (root/'standalone_execution.json').write_text(json.dumps({**execution,'notebook':str(root/'AutoMX_CIM_Code_a_Chip.executed.ipynb')},indent=2)+'\n')
    checks=[]
    for name in ('verify_standalone_run.py','verify_measured_costs.py','verify_mha_ip_run.py'):
        log=folder/(Path(name).stem+'.log')
        with log.open('w') as stream:q=subprocess.run([sys.executable,str(root/'scripts'/name),str(root)] if name=='verify_standalone_run.py' else [sys.executable,str(root/'scripts'/name)],cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
        checks.append({'script':name,'returncode':q.returncode,'log':str(log)})
    if not all(c['returncode']==0 for c in checks):
        for p in backup.iterdir():shutil.copy2(p,root/p.name)
        raise AssertionError(checks)
    views=parent['outputs'] if routed else read(run/'full_native/full_native/runall_manifest.json')['views']
    shutil.copy2(views['gds']['path'],root/'exports/AutoMX_CIM_five_block_top.gds')
    for label,path in render['images'].items():shutil.copy2(path,root/'exports'/('AutoMX_CIM_five_block_top_'+label+'.png'))
    if evaluation:
        shutil.copy2(evaluated_parent['outputs']['gds']['path'],root/'exports/AutoMX_CIM_evaluated_candidate.gds')
        for label,path in evaluated_render['images'].items():shutil.copy2(path,root/'exports'/('AutoMX_CIM_evaluated_candidate_'+label+'.png'))
    result={'status':'VERIFIED_ROUTED_PARTITION_RELEASE' if routed else 'VERIFIED_MEASURED_PROTOTYPE_RELEASE','checked_utc':datetime.now(timezone.utc).isoformat(),
        'root':str(root),'fresh_run':str(run),'total_cells':len(book.cells),'code_cells':execution['code_cells'],
        'preceding_cells_retained':len(previous.cells),'full_run_elapsed_s':execution['elapsed_s'],'checks':checks,
        'native_frames':6,'logical_native_conversions':384,'partial_decode_mismatches':0,'rtl_output_mismatches':0,
        'physical_pwm_codes_measured':64,'physical_pwm_contract_pass':not failed_pulse_checks,'failed_pulse_checks':failed_pulse_checks,
        'evaluated_candidate':evaluation,'native_stimulus':native['contract']['stimulus'],'gating_child_energy_reduction_percent':power['gating_child_energy_reduction_percent'],
        'main_and_executed_notebook_identical':(root/'AutoMX_CIM_Code_a_Chip.ipynb').read_bytes()==(root/'AutoMX_CIM_Code_a_Chip.executed.ipynb').read_bytes(),
        'icg_enable_setup_ns':enable['setup_slack_ns'],'icg_enable_hold_ns':enable['hold_slack_ns'],
        'top_gds':views['gds']['path'],'scope':('Fresh physically qualified delivered PWM and receiver input loading, actual enlarged-core GDS/DRC/transistor LVS, fresh parent rails/signal LVS/hierarchical timing, and tagged six-frame live-transistor/real-SAR partition replay. Native core uses the declared compact intrinsic transistor/MIM reference; complete internal-wire transistor PEX, full-foundry signoff and whole-chip energy are separate qualifications.' if routed else 'Fresh parent route and bounded physical checks; exhaustive delivered-pulse measurement is separate from the ideal-50-ps timing-aligned transistor/SAR partition and tagged six-frame RTL replay. Adopted calibration ICG has matched child VCD/Liberty savings and an independent mapped enable timing check. Routed-PWM native closure, full-foundry signoff and complete-chip energy are not claimed.')}
    (folder/'release_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (root/'LATEST_RUN.json').write_text(json.dumps({'run':str(run),'execution_root':str(root),'top_gds':str(root/'exports/AutoMX_CIM_five_block_top.gds'),'manifest':str(run/'full_native/full_native/runall_manifest.json'),'release_validation':str(folder/'release_validation.json')},indent=2)+'\n')
    print('MEASURED_PROTOTYPE_RELEASE_VERIFIED',json.dumps(result),flush=True);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();finalize(args.root)
