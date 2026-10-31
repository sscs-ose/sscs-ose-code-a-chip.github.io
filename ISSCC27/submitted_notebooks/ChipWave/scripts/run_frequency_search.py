"""Declared high-frequency experiments on baseline RTL; native tool workflows."""
from pathlib import Path
import argparse,hashlib,json,math,os,re,shutil,subprocess,sys,time
import yaml
CASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE/'scripts'))
from freeze_tool_workflow import freeze
from collect_physical import collect
from chip_nebula.dashboard.workbench import WorkbenchProject
from chip_nebula.taskgraph.static_store import StaticTaskGraphStore
FREQUENCIES=(80,90,95)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def period(frequency):
    if type(frequency) not in (int,float) or not math.isfinite(frequency) or not 20<=frequency<=150:raise ValueError('frequency outside declared exploration range')
    return float(f'{1000/frequency:.6g}')

def prepare(project,frequency,rtl_source=None):
    ns=period(frequency)
    selected=None
    if rtl_source is not None:
        selected=json.loads((rtl_source/'selected-delivery.json').read_text())
        sources=selected['exported_source_sha256']
        assert len(sources)==3 and {Path(p).name for p in sources}=={'rv32i_five_stage_cpu.sv','nebula_npu_dot4.sv','nebula_cpu_npu_top.sv'}
        for p,expected in sources.items():
            path=rtl_source/p
            if not path.resolve().is_relative_to((rtl_source/'rtl').resolve()) or path.is_symlink():raise ValueError('Unsafe RTL source')
            assert digest(path)==expected,p
    shutil.copytree(CASE/'released_design',project)
    if selected is not None:
        shutil.rmtree(project/'rtl')
        for p,expected in sources.items():
            destination=project/p;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(rtl_source/p,destination);assert digest(destination)==expected
        (project/'selected-delivery.json').write_text(json.dumps(selected,indent=2,default=str)+'\n')
    sdk=WorkbenchProject(project);cfg=yaml.safe_load((project/'workbench.yaml').read_text())
    cfg.update(top_module='nebula_cpu_npu_top',design_files=[str(p.relative_to(project)) for p in sorted(project.glob('rtl/**/*.sv'))]);sdk.save_config(cfg)
    receipt=sdk.configure_physical_project(top_module='nebula_cpu_npu_top',clock_port='clk',clock_period_ns=ns,platform='sky130hd',simulation_command='python3 scripts/run_kernels.py --project . --output build/operators')
    assert receipt['environment']['ready']
    physical=project/'physical/chip-nebula';(physical/'configuration-receipt.json').write_text(json.dumps(receipt,indent=2,default=str)+'\n')
    config=physical/'config.mk';text=config.read_text()
    for key,value in {'CORE_UTILIZATION':'40','PLACE_DENSITY':'0.55','ABC_AREA':'0'}.items():
        text,count=re.subn(r'^export '+key+r' = .+$','export '+key+' = '+value,text,flags=re.M);assert count==1,key
    config.write_text(text)
    if selected is not None:
        # The SDK's port parser treats compact reset declarations differently; bind the control's exact SDC.
        control_sdc=CASE/f'results/frequency/mhz{frequency}/frozen-inputs/constraints.sdc'
        (physical/'constraints.sdc').write_bytes(control_sdc.read_bytes())
    sdc=(physical/'constraints.sdc').read_text();m=re.search(r'create_clock .*?-period\s+([\d.]+)',sdc);assert m and abs(float(m[1])-ns)<1e-8
    (physical/'frequency-experiment.json').write_text(json.dumps({'target_mhz':frequency,'target_period_ns':ns,'core_utilization':40,'place_density':0.55,'abc_area':0,'corner':'TT25C1.8V','single_declared_physical_attempt':True,'scope':f'New clock and speed-mapped synthesis before workflow freeze; immutable {"standard-flow" if selected else "baseline"} RTL, checkers and library limits'},indent=2)+'\n')
    (project/'scripts').mkdir(exist_ok=True)
    for name in ('run_physical.py','run_kernels.py','kernel_programs.py'):shutil.copy2(CASE/'scripts'/name,project/'scripts'/name)
    shutil.copytree(CASE/'verification',project/'verification')
    roles=project/'.chip_nebula/roles';roles.mkdir(parents=True,exist_ok=True);recipes=project/'.chip_nebula/recipes';recipes.mkdir(parents=True,exist_ok=True)
    shutil.copy2(CASE/'workflows/case-physical-tool.yaml',roles/'case-physical-tool.yaml')
    definition=yaml.safe_load((CASE/'workflows/cpu-npu-physical.yaml').read_text());task=definition['tasks']['physical']
    task['intent']=f'Run fixed {"standard-flow" if selected else "baseline"} CPU/NPU RTL to GDS at Sky130HD TT25C1.8V, {frequency} MHz ({ns:.12g} ns), speed synthesis and 40% initial utilization. Preserve failures and all acceptance thresholds.'
    task['max_attempts']=1;recipe=recipes/'cpu-npu-physical.yaml';recipe.write_text(yaml.safe_dump(definition,sort_keys=False))
    (project/'.gitignore').write_text('.chip_nebula/\nbuild/\n__pycache__/\n*.pyc\n')
    for command in (['git','init','-q'],['git','config','user.name','Frequency experiment'],['git','config','user.email','automation@chipwave.invalid'],['git','add','.'],['git','add','-f',str(roles/'case-physical-tool.yaml'),str(recipe)],['git','commit','-qm','Freeze explicit high-frequency target and unchanged design']):subprocess.run(command,cwd=project,check=True)
    if selected is None:freeze(project,recipe,'independent-replay')
    else:freeze(project,recipe,'independent-replay',source_design_delivery=selected['id'])

