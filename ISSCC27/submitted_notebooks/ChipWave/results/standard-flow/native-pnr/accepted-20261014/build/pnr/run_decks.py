import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
c = json.loads((root / 'physical/chip-nebula/implementation.constraints.json').read_text())
flow = Path(c['platform_lock']['flow_home'])
result = root / 'build/pnr/results'
report = root / 'reports/pnr'
openroad_exe = json.loads((report / 'input_audit.json').read_text())['tool_identity']['path']
base = ['make', '-C', str(root / 'build/pnr'), '-f', str(flow / 'Makefile'),
        f'DESIGN_CONFIG={root / "build/pnr/config.mk"}', f'FLOW_HOME={flow}',
        f'WORK_HOME={root / "build/pnr"}', f'RESULTS_DIR={result}',
        f'OBJECTS_DIR={root / "build/pnr/objects"}', f'LOG_DIR={report / "logs"}',
        f'REPORTS_DIR={report / "stages"}', f'KLAYOUT_CMD={root / "build/pnr/klayout_qualified.sh"}', 'NUM_CORES=2', 'KLAYOUT_VERSION=0.30.12', 'PYTHON_EXE=python3',
        f'OPENROAD_EXE={openroad_exe}',
        '-o', str(result / '1_2_yosys.v'), '-o', str(result / '1_2_yosys.sdc')]
commands = []
jobs = [('gds_master_audit', ['/tmp/chipnebula-pinned-tools/bin/klayout','-b','-r',str(root / 'build/pnr/check_gds_masters.py')]),
        ('stream_out', base + ['do-gds']),
        ('independent_drc', ['/tmp/chipnebula-pinned-tools/bin/klayout','-b','-rd',f'in_gds={result / "6_final.gds"}',
                             '-rd',f'report_file={report / "stages/6_drc.lyrdb"}',
                             '-r',c['view_binding']['views']['drc/sky130hd.lydrc']['installed_path']])]
for name, command in jobs:
    log = report / (name + '.log')
    with log.open('w') as f:
        rc = subprocess.run(command, cwd=root / 'build/pnr', stdout=f, stderr=subprocess.STDOUT).returncode
    commands.append(dict(name=name, argv=command, exit_code=rc, evidence=str(log.relative_to(root))))
    (report / 'deck_commands.json').write_text(json.dumps(commands, indent=2) + '\n')
    print(name, rc, flush=True)
    if rc: raise SystemExit(rc)
    if name == 'gds_master_audit':
        assert json.loads((report / 'gds_master_audit.json').read_text())['status'] == 'passed', 'Error-Class: invalid_physical_view: actual ODB masters missing from frozen GDS'
cdl = result / '6_final.cdl'
libcdl = Path(c['view_binding']['views']['cdl/sky130hd.cdl']['installed_path'])
combined = root / 'build/pnr/objects/6_final_concat.cdl'
combined.write_bytes(cdl.read_bytes() + b'\n' + libcdl.read_bytes())
command = ['/tmp/chipnebula-pinned-tools/bin/klayout','-b','-rd',f'in_gds={result / "6_final.gds"}',
           '-rd',f'cdl_file={combined}', '-rd',f'top_cell={c["physical_top"]}',
           '-rd',f'target_netlist={result / "lvs_extracted.cir"}',
           '-rd',f'report_file={report / "6_lvs.lvsdb"}',
           '-r',c['view_binding']['views']['lvs/sky130hd.lylvs']['installed_path']]
with (report / 'independent_lvs.log').open('w') as f:
    rc = subprocess.run(command, cwd=root / 'build/pnr', stdout=f, stderr=subprocess.STDOUT).returncode
commands.append(dict(name='independent_lvs', argv=command, exit_code=rc, evidence='reports/pnr/independent_lvs.log'))
(report / 'deck_commands.json').write_text(json.dumps(commands, indent=2) + '\n')
print('independent_lvs',rc,flush=True)
raise SystemExit(rc)
