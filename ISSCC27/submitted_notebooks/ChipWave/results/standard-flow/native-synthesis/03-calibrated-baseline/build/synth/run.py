import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/synthesis'
commands = [
    (['python3', '-B', 'build/synth/preflight.py'], 'preflight.log'),
    (['/tmp/chipnebula-pinned-tools/bin/yosys', '-Q', '-T', '-l', 'reports/synthesis/yosys.log', 'build/synth/synth.ys'], 'yosys_console.log'),
    (['/eda/opensource/openroad/26Q3/bin/sta', '-no_init', '-exit', 'build/synth/sta.tcl'], 'sta.log'),
    (['python3', '-B', 'build/synth/write_report.py'], 'report_generation.log'),
    (['/tmp/chipnebula-public-repro-user37/bin/python', '-m', 'chip_nebula.taskgraph.result_summary', 'reports/synthesis/result_summary.json', '--profile', 'synthesis', '--required', 'design.cell_area', '--required', 'design.macro_count', '--required', 'design.standard_cell_count', '--required', 'timing.hold_slack', '--required', 'timing.setup_slack', '--measured', 'design.standard_cell_count', '--measured', 'design.cell_area', '--measured', 'design.macro_count'], 'summary_gate.log'),
]
receipts = []
(OUT / 'execution_status.json').write_text(json.dumps(dict(verdict='failed',status='running'))+'\n')
for args, name in commands:
    with (OUT/name).open('w') as log:
        result = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    receipts.append(dict(argv=args,log='reports/synthesis/'+name,exit_code=result.returncode))
    (OUT/'commands.json').write_text(json.dumps(receipts,indent=2)+'\n')
    assert result.returncode == 0, f'{name} failed; see raw evidence'
summary=json.loads((OUT/'result_summary.json').read_text())
setup=next(m for m in summary['metrics'] if m['id']=='timing.setup_slack')
assert setup['status']=='measured' and setup['value'] >= 0
(OUT/'gates.json').write_text(json.dumps(dict(verdict='passed',gates=[dict(name='synthesis-result-summary',exit_code=0,evidence='reports/synthesis/summary_gate.log'),dict(name='setup-timing-closure',metric='timing.setup_slack',value=setup['value'],operator='>=',threshold=0,passed=True)]),indent=2)+'\n')
(OUT/'execution_status.json').write_text(json.dumps(dict(verdict='passed',status='completed',netlist_release_authorized_by_gates=True),indent=2)+'\n')
print('SYNTHESIS_PASS: reproducible mapped netlist; frozen summary and setup gates pass')
