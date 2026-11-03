"""Build and run a real CACE 5.2 project from the pinned public SPICE recipes.

Uses installed, unmodified CACE, xschem and ngspice. No network or installation.
The schematic is a SPICE-body wrapper, not a reconstructed transistor schematic.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import psutil
import yaml


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sch_code(value, name='body'):
    # xschem file quoting: escape literal SPICE expressions and quoted include paths.
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('{', '\\{').replace('}', '\\}')
    return 'C {devices/code_shown.sym} 500 0 0 0 {name='+name+' only_toplevel=false value="'+value+'"}\n'


def prepare(root, project, case, xschem, ngspice, codemodel_dir):
    from evidence import verify_manifest
    verify_manifest(root)
    project.mkdir(parents=True, exist_ok=False)
    for name in ['xschem','cace/templates','cace/scripts','netlist/schematic','profile','bin',
                 'pdk/sky130A/libs.tech/xschem']:
        (project/name).mkdir(parents=True,exist_ok=True)
    recipe = root/'recipes'/(case+'.spice')
    deck = recipe.read_text().replace('@PROJECT_ROOT@',root.as_posix())
    match = re.search(r'^\.subckt (\S+) (.+)$',deck,re.M)
    dut, pins = match.group(1), match.group(2).split()
    start = match.end()
    end = re.search(r'^\.ends\s*$',deck[start:],re.M)
    body = deck[start:start+end.start()]
    dependencies = deck[start+end.end():]
    dependencies = re.sub(r'^\.(GLOBAL.*|end)\s*$','',dependencies,flags=re.M|re.I)
    (project/'xschem/dut_body.spice').write_text(body,encoding='utf-8')
    (project/'xschem/dependencies.spice').write_text(dependencies,encoding='utf-8')
    header='v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n'
    schematic=header
    for i,pin in enumerate(pins):
        schematic+='C {devices/iopin.sym} 0 '+str(i*30)+' 0 0 {name=p'+str(i)+' lab='+pin+'}\n'
    schematic+=sch_code('.include "'+(project/'xschem/dut_body.spice').as_posix()+'"')
    schematic+=sch_code('.include "'+(project/'xschem/dependencies.spice').as_posix()+'"','dependencies').replace('only_toplevel=false','only_toplevel=false place=end').replace('500 0 0 0','500 300 0 0')
    schematic=schematic.replace('devices/',(xschem.parent.parent/'xschem_library/devices').as_posix()+'/')
    (project/'xschem'/(dut+'.sch')).write_text(schematic,encoding='utf-8')
    # Matching symbol fixes the published positional port order for xschem.
    symbol='v {xschem version=3.4.4 file_version=1.2}\nK {type=subcircuit format="@name @pinlist @symname" template="name=x1"}\n'
    for i,pin in enumerate(pins):
        symbol+='B 5 -2 '+str(i*30-2)+' 2 '+str(i*30+2)+' {name='+pin+' dir=inout}\n'
    (project/'xschem'/(dut+'.sym')).write_text(symbol,encoding='utf-8')
    bench=deck[:match.start()]
    bench=re.sub(r'^\*\*?\.?subckt.*$','',bench,flags=re.M)
    bench=bench.replace('quit\n','unset wr_vecnames\nwrdata CACE{filename}_CACE{N}.data v(osc_ck) v(por)\nquit\n')
    bench=bench.replace('sky130.lib.spice" tt','sky130.lib.spice" CACE{corner}')
    bench=bench.replace('.option TEMP=27.0','.option TEMP=CACE{temperature}')
    bench+='\n.include "'+(project/'netlist/schematic'/(dut+'.spice')).as_posix()+'"\n.GLOBAL GND\n'
    bench='* Declared stop time CACE{audit_stop_s}\n'+bench
    template=header+sch_code(bench,'testbench')
    template=template.replace('devices/',(xschem.parent.parent/'xschem_library/devices').as_posix()+'/')
    (project/'cace/templates/startup.sch').write_text(template,encoding='utf-8')
    rc='set XSCHEM_LIBRARY_PATH {'+(xschem.parent.parent/'xschem_library').as_posix()+'}\n'
    rc+='set XSCHEM_SHAREDIR {'+(xschem.parent.parent/'share').as_posix()+'}\n'
    # 3.4.4 uses lvs_netlist for the top-level subcircuit wrapper; newer xschem
    # uses top_is_subckt. Set both explicitly without changing CACE source.
    (project/'xschem/xschemrc').write_text(rc+'set lvs_netlist 1\nset top_is_subckt 1\n')
    (project/'pdk/sky130A/libs.tech/xschem/xschemrc').write_text(rc+'set lvs_netlist 0\nset top_is_subckt 0\n')
    init=['set num_threads=1','set ngbehavior=hsa','set filetype=ascii']
    if codemodel_dir:
        if ' ' in str(codemodel_dir): raise ValueError('Native Windows code-model paths must have no spaces')
        for name in ['spice2poly','analog','digital','xtradev','xtraevt','table','tlines']:
            path=codemodel_dir/(name+'.cm')
            if not path.is_file(): raise FileNotFoundError(path)
            init.append('codemodel '+path.as_posix())
    (project/'cace/spiceinit').write_text('\n'.join(init)+'\n')
    (project/'cace/spinit').write_text('* Initialization supplied in per-run .spiceinit\n')
    shutil.copy2(root/'cace_startup_gate.py',project/'cace/scripts/cace_startup_gate.py')
    if os.name=='nt':
        # CACE invokes ngspice by this name. Byte-identical native executable, no shim.
        shutil.copy2(ngspice,project/'bin/ngspice.exe')
    stop=.006 if case.endswith('_slow') else .004
    spec={'minimum':{'value':.5},'maximum':{'value':2},'unit':'ms'}
    data={'name':dut,'description':'Measurement validity for the public POR; netlist-body schematic wrapper',
          'PDK':'sky130A','cace_format':5.2,
          'authorship':{'designer':'Original POR: Robin Matthew Tsang (ajcci repository); verification notebook: Qin Ruiyao',
                        'license':'Apache 2.0'},
          'paths':{'root':'..','schematic':'xschem','netlist':'netlist'},
          'default_conditions':{'audit_stop_s':{'typical':stop},'corner':{'typical':'tt'},
                                'temperature':{'typical':27.0,'unit':'°C'}},'pins':{},
          'parameters':{'startup_time':{'display':'Validated startup delay',
            'spec':{'startup_validated':spec},
            'tool':{'ngspice':{'template':'startup.sch','format':'ascii','suffix':'.data',
                'variables':['time','osc','por'],'script':'cace_startup_gate.py',
                'script_variables':['startup_validated'],'spiceinit_path':str(project/'cace/spiceinit'),'jobs':1}}}}}
    (project/'cace/por.yaml').write_text(yaml.safe_dump(data,sort_keys=False),encoding='utf-8')
    return {'case':case,'recipe_sha256':digest(recipe),'dut':dut,'ports':pins,
            'wrapper_note':'Published SPICE body in an xschem wrapper; supporting subcircuits emitted outside DUT; no layout flow.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case',choices=['tt27_continuous_fossi','tt27_continuous_fossi_slow','tt27_continuous_nanoamp'])
    ap.add_argument('--xschem',type=Path,required=True)
    ap.add_argument('--ngspice',type=Path,required=True)
    ap.add_argument('--codemodel-dir',type=Path)
    ap.add_argument('--awk-dir',type=Path)
    ap.add_argument('--prepare-only',action='store_true')
    ap.add_argument('--output-dir',type=Path,default=Path.cwd()/'cace_runs',
                    help='Use a short writable path on Windows (native tools have path-length limits)')
    args=ap.parse_args()
    root=Path(__file__).resolve().parent
    project=args.output_dir.resolve()/datetime.now(timezone.utc).strftime('%H%M%S%f')
    xschem=args.xschem.resolve();ngspice=args.ngspice.resolve()
    meta=prepare(root,project,args.case,xschem,ngspice,args.codemodel_dir.resolve() if args.codemodel_dir else None)
    meta.update(python=sys.executable,xschem_sha256=digest(xschem),ngspice_sha256=digest(ngspice))
    if args.prepare_only:
        print(project);return 0
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',
             PDK_ROOT=str(project/'pdk'),PDK='sky130A',PYTHONUTF8='1')
    env.pop('PYTHONPATH',None)
    # Scope xschem's native Windows profile writes to this child process only.
    if os.name=='nt': env['USERPROFILE']=str(project/'profile')
    env['PATH']=os.pathsep.join([str(project/'bin'),str(xschem.parent),str(ngspice.parent),
                                str(args.awk_dir.resolve()) if args.awk_dir else '',env['PATH']])
    env['SPICE_SCRIPTS']=str(project/'cace')
    command=[sys.executable,'-m','cace',str(project/'cace/por.yaml'),'--source','schematic',
             '--jobs','1','--parallel-parameters','1','--sequential','--no-plot','--no-progress-bar']
    samples=[];cutoff=None;start=time.perf_counter()
    with (project/'cli.log').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen(command,cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT)
        parent=psutil.Process(proc.pid)
        try: parent.cpu_affinity([parent.cpu_affinity()[0]])
        except (psutil.Error,AttributeError): pass
        while proc.poll() is None:
            try:
                tree=[parent]+parent.children(recursive=True)
                rss=sum(p.memory_info().rss for p in tree if p.is_running())
                samples.append({'elapsed_s':time.perf_counter()-start,'tree_rss':rss})
                if rss>4*2**30:cutoff='memory_budget'
                if time.perf_counter()-start>180:cutoff='wall_budget'
                if sum(p.stat().st_size for p in project.rglob('*') if p.is_file())>200*2**20:cutoff='output_budget'
                if cutoff:
                    for p in reversed(tree):
                        try:p.kill()
                        except psutil.Error:pass
                    proc.wait();break
            except psutil.Error:pass
            time.sleep(.1)
    meta.update(command=command,exit_code=proc.returncode,termination_reason=cutoff,
                wall_s=time.perf_counter()-start,peak_tree_rss=max((r['tree_rss'] for r in samples),default=0),
                samples=samples,workers=1,limits='180 s, 4 GiB summed RSS, 200 MiB output; sampled watchdog, not OS quota')
    (project/'integration.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in meta.items() if k!='samples'},indent=2))
    print('Saved:',project)
    return proc.returncode


if __name__=='__main__':raise SystemExit(main())
