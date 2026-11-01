"""One 85 C electronics sensitivity at fixed 26.85 C fitted PV; --audit-only never simulates."""
import argparse
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

DEST=Path(__file__).resolve().parent
REPO=DEST.parents[3]
ACCEPTED=DEST.parent/'clock_compact_convergence'
BASE=REPO/'examples/microrobot/local_runs/clock_layout/compact_x_v1/extracted_12p5ns'
RUN=BASE.parent/'hot85_fixed_pv26p85_12p5ns'
EXECUTION_HELPER=ACCEPTED/'run_convergence.py'
spec=importlib.util.spec_from_file_location('accepted_convergence',EXECUTION_HELPER)
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
audit_helper=previous.audit_helper
sha,dump=previous.sha,previous.dump


def inputs():
    accepted=json.loads((ACCEPTED/'metrics.json').read_text())
    assert accepted['status']=='Reviewed and accepted as timestep-consistency evidence for the compact tt PV cold-start bench; no electrical design acceptance'
    nominal=accepted['cases']['compact_12p5ns']
    assert nominal['full_completion'] and accepted['milestone_pass']
    for name,value in nominal['sha256'].items():assert sha(BASE/name)==value,name
    original=(BASE/'clock.spice').read_text()
    assert [line for line in original.splitlines() if line.startswith('.temp ')]==['.temp 26.85']
    assert [line for line in original.splitlines() if line.startswith('tran ')]==['tran 1.25e-08 0.004 0 1.25e-08']
    changes={'.temp 26.85':'.temp 85'}
    for line in original.splitlines():
        if re.match(r'^Dp[123] ',line):
            assert line.split()[-1]=='fitted_pv' and 'temp' not in line.lower()
            changes[line]=line+' TEMP=26.85'
    assert len(changes)==4
    changed=original
    for before,after in changes.items():
        assert changed.count(before+'\n')==1
        changed=changed.replace(before+'\n',after+'\n',1)
    reverse=changed
    for before,after in changes.items():reverse=reverse.replace(after+'\n',before+'\n',1)
    assert reverse==original
    changed_lines=[(a,b) for a,b in zip(original.splitlines(),changed.splitlines()) if a!=b]
    assert len(changed_lines)==4 and dict(changed_lines)==changes
    library=Path(re.search(r'^\.lib "([^"]+)" tt$',original,re.M)[1])
    assert sha(library)==accepted['input_proof']['top_level_PDK_library_sha256']
    proof={'scope':'One hot-electronics 85 C sensitivity with fitted PV fixed at 26.85 C',
           'exact_four_changed_lines':changed_lines,'nominal_full_data_and_input_sha256':nominal['sha256'],
           'accepted_nominal_metrics_sha256':sha(ACCEPTED/'metrics.json'),
           'source_deck_sha256':sha(BASE/'clock.spice'),'hot_deck_sha256':hashlib.sha256(changed.encode()).hexdigest(),
           'top_level_PDK_library':str(library),'top_level_PDK_library_sha256':sha(library),
           'runner_sha256':sha(Path(__file__)),'execution_helper_sha256':sha(EXECUTION_HELPER),
           'full_data_audit_helper_sha256':sha(previous.HELPER)}
    return original,changed,proof


def execute():
    # Reuse the accepted fresh-directory, one-invocation, 180 s runner.
    previous.BASE,previous.RUN,previous.inputs=BASE,RUN,inputs
    previous.execute()


