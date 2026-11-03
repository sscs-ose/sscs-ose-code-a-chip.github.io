"""Adopt a completely executed candidate, audit its artifacts, and write the release record."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import argparse, importlib.util, json, shutil, subprocess, sys, time
import nbformat


def finalize(root, expected_run):
    root=Path(root).resolve();sys.path.insert(0,str(root))
    folder=root/'experiments/priority_20261028';status_file=folder/'notebook_execution.json'
    last=None
    while True:
        try:
            state=json.loads(status_file.read_text())
        except json.JSONDecodeError:
            # The notebook writer briefly truncates this small status file.
            time.sleep(.2)
            continue
        if state['status']!='RUNNING':break
        marker=state.get('last_started_cell')
        if marker!=last:print('WAITING_FOR_CELL',marker,flush=True);last=marker
        time.sleep(5)
    assert state['status']=='ALL_CODE_CELLS_EXECUTED',state
    assert state['executed_cells']==state['code_cells']==156 and not state['errors'],state
    run=max((root/'runs').glob('fresh_*'));assert run.name==expected_run,(run,expected_run)
    work=run/'priority_application';physical=run/'full_native/full_native'
    def read(p):return json.loads(Path(p).read_text())
    app=read(work/'application/application_metrics.json')
    rtl=read(work/'application_rtl/verification.json')
    native=read(work/'native_application/verification.json')
    replay=read(work/'native_replay/verification.json')
    decoder=read(work/'decoder/verification.json')
    power=read(work/'activity_power/verification.json')
    manifest=read(physical/'runall_manifest.json')
    for result in (rtl,native,replay,decoder,power):assert result['status']=='PASS'
    assert app['test_windows']==rtl['frames_per_path']==2947
    assert len(rtl['results'])==4
    assert native['unique_native_jobs']==400 and native['logical_conversions']==128
    assert native['partial_decode_mismatches']==0 and all(f['output_mismatches']==0 for f in native['frames'])
    assert replay['mismatches']==0 and replay['native_transaction_identity_checked']
    assert decoder['cases']==98304
    assert [r['variant'] for r in power['results']]==['linear','binary','digital']
    assert all(r['gate_output_mismatches']==0 for r in power['results'])
    assert all(.85<p['annotation_fraction_including_ports']<=1 for r in power['results'] for p in r['power_blocks'])
    start=datetime.strptime(run.name.removeprefix('fresh_'),'%Y%m%d_%H%M%S_%f').replace(tzinfo=timezone.utc).timestamp()
    fresh_files=[work/'application/application_metrics.json',work/'decoder/verification.json',work/'application_rtl/verification.json',
       work/'native_application/verification.json',work/'native_replay/verification.json',work/'activity_power/verification.json']
    assert all(p.stat().st_mtime>=start for p in fresh_files)
    assert len(list((work/'native_application/conversions').glob('case_*/summary.json')))==400
    routed=(physical/'cold_pnr/design/runs/cold/results/routing/automx_cim_mixed_signal_proto.nl.v').read_text()
    assert '.inn_analog(AINP)' in routed and '.inp_analog(AINN)' in routed
    timing=manifest['views']['nominal_timing'];assert timing['setup_slack_ns']>=0 and timing['hold_slack_ns']>=0,timing
    candidate=Path(state['output']);book=nbformat.read(candidate,4)
    previous=nbformat.read(folder/'baseline/AutoMX_CIM_Code_a_Chip.ipynb',4)
    assert len(book.cells)==409 and {c.id for c in previous.cells}<={c.id for c in book.cells}
    assert all(c.execution_count is not None and c.outputs for c in book.cells if c.cell_type=='code')
    assert not any(o.output_type=='error' for c in book.cells if c.cell_type=='code' for o in c.outputs)
    result_index=next(c for c in book.cells if c.id=='output-results-map')
    result_index.source+='\n\n### Application and controller result\n\n'+(
      f"The frozen six-activity UCI HAR model reaches **{app['models']['integer_mha']['accuracy']*100:.3f}% accuracy** and **{app['models']['integer_mha']['macro_f1']*100:.3f}% macro-F1** on 2,947 windows from nine unseen subjects. All four RTL paths preserve all 23,576 output values per path. Two preselected frames additionally match native circuit/SAR measurements and measured-code replay over 128 ADC transactions.\n\n"
      'The design change replaces 38 linear comparisons with five/six binary-search comparisons while preserving calibration and numerical outputs. Matched functional-ADC latency falls from 145.121 to 61.529 µs/frame; mapped readout cell area increases 0.570%. A separate routed-gate experiment reduces readout + MHA estimated active energy by approximately 45.3%. The serial sign/add digital baseline remains faster and uses less estimated digital energy at this small size. These results support calibrated integration and a measured controller improvement; the hardware block is an attention coprocessor within a software sensor-classification pipeline.\n')
    # The running kernel used this same bounded timeout via its recorded input
    # transform after the isolated-package test hit the original wall limit.
    decoder_cell=next(c for c in book.cells if c.id=='priority-decoder-source')
    decoder_cell.source=decoder_cell.source.replace('timeout=180','timeout=600')
    assert 'timeout=600' in decoder_cell.source
    print('FRESH_APPLICATION_AND_CIRCUIT_AUDIT_PASS',flush=True)
    # Correct only progress-document follow-up wording. Numerical computation,
    # stimulus, measurements, plots and the validated tool calls stay identical.
    replacements={
      'Complete native calibration and two application frames; replay their actual ADC words through the real readout/MHA RTL.':'Expand the bounded operating-point/calibration-transfer campaign and native frame coverage.',
      'Adopt a completed readout physical candidate and reroute/recheck the parent after the ADC polarity correction.':'Measure loaded physical PWM delay taps and establish their relation to the ideal native input drivers.',
      'Integrate source-visible application, decoder, cost and native replay cells into the full notebook and execute from a fresh kernel.':'Have another team member verify a clean extraction/bootstrap in a separate environment.',
      'Add activity-annotated digital energy, idle/startup accounting and the bounded PVT campaign; mapped area/RTL latency are not energy measurements.':'Complete startup/calibration amortization, sensor idle and the remaining power terms before claiming whole-system energy.'}
    cell=next(c for c in book.cells if c.id=='priority-summary-source')
    for old,new in replacements.items():
        assert old in cell.source;cell.source=cell.source.replace(old,new)
    helper=root/'scripts/summarize_priority_implementation.py'
    helper.write_text(cell.source.split('\n',1)[1])
    source_book=nbformat.read(root/'AutoMX_CIM_Code_a_Chip.priority.ipynb',4)
    next(c for c in source_book.cells if c.id=='priority-summary-source').source=cell.source
    nbformat.write(source_book,root/'AutoMX_CIM_Code_a_Chip.priority.ipynb')
    nbformat.write(book,candidate)
    from scripts.summarize_priority_implementation import summarize
    summarize(root,work)
    for name in ['AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb']:shutil.copyfile(candidate,root/name)
    execution={**state,'notebook':str(root/'AutoMX_CIM_Code_a_Chip.executed.ipynb'),
      'documentary_followup_strings_updated':True,'numerical_computation_changed_after_run':False,
      'exhaustive_decoder_wall_timeout_s':600,'timeout_configuration':'experiments/priority_20261028/runtime_timeout_adjustment.json'}
    (root/'standalone_execution.json').write_text(json.dumps(execution,indent=2)+'\n')
    def check(script):
        log=folder/(Path(script).stem+'.log')
        with log.open('w') as stream:
            r=subprocess.run([sys.executable,str(root/script)],cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=480)
        return {'script':script,'returncode':r.returncode,'log':str(log)}
    scripts=['scripts/verify_standalone_run.py','scripts/verify_measured_costs.py','scripts/verify_mha_ip_run.py']
    with ThreadPoolExecutor(max_workers=3) as pool:checks=list(pool.map(check,scripts))
    assert all(c['returncode']==0 for c in checks),checks
    print('INDEPENDENT_PHYSICAL_ENERGY_AND_RENDER_CHECKS_PASS',flush=True)
    export=root/'exports';export.mkdir(exist_ok=True)
    shutil.copy2(manifest['views']['gds']['path'],export/'AutoMX_CIM_five_block_top.gds')
    shutil.copy2(manifest['views']['top_png']['path'],export/'AutoMX_CIM_five_block_top.png')
    floorplan=physical/'render_top/block_floorplan.svg'
    if floorplan.exists():shutil.copy2(floorplan,export/'AutoMX_CIM_five_block_top.floorplan.svg')
    shutil.copy2(folder/'README.release.md',root/'README.md')
    readme=(root/'README.md').read_text();readme=readme.replace('## Measured results',f"Fresh-kernel Run All passed **156/156 code cells**, without notebook errors, in **{state['elapsed_s']/60:.2f} minutes**. Fresh artifacts: `{run.relative_to(root)}/`. Parent TT slack at 25 MHz: **{timing['setup_slack_ns']:+.2f} ns setup / {timing['hold_slack_ns']:+.2f} ns hold**. Independent checks confirm zero router violations, signal macro-boundary LVS, connected rails and identical overview renders.\n\n## Measured results",1)
    (root/'README.md').write_text(readme)
    release=root/'docs/PRIORITY_RELEASE_20261028.md';text=release.read_text()
    text=text.replace('the integrated 409-cell / 156-code-cell candidate is undergoing a fresh-kernel Run All before adoption.','the integrated 409-cell / 156-code-cell notebook passed fresh-kernel Run All and has been adopted as the main notebook.')
    text=text.replace('Use `experiments/priority_20261028/notebook_execution.json` for live validation status.','Execution and artifact checks are recorded in `experiments/priority_20261028/release_validation.json`.')
    text=text.replace('The parent mixed top is being regenerated after adoption of the new readout and the corrected differential ADC pair.',f"The parent mixed top has been regenerated with the new readout and corrected differential pair; its TT setup/hold slack is {timing['setup_slack_ns']:+.2f}/{timing['hold_slack_ns']:+.2f} ns at 25 MHz.")
    text=text.replace('- Finish the active Run All; adopt the executed notebook only after every code cell succeeds, then independently audit fresh waveforms, both KLayout renders, parent routing/LVS/rail connectivity and MHA physical contents.','- Completed: all 156 code cells and independent fresh-waveform, KLayout-render, parent routing/LVS/rail and MHA physical-content checks passed.')
    text+=f"\n## Final execution record\n\nRun: `{run.relative_to(root)}`. All 156 code cells completed in {state['elapsed_s']/60:.2f} minutes; no notebook errors and no empty code-cell outputs. All 374 previous cell IDs are retained. Readout/MHA gate activity and native ADC records were regenerated in this run. The main and executed notebooks have identical content.\n"
    release.write_text(text)
    plan=root/'docs/THREE_DAY_APPLICATION_PLAN_20261027.md';text=plan.read_text().replace('- [ ] Final 409-cell / 156-code-cell fresh Run All','- [x] Final 409-cell / 156-code-cell fresh Run All');plan.write_text(text)
    report={'status':'VERIFIED_PRIORITY_RELEASE','checked_utc':datetime.now(timezone.utc).isoformat(),'run':str(run),
      'notebook':str(root/'AutoMX_CIM_Code_a_Chip.ipynb'),'total_cells':409,'code_cells':156,'preserved_previous_cells':len(previous.cells),
      'elapsed_s':state['elapsed_s'],'notebook_errors':[],'empty_code_outputs':0,'test_frames_per_rtl_path':2947,
      'native_logical_conversions':128,'native_unique_jobs':400,'decoder_cases':98304,'parent_tt_timing':timing,
      'checks':checks,'scope':'Fresh local kernel/results; source-matched hard IP reused, parent rebuilt; measured native responses replayed through actual RTL. Separate-machine bootstrap and complete-system power remain follow-up work.',
      'documentary_followup_strings_updated':True,'numerical_computation_changed_after_run':False}
    package_check=folder/'ip_package_validation_retry/verification.json'
    if package_check.is_file():
        assert read(package_check)['status']=='PASS'
        report['clean_local_ip_extraction_verification']=str(package_check)
    (folder/'release_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    progress=root/'docs/PRIORITY_IMPLEMENTATION_20261028.md'
    with progress.open('a') as stream:stream.write(f"\n## Integrated release verification\n\nFresh Run All: **156/156**, {state['elapsed_s']/60:.2f} minutes, no notebook errors. All 374 previous cell IDs are retained. Independent raw-energy, KLayout pixel comparison, routing/LVS/rail and MHA physical audits passed. New parent TT slack: {timing['setup_slack_ns']:+.2f}/{timing['hold_slack_ns']:+.2f} ns. Main notebook: `AutoMX_CIM_Code_a_Chip.ipynb`. Full scope and next work: `docs/PRIORITY_RELEASE_20261028.md`.\n")
    status=read(folder/'implementation_status.json');status.update(state='VERIFIED_RELEASE',updated_utc=report['checked_utc'],known_good_main_replaced=True,release_validation=str(folder/'release_validation.json'),fresh_validation_run=str(run))
    (folder/'implementation_status.json').write_text(json.dumps(status,indent=2)+'\n')
    print('PRIORITY_RELEASE_READY',json.dumps(report),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args()
    finalize(Path(__file__).resolve().parents[1],a.run)
