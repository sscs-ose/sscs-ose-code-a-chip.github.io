"""Optional bounded SPICE rerun. No installation or network access.

Example: python reproduce.py tt27_continuous_wrapped --ngspice /path/ngspice
Windows: add --codemodel-dir /path/Spice64/lib/ngspice when needed.
Outputs go to a new directory, never overwrite the evidence snapshot.
"""
import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import psutil
from evidence import assess_run, verify_manifest


def main():
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case', choices=sorted(p.stem for p in (root/'recipes').glob('*.spice')))
    ap.add_argument('--ngspice', default=shutil.which('ngspice') or shutil.which('ngspice_con'))
    ap.add_argument('--codemodel-dir', type=Path)
    args = ap.parse_args()
    if not args.ngspice: ap.error('Specify an existing XSPICE-enabled ngspice executable')
    exe = Path(args.ngspice).resolve()
    if not exe.is_file(): ap.error('ngspice executable does not exist')
    verify_manifest(root)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = root/'reruns'/(args.case+'_'+stamp)
    run.mkdir(parents=True,exist_ok=False)
    text = (root/'recipes'/(args.case+'.spice')).read_text().replace('@PROJECT_ROOT@',root.as_posix())
    (run/'input.spice').write_text(text)
    init = ['set num_threads=1','set ngbehavior=hsa','set filetype=ascii']
    if args.codemodel_dir:
        cmroot = args.codemodel_dir.resolve()
        if ' ' in str(cmroot): ap.error('This ngspice Windows codemodel path must have no spaces')
        for name in ['spice2poly','analog','digital','xtradev','xtraevt','table','tlines']:
            cm = cmroot/(name+'.cm')
            if not cm.is_file(): ap.error('Missing code model: '+str(cm))
            init.append('codemodel '+cm.as_posix())
    (run/'.spiceinit').write_text('\n'.join(init)+'\n')
    provenance=json.loads((root/'data/runs'/args.case/'provenance.json').read_text())
    provenance['original_generated_sha256']=provenance['generated_sha256']
    provenance['generated_sha256']=hashlib.sha256((run/'input.spice').read_bytes()).hexdigest()
    provenance['generated_sha256_normalization']='Exact input.spice file bytes'
    provenance['input_file_sha256']=provenance['generated_sha256']
    provenance['replay_of']=args.case
    provenance['recipe_sha256']=hashlib.sha256((root/'recipes'/(args.case+'.spice')).read_bytes()).hexdigest()
    provenance['adaptations'].append('Relocated includes to the bundled source/model snapshot for this fresh rerun.')
    (run/'provenance.json').write_text(json.dumps(provenance,indent=2))
    env = dict(os.environ, OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    samples=[]; reason=None; started=time.perf_counter()
    with (run/'stdout.log').open('w') as log:
        p = subprocess.Popen([str(exe),'-b','input.spice'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT)
        process = psutil.Process(p.pid)
        try: process.cpu_affinity([process.cpu_affinity()[0]])
        except (psutil.Error, AttributeError): pass
        while p.poll() is None:
            try:
                m=process.memory_info()
                samples.append(dict(elapsed=time.perf_counter()-started,rss=m.rss,
                                    peak_wset=getattr(m,'peak_wset',m.rss)))
                if m.rss > 4*2**30: reason='memory_budget'
            except psutil.NoSuchProcess: pass
            if time.perf_counter()-started > 120: reason='wall_budget'
            if sum(f.stat().st_size for f in run.iterdir() if f.is_file())>200*2**20:
                reason='output_budget'
            if reason: p.kill(); p.wait(); break
            time.sleep(.025)
    resources=dict(exit_code=p.returncode,wall_seconds=time.perf_counter()-started,
                   termination_reason=reason,workers=1,requested_numeric_threads=1,
                   peak_windows_wset=max((s['peak_wset'] for s in samples),default=0),
                   peak_sampled_rss=max((s['rss'] for s in samples),default=0),samples=samples,
                   limits_note='25 ms watchdog; 120 s wall, 4 GiB RSS, 200 MiB output; not an OS hard quota')
    (run/'resources.json').write_text(json.dumps(resources,indent=2))
    report=assess_run(run)
    (run/'assessment.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    print('Saved:',run)
    # A completed invalid measurement is not a successful verification run.
    return 0 if report['measurement']=='VALID' and report['verdict']=='PASS' else 2


if __name__=='__main__': raise SystemExit(main())
