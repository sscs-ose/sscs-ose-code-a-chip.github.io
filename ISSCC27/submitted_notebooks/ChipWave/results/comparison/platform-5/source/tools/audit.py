import subprocess,json
from pathlib import Path
r=subprocess.run(['python3','tools/smoke.py'],text=True,capture_output=True)
out=Path('build');out.mkdir(exist_ok=True);(out/'audit.log').write_text(r.stdout+r.stderr)
report={'subject':'generated-rtl','verdict':'passed' if r.returncode==0 else 'failed','log':'build/audit.log'}
(out/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
