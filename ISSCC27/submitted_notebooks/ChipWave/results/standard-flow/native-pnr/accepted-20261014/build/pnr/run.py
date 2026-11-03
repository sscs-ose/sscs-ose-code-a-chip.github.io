import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
from checkpoint import save as checkpoint

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
BUILD = ROOT / 'build/pnr'
REPORT = ROOT / 'reports/pnr'
RESULT = BUILD / 'results'
for p in (BUILD, REPORT, RESULT, BUILD / 'objects', BUILD / 'checkpoints', REPORT / 'logs', REPORT / 'stages'):
    p.mkdir(parents=True, exist_ok=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, data):
    p = Path(p)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(p)


def now():
    return datetime.now(timezone.utc).isoformat()


c = json.loads((ROOT / 'physical/chip-nebula/implementation.constraints.json').read_text())
flow = Path(c['platform_lock']['flow_home'])
openroad_requested = Path(c['physical_execution']['openroad_executable'])
openroad_exe = openroad_requested.resolve()
tool_version = subprocess.check_output([str(openroad_exe), '-version'], text=True).strip()
assert sha(openroad_exe) == c['physical_execution']['executable_sha256'], 'Authorized OpenROAD hash differs'
assert tool_version in c['physical_execution']['version'], 'Authorized OpenROAD version differs'
tool_identity = dict(path=str(openroad_requested), resolved_path=str(openroad_exe), sha256=sha(openroad_exe), version=tool_version, threads=2)
version_log = REPORT / 'klayout_version.log'
klayout_version = version_log.read_text().strip() if version_log.exists() else subprocess.check_output(['klayout', '-v'], text=True).strip()
version_log.write_text(klayout_version + '\n')
assert klayout_version == 'KLayout 0.30.12', 'KLayout version qualification failed'
inputs = []
for aid in ('artifact-8bfa326445194758816c2d0d07307a6f', 'artifact-0040978541934ec0803b607ff5200dae', 'artifact-0b514721fd8641408ffcec0d7f4350ec'):
    p = ROOT / '.nebula_inputs' / aid / 'artifact.json'
    a = json.loads(p.read_text())
    files = []
    for name in a['content']['paths']:
        actual = (ROOT / name).read_bytes()
        frozen = subprocess.check_output(['git', 'show', a['content']['commit'] + ':' + name])
        assert actual == frozen, name
        files.append(dict(path=name, sha256=sha(ROOT / name)))
    inputs.append(dict(artifact_id=aid, commit=a['content']['commit'], record_sha256=sha(p), files=files))
assert c['status'] == 'frozen'
assert sha(ROOT / c['sdc_path']) == c['sdc_sha256']
views = []
for name, v in c['view_binding']['views'].items():
    p = Path(v['installed_path'])
    required = name in ['config.mk', 'fastroute.tcl', 'make_tracks.tcl', 'pdn.tcl', 'tapcell.tcl', 'setRC.tcl', 'rcx_patterns.rules', 'fill.json'] or name.startswith(('lef/', 'lib/'))
    valid = p.exists() and sha(p) == v['sha256']
    views.append(dict(name=name, path=str(p), required_for_pnr=required, valid=valid, sha256=sha(p) if p.exists() else None))
    if required and not valid:
        write(REPORT / 'input_audit.json', dict(verdict='failed', error_class='invalid_physical_view', views=views, inputs=inputs))
        raise RuntimeError('Error-Class: invalid_physical_view: ' + name)
mapped = json.loads((ROOT / 'build/synth/mapped.json').read_text())['modules'][c['physical_top']]
libcells = json.loads((ROOT / 'reports/synthesis/liberty_cells.json').read_text())
lef = Path(c['view_binding']['views']['lef/sky130_fd_sc_hd_merged.lef']['installed_path']).read_text()
masters = {x['type'] for x in mapped['cells'].values()}
for m in masters | {c['pdn']['tap_cell']} | set(c['pdn']['fill_cells']) | set(c['cts']['allowed_clock_buffer_cells']) | {c['pdn']['antenna_diode']}:
    assert 'MACRO ' + m + '\n' in lef, 'Error-Class: invalid_physical_view: missing LEF ' + m
for m in masters | set(c['cts']['allowed_clock_buffer_cells']) | {c['pdn']['antenna_diode']}:
    assert m in libcells, 'Error-Class: invalid_physical_view: missing Liberty ' + m