def collect_failed(project,attempt,output):
    commit=attempt.workspace_commit
    if not commit:return None
    names=subprocess.run(['git','ls-tree','-r','--name-only',commit,'build/rtl-to-gds'],cwd=project,capture_output=True,text=True,check=True).stdout.splitlines()
    output.mkdir(parents=True)
    files=[]
    for name in names:
        p=Path(name)
        if p.suffix not in ('.json','.log','.rpt','.gds','.sdc','.spef','.v','.cdl'):continue
        data=subprocess.run(['git','show',f'{commit}:{name}'],cwd=project,capture_output=True,check=True).stdout
        rel=p.relative_to('build/rtl-to-gds');target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);files.append({'path':str(rel),'sha256':hashlib.sha256(data).hexdigest()})
    (output/'failed-attempt.json').write_text(json.dumps({'attempt':attempt.id,'status':attempt.status.value,'workspace_commit':commit,'accepted_delivery':False,'files':files},indent=2)+'\n');return str(output)

def run(output,resume=False):
    if output.exists() and not resume:raise ValueError('Previous experiment preserved; explicit --resume required')
    output.mkdir(exist_ok=resume)
    os.environ.update(ORFS_ROOT=str(CASE/'toolchain/orfs'),NUM_CORES='2')
    flow=json.loads((CASE/'toolchain/orfs/source-manifest.json').read_text())['files']
    for f in flow:assert digest(CASE/'toolchain/orfs'/f['path'])==f['sha256']
    rtl=json.loads((CASE/'released_design/selected-delivery.json').read_text())['exported_source_sha256']
    if not resume:(output/'plan.json').write_text(json.dumps({'frequencies_mhz':FREQUENCIES,'utilization_percent':40,'abc_area':0,'corner':'TT25C1.8V','rtl_sha256':rtl,'constraints_scope':'Clock period changes; I/O 0.5 ns and uncertainty 0.1 ns retained; no relaxed exceptions','baseline_note':'Existing 10 MHz baseline uses area synthesis, so power/area changes are not isolated clock-only effects','decision_rule':'All timing/DRC/LVS/electrical checks must pass; estimate is not acceptance','model_calls':0},indent=2)+'\n')
    rows=json.loads((output/'progress.json').read_text())['rows'] if resume else []
    assert [r['target_mhz'] for r in rows]==list(FREQUENCIES[:len(rows)])
    if resume:
        plan=json.loads((output/'plan.json').read_text());assert plan['rtl_sha256']==rtl and plan['frequencies_mhz']==list(FREQUENCIES)
        for row in rows:assert all(digest(output/f"mhz{row['target_mhz']}"/k)==v for k,v in rtl.items())
    for frequency in FREQUENCIES[len(rows):]:
        project=output/f'mhz{frequency}';print('FREQUENCY_START',frequency,flush=True);start=time.monotonic();prepare(project,frequency)
        assert all(digest(project/k)==v for k,v in rtl.items())
        with (output/f'mhz{frequency}-workflow.log').open('w') as log:
            code=subprocess.run([sys.executable,'-m','chip_nebula.cli.commands','--project-root',str(project),'run',str(project/'.chip_nebula/recipes/cpu-npu-physical.yaml'),'--workflow','independent-replay','--param','rtl=imported-main-rtl','--workers','1','--resume'],stdout=log,stderr=subprocess.STDOUT).returncode
        row={'target_mhz':frequency,'target_ns':period(frequency),'exit_code':code,'wall_seconds':time.monotonic()-start,'qualified':False,'source_unchanged':all(digest(project/k)==v for k,v in rtl.items())}
        evidence=output/'evidence'/f'mhz{frequency}'
        with StaticTaskGraphStore(project/'.chip_nebula/shared/memory/taskgraph-v2.db') as store:
            row['task_state']=store.task_state('independent-replay:physical').value;attempts=store.list_attempts('independent-replay:physical')
            row['attempts']=[{'id':a.id,'status':a.status.value,'failure':a.diagnostics.get('failure_reason','')} for a in attempts]
        if row['task_state']=='satisfied':
            collect(project,'independent-replay',evidence,include_operators=True)
            raw=json.loads(next(evidence.glob('orfs-work/logs/**/6_report.json')).read_text());counts={k:raw['finish__timing__drv__'+k] for k in ('max_slew','max_cap','max_fanout')};summary=json.loads((evidence/'summary.json').read_text())
            row.update(metrics=summary['metrics'],electrical_violations=counts,qualified=code==0 and row['source_unchanged'] and all(v==0 for v in counts.values()))
        elif attempts:row['failed_evidence']=collect_failed(project,attempts[-1],evidence)
        rows.append(row);(output/'progress.json').write_text(json.dumps({'rows':rows,'complete':len(rows)==len(FREQUENCIES)},indent=2)+'\n');print('FREQUENCY_FINISHED',frequency,'qualified',row['qualified'],flush=True)
    (output/'summary.json').write_text(json.dumps({'complete':True,'rows':rows,'all_declared_targets_reported':True,'model_calls':0},indent=2)+'\n')

