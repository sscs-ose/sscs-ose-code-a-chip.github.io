"""Exactly one 4 ms/12.5 ns compact-clock run; --audit-only never simulates."""
import argparse
from datetime import datetime, timezone
import difflib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

DEST=Path(__file__).resolve().parent
REPO=DEST.parents[3]
ACCEPTED=DEST.parent/'clock_compact_placement'
BASE=REPO/'examples/microrobot/local_runs/clock_layout/compact_x_v1/extracted_25ns'
RUN=BASE.parent/'extracted_12p5ns'
HELPER=DEST.parent/'clock_cap_ablation/run_diagnostic.py'
spec=importlib.util.spec_from_file_location('full_data_audit',HELPER)
audit_helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_helper)
sha,dump=audit_helper.sha,audit_helper.dump
COARSE='tran 2.5e-08 0.004 0 2.5e-08'
FINE='tran 1.25e-08 0.004 0 1.25e-08'


def inputs():
    accepted=json.loads((ACCEPTED/'metrics.json').read_text())
    case=accepted['cases']['compact_x_25ns']
    assert accepted['status']=='Reviewed and accepted as compact-placement improvement evidence; no electrical design acceptance'
    assert case['full_completion']
    for name,value in case['sha256'].items():
        assert sha(BASE/name)==value, name
    original=(BASE/'clock.spice').read_text()
    assert [line for line in original.splitlines() if line.startswith('tran ')]==[COARSE]
    assert original.count(COARSE)==1
    changed=original.replace(COARSE,FINE,1)
    assert changed.replace(FINE,COARSE,1)==original
    assert [line for line in changed.splitlines() if line.startswith('tran ')]==[FINE]
    library=Path(re.search(r'^\.lib "([^"]+)" tt$',original,re.M)[1])
    assert sha(library)==accepted['proof']['pdk_top_level_library_sha256']
    proof={'only_deck_change':'Both tran timestep fields: 2.5e-08 -> 1.25e-08; stop remains 0.004 s',
           'accepted_compact_metrics_sha256':sha(ACCEPTED/'metrics.json'),
           'source_25ns_files_sha256':case['sha256'],
           'top_level_PDK_library':str(library),'top_level_PDK_library_sha256':sha(library),
           'audit_helper_sha256':sha(HELPER),'runner_sha256':sha(Path(__file__)),
           'source_deck_sha256':sha(BASE/'clock.spice'),
           'fine_deck_sha256':__import__('hashlib').sha256(changed.encode()).hexdigest()}
    return original,changed,proof


def execute():
    original,changed,proof=inputs()
    RUN.mkdir(exist_ok=False)
    (RUN/'clock.spice').write_text(changed)
    for name in ['.spiceinit','receiver_cells.spice']:shutil.copy2(BASE/name,RUN/name)
    executable=shutil.which('ngspice')
    if not executable:raise FileNotFoundError('ngspice is required')
    proof['checked_before_simulation_UTC']=datetime.now(timezone.utc).isoformat()
    dump(RUN/'input_checks.json',proof)
    command=[executable,'-b','clock.spice']
    record={'command':command,'cwd':str(RUN.relative_to(REPO)), 'timeout_s':180,
            'fresh_run_directory':True,'simulator_invocations':1,'maximum_timestep_s':12.5e-9,
            'requested_stop_s':.004,'status':'started','started_UTC':datetime.now(timezone.utc).isoformat()}
    dump(RUN/'execution.json',record)
    start=time.monotonic()
    try:
        result=subprocess.run(command,cwd=RUN,capture_output=True,text=True,timeout=180)
        record.update(returncode=result.returncode,status='returned')
        log=result.stdout+result.stderr
    except subprocess.TimeoutExpired as exc:
        record.update(returncode=None,status='timeout')
        to_text=lambda value:value.decode(errors='replace') if isinstance(value,bytes) else (value or '')
        log=str(exc)+'\n'+to_text(exc.stdout)+to_text(exc.stderr)
    record.update(wall_s=time.monotonic()-start,finished_UTC=datetime.now(timezone.utc).isoformat())
    (RUN/'ngspice.log').write_text(log)
    dump(RUN/'execution.json',record)
    print(json.dumps(record),flush=True)


