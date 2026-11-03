"""Public development check, intentionally smaller than the independent grader."""
import json,subprocess
from pathlib import Path
root=Path.cwd();out=root/'build/smoke';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))
if not sources:raise ValueError('No RTL delivered')
for p in sources:
 if p.is_symlink() or not p.resolve().is_relative_to((root/'rtl').resolve()):raise ValueError('Unsafe RTL path')
commands=[['iverilog','-g2012','-s','benchmark_check_tb','-o',str(out/'sim'),*map(str,sources),'tb/development_tb.sv'],['vvp',str(out/'sim')]]
codes=[];text=''
for command in commands:
 r=subprocess.run(command,text=True,capture_output=True,timeout=90);codes.append(r.returncode);text+=r.stdout+r.stderr
 if r.returncode:break
(out/'smoke.log').write_text(text)
report=dict(subject='benchmark-rtl',verdict='passed' if codes==[0,0] and 'BENCHMARK_PASS' in text else 'failed',repair_summary=text[-10000:])
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
if report['verdict']!='passed':raise SystemExit(1)