def audit():
    original,changed,proof=inputs()
    assert (RUN/'clock.spice').read_text()==changed
    for name in ['.spiceinit','receiver_cells.spice']:assert sha(RUN/name)==sha(BASE/name)
    checkpoint=json.loads((RUN/'input_checks.json').read_text())
    assert checkpoint==dict(proof,checked_before_simulation_UTC=checkpoint['checked_before_simulation_UTC'])
    execution=json.loads((RUN/'execution.json').read_text())
    assert execution['simulator_invocations']==1
    nominal=audit_helper.audit_case(BASE)
    try:
        hot=audit_helper.audit_case(RUN)
    except (ValueError,IndexError) as exc:
        log=(RUN/'ngspice.log').read_text()
        hot={'source':str(RUN.relative_to(REPO)),'full_completion':False,
             'failure':'Full-data audit could not parse complete data: '+str(exc),
             'sha256':{p.name:sha(p) for p in sorted(RUN.iterdir()) if p.is_file()},
             'log_abort_markers':[s for s in ['simulation(s) aborted','doanalyses:','timestep too small'] if s in log.lower()]}
    complete=bool(nominal.get('full_completion') and hot.get('full_completion') and execution['returncode']==0 and execution['status']=='returned')
    comparisons={};behavior=False
    if complete:
        values={'clock_frequency_Hz':(nominal['edges']['steady_clock_frequency_Hz'],hot['edges']['steady_clock_frequency_Hz'])}
        values.update({name+'_power_W':(nominal['power_W'][name],hot['power_W'][name]) for name in ['analog_clock','first_ff_and_feedback','whole_clock_and_first_ff']})
        values.update({'rail_'+name+'_V':(nominal['rail_V'][name],hot['rail_V'][name]) for name in ['time_average','minimum','maximum']})
        for name,(a,b) in values.items():comparisons[name]={'nominal':a,'hot85_fixed_PV':b,'hot_over_nominal':b/a if a and b is not None else None}
        edges=hot['edges']
        behavior=bool(hot['existing_bench_criterion_evaluation']['passed'] and edges['steady_q_rise_count']>=3 and
                      set(edges['clock_rises_between_successive_sustained_q_rises'])=={2})
    for name in ['clock.spice','.spiceinit','receiver_cells.spice','ngspice.log','execution.json','input_checks.json']:shutil.copy2(RUN/name,DEST/name)
    (DEST/'source_nominal_12p5ns.spice').write_text(original)
    (DEST/'deck.diff').write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),changed.splitlines(keepends=True),fromfile='accepted_nominal_12p5ns/clock.spice',tofile='hot85_fixed_PV26p85_12p5ns/clock.spice')))
    result={'status':'Awaiting Astra hot-electronics sensitivity review' if complete else 'Hot sensitivity incomplete; whole-window hot metrics invalid; stopped without retry',
            'scope':proof['scope'],'complete_finite_full_transient_and_exit_zero':complete,
            'unchanged_bench_criteria_and_at_least_3_steady_Q_rises_and_sustained_divide_by_two_pass':behavior,
            'whole_window_comparisons_valid':complete,'comparisons':comparisons,
            'cases':{'nominal_26p85_12p5ns':nominal,'electronics85_fixedPV26p85_12p5ns':hot},
            'execution':execution,'input_proof':checkpoint,
            'assumptions':json.loads((ACCEPTED/'metrics.json').read_text())['assumptions'],
            'temperature_policy':'Electronics global .temp 85 C; each Dp1/Dp2/Dp3 has instance TEMP=26.85 C. Fitted PV model TNOM=26.85 EG=0 XTI=0 unchanged; instance TEMP additionally fixes diode thermal voltage.',
            'limitations':['One hot-electronics sensitivity with fixed-temperature fitted PV, not whole-device thermal calibration',
                           'No hot timestep refinement or hot convergence qualification; nominal timestep consistency does not establish hot convergence',
                           'Does not resolve prior coupled-controller hot failures; no coupled controller, PVT sweep or mismatch work',
                           'No arbitrary frequency/power acceptance thresholds or 13 kHz requirement applied; existing swing/divider criteria unchanged',
                           'Raw clock.dat remains local; no raw transient or local PDF exported; no physical regeneration']}
    dump(DEST/'metrics.json',result)
    refresh_manifest()
    print(json.dumps({'complete':complete,'unchanged_behavior_pass':behavior,'comparisons':comparisons,
                      'hot':{key:hot.get(key) for key in ['rows','columns','all_finite','first_time_s','actual_stop_s','nondecreasing_time','log_abort_markers']}}),flush=True)


def refresh_manifest():
    dump(DEST/'sha256.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='sha256.json' and '__pycache__' not in p.parts})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    if not args.audit_only:execute()
    audit()