def audit():
    original,changed,proof=inputs()
    assert (RUN/'clock.spice').read_text()==changed
    for name in ['.spiceinit','receiver_cells.spice']:assert sha(BASE/name)==sha(RUN/name)
    checkpoint=json.loads((RUN/'input_checks.json').read_text())
    # Runner edits after execution must be visible rather than replacing provenance.
    assert checkpoint==dict(proof,checked_before_simulation_UTC=checkpoint['checked_before_simulation_UTC'])
    execution=json.loads((RUN/'execution.json').read_text())
    assert execution['simulator_invocations']==1
    cases={name:audit_helper.audit_case(path) for name,path in [('compact_25ns',BASE),('compact_12p5ns',RUN)]}
    completions=all(case.get('full_completion') for case in cases.values())
    execution_pass=execution['returncode']==0 and execution['status']=='returned'
    comparisons={}
    if completions:
        coarse,fine=cases.values()
        values={'clock_frequency_Hz':(coarse['edges']['steady_clock_frequency_Hz'],fine['edges']['steady_clock_frequency_Hz'])}
        values.update({name+'_power_W':(coarse['power_W'][name],fine['power_W'][name]) for name in ['analog_clock','first_ff_and_feedback','whole_clock_and_first_ff']})
        for name,(a,b) in values.items():
            relative=abs(a-b)/abs(b)
            comparisons[name]={'coarse_25ns':a,'fine_12p5ns':b,'absolute_relative_difference_to_fine':relative,'threshold':.01,'passed':relative<.01}
    convergence=bool(comparisons) and all(record['passed'] for record in comparisons.values())
    behavior=bool(completions and all(case['existing_bench_criterion_evaluation']['passed'] and
        set(case['edges']['clock_rises_between_successive_sustained_q_rises'])=={2} for case in cases.values()))
    passed=execution_pass and completions and convergence and behavior
    for name in ['clock.spice','.spiceinit','receiver_cells.spice','ngspice.log','execution.json','input_checks.json']:
        shutil.copy2(RUN/name,DEST/name)
    (DEST/'source_25ns.spice').write_text(original)
    (DEST/'deck.diff').write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),changed.splitlines(keepends=True),fromfile='accepted_compact_25ns/clock.spice',tofile='compact_12p5ns/clock.spice')))
    result={'status':'Awaiting Astra convergence review' if passed else 'Convergence milestone failed; no additional refinement authorized',
            'scope':'One compact-layout timestep refinement, 25 ns to 12.5 ns, 4 ms stop; no physical regeneration',
            'milestone_pass':passed,'full_completion_and_execution_pass':completions and execution_pass,
            'frequency_and_three_integrated_powers_within_1_percent':convergence,
            'unchanged_bench_criterion_and_sustained_divide_by_two_pass':behavior,
            'comparison_method':'abs(coarse-fine)/abs(fine) < 0.01; frequency threshold crossings and exact 2.4–4 ms integrated powers from unchanged full-data audit',
            'comparisons':comparisons,'execution':execution,'input_proof':checkpoint,'cases':cases,
            'assumptions':json.loads((ACCEPTED/'metrics.json').read_text())['assumptions'],
            'limitations':['One timestep refinement at one tt PV cold-start condition; no PVT or mismatch qualification',
                           'Convergence evidence applies to this compact extracted circuit and measured observables, not design or application acceptance',
                           'Raw clock.dat files remain local; no raw transient or local PDF exported']}
    dump(DEST/'metrics.json',result)
    refresh_manifest()
    print(json.dumps({'milestone_pass':passed,'comparisons':comparisons,
                      'cases':{name:{key:case.get(key) for key in ['rows','columns','all_finite','actual_stop_s','rail_V','log_abort_markers']} for name,case in cases.items()}}),flush=True)


def refresh_manifest():
    dump(DEST/'sha256.json',{str(path.relative_to(DEST)):sha(path) for path in sorted(DEST.rglob('*')) if path.is_file() and path.name!='sha256.json' and '__pycache__' not in path.parts})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only',action='store_true')
    args=parser.parse_args()
    if not args.audit_only:execute()
    audit()