assert not (masters & set(c['electrical']['dont_use_cells']))
area = sum(libcells[x['type']]['area'] for x in mapped['cells'].values())
side = math.sqrt(area / 0.4)
width, height = math.ceil(side / 0.46) * 0.46, math.ceil(side / 2.72) * 2.72
write(REPORT / 'input_audit.json', dict(verdict='passed', spec_digest=c['spec_digest'], physical_revision='calibrated-geometry-v2', inputs=inputs, views=views, tool_version=tool_version, tool_identity=tool_identity, functional_master_count=len(masters), mapped_cell_count=len(mapped['cells']), mapped_area_um2=area, core_area=[10,10,10+width,10+height], die_area=[0,0,width+20,height+20], orfs_revision_declared=c['platform_lock']['orfs_revision'], orfs_revision_observed=None, note='Installed ORFS is an exported tree; frozen resource hashes verified. Pure physical cells do not require Liberty.'))
guardband_config = ''
if (REPORT / 'guardband.json').exists():
    margins=json.loads((REPORT / 'guardband.json').read_text())
    assert all(0 <= margins[k] <= 35 for k in ['slew_margin_percent','cap_margin_percent'])
    guardband_config=f"export SLEW_MARGIN = {margins['slew_margin_percent']}\nexport CAP_MARGIN = {margins['cap_margin_percent']}\n"
config = f'''{guardband_config}export DESIGN_NAME = {c['physical_top']}
export PLATFORM = sky130hd
export DESIGN_NICKNAME = nebula_cpu_npu_top
export VERILOG_FILES = {ROOT / 'build/synth/nebula_cpu_npu_top.v'}
export SDC_FILE = {ROOT / c['sdc_path']}
export DIE_AREA = 0 0 {width+20:.6f} {height+20:.6f}
export CORE_AREA = 10 10 {width+10:.6f} {height+10:.6f}
export PLACE_DENSITY = 0.55
export CTS_BUF_LIST = {' '.join(c['cts']['allowed_clock_buffer_cells'])}
export PRE_GLOBAL_ROUTE_TCL = {BUILD / 'route_checkpoints.tcl'}
export PRE_DETAIL_ROUTE_TCL = {BUILD / 'route_checkpoints.tcl'}
export PRE_FINAL_REPORT_TCL = {BUILD / 'rcx_compat.tcl'}
export POST_FINAL_REPORT_TCL = {BUILD / 'no_auto_images.tcl'}
'''
(BUILD / 'config.mk').write_text(config)
base = ['make', '-C', str(BUILD), '-f', str(flow / 'Makefile'), f'DESIGN_CONFIG={BUILD / "config.mk"}',
        f'WORK_HOME={BUILD}', f'RESULTS_DIR={RESULT}', f'OBJECTS_DIR={BUILD / "objects"}',
        f'LOG_DIR={REPORT / "logs"}', f'REPORTS_DIR={REPORT / "stages"}',
        f'FLOW_HOME={flow}', f'OPENROAD_EXE={openroad_requested}',
        f'KLAYOUT_CMD={BUILD / "klayout_qualified.sh"}', 'NUM_CORES=2', 'KLAYOUT_VERSION=0.30.12', 'PYTHON_EXE=python3',
        '-o', str(RESULT / '1_2_yosys.v'), '-o', str(RESULT / '1_2_yosys.sdc')]
stages = [('floorplan','2_floorplan.odb'), ('place','3_place.odb'), ('cts','4_cts.odb'), ('grt','5_1_grt.odb'), ('5_2_route','5_2_route.odb'), ('route','5_route.odb'), ('finish','6_final.odb')]
parser = argparse.ArgumentParser()
parser.add_argument('--from-stage', choices=[s for s,_ in stages], default='floorplan')
parser.add_argument('--to-stage', choices=[s for s,_ in stages], default='finish')
parser.add_argument('--restore', action='store_true')
parser.add_argument('--rebuild', action='store_true')
args = parser.parse_args()
if args.restore:
    latest = json.loads((BUILD / 'checkpoints/latest.json').read_text())
    assert latest['tool_identity'] == tool_identity, 'Checkpoint tool identity differs'
    assert [(v['artifact_id'], v['commit']) for v in latest['inputs']] == [(v['artifact_id'], v['commit']) for v in inputs], 'Checkpoint frozen inputs differ'
    slot = ROOT / latest['active_slot']
    assert sha(slot) == latest['odb_sha256']
    restored_database = ROOT / latest.get('restore_database', latest['source_database'])
    shutil.copyfile(slot, restored_database)
    if args.from_stage == 'grt' and latest['stage'] in ('detailed_route', 'antenna_legalized'):
        # GRT skips detailed wires; rebuild guides from the same cells, CTS, PDN and diodes.
        with (REPORT / 'restore_route_preparation.log').open('w') as log:
            subprocess.run([str(openroad_exe), '-no_init', '-exit', '-threads', '2', str(BUILD / 'prepare_rc_eco.tcl')],
                           cwd=ROOT, env=dict(os.environ, NEBULA_ECO_SOURCE=str(restored_database.relative_to(ROOT))),
                           stdout=log, stderr=subprocess.STDOUT, check=True)