def self_check():
    assert period(80)==12.5 and period(90)==11.1111 and period(95)==10.5263
    assert all(period(f)<=1000/f for f in FREQUENCIES), 'Rounding must not weaken declared targets'
    for value in (True,0,19,151,float('nan'),float('inf')):
        try:period(value)
        except ValueError:pass
        else:raise AssertionError('Invalid frequency accepted')
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);source=root/'source';(source/'rtl').mkdir(parents=True)
        paths=['rtl/rv32i_five_stage_cpu.sv','rtl/nebula_npu_dot4.sv','rtl/nebula_cpu_npu_top.sv']
        (source/'selected-delivery.json').write_text(json.dumps({'exported_source_sha256':dict.fromkeys(paths,'0'*64)}))
        for path in paths:(source/path).write_text('modified source')
        destination=root/'must-not-exist'
        try:prepare(destination,95,rtl_source=source)
        except AssertionError:pass
        else:raise AssertionError('Modified standard source accepted')
        assert not destination.exists(), 'Invalid source must fail before creating an experiment'
    print('FREQUENCY_SELF_CHECK_PASS: targets and invalid-input guard; real runs additionally bind generated SDC and unchanged RTL')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--self-check',action='store_true');parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if args.self_check:self_check()
    else:
        if args.output is None:parser.error('--output is required for a real experiment')
        run(args.output.resolve(),args.resume)