for src, dst in [('build/synth/nebula_cpu_npu_top.v','1_2_yosys.v'), (c['sdc_path'],'1_2_yosys.sdc')]:
    p = RESULT / dst
    if not p.exists(): shutil.copyfile(ROOT / src, p)
assert sha(RESULT / '1_2_yosys.v') == sha(ROOT / 'build/synth/nebula_cpu_npu_top.v')
commands = json.loads((REPORT / 'commands.json').read_text()) if (REPORT / 'commands.json').exists() else []
status = dict(schema_version=1, status='failed', completed=False, started_at=now(), inputs=inputs, tool_version=tool_version, evidence=['reports/pnr/input_audit.json'], reason='Physical flow is incomplete; no release claim.')
write(REPORT / 'execution_status.json', status)
for i, (stage, filename) in enumerate(stages):
    if i < [s for s,_ in stages].index(args.from_stage): continue
    targets = {
        'floorplan':[str(RESULT / '1_synth.odb'), 'do-floorplan'], 'place':['do-place'], 'cts':['do-cts'],
        'grt':['do-5_1_grt'], '5_2_route':['do-5_2_route'],
        'route':['do-5_3_fillcell','do-5_route','do-5_route.sdc']}
    command = base + ([str(RESULT / '6_1_fill.odb'), str(RESULT / '6_1_fill.sdc'), 'do-6_report', 'finish'] if stage=='finish' else targets[stage] if args.rebuild else [stage])
    log = REPORT / f'{stage}.log'
    for old in commands:
        if old['stage'] == stage and old.get('exit_code') != 0 and old['log'] == str(log.relative_to(ROOT)):
            failure_log = REPORT / f'{stage}.failure-{commands.index(old)}.log'
            assert not failure_log.exists(), 'Preserve existing failure evidence before another repair'
            log.replace(failure_log)
            old['log'] = str(failure_log.relative_to(ROOT))
    commands.append(dict(stage=stage, argv=command, started_at=now(), log=str(log.relative_to(ROOT)), tool_identity=tool_identity, threads=2, environment_source_paths=c['physical_execution']['environment_source_paths'], config_sha256=sha(BUILD / 'config.mk')))
    write(REPORT / 'commands.json', commands)
    print('RUN', stage, flush=True)
    with log.open('w') as f:
        rc = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT).returncode
    commands[-1].update(exit_code=rc, completed_at=now())
    if rc == 0:
        commands[-1]['database_sha256'] = sha(RESULT / filename)
    write(REPORT / 'commands.json', commands)
    status.update(last_stage=stage, exit_code=rc, evidence=['reports/pnr/input_audit.json','reports/pnr/commands.json',str(log.relative_to(ROOT))])
    if rc:
        status['reason'] = f'ORFS {stage} failed; inspect direct log. No successful final execution.'
        write(REPORT / 'execution_status.json', status)
        raise SystemExit(rc)
    if stage=='finish':
        assert (RESULT / '6_final.spef').stat().st_size>0, 'Final extraction did not produce SPEF'
    for old in commands[:-1]:
        if old['stage']==stage and old.get('exit_code')!=0:
            old['resolved_by_command_index']=len(commands)-1
    write(REPORT / 'commands.json', commands)
    checkpoint(stage, RESULT / filename, stages[min(i+1,len(stages)-1)][0])
    if stage == 'place':
        subprocess.run(['python3','-B',str(BUILD / 'check_geometry.py'),'--database',str((RESULT / filename).relative_to(ROOT)),'--stage','placement'], check=True)
    write(REPORT / 'execution_status.json', status)
    print('CHECKPOINT', stage, flush=True)
    if stage == args.to_stage: break
