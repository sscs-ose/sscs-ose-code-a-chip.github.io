import json,subprocess
from pathlib import Path
r=subprocess.run(['python3','tools/smoke.py'],text=True,capture_output=True,timeout=90)
out=Path('build/audit');out.mkdir(parents=True,exist_ok=True);(out/'audit.log').write_text(r.stdout+r.stderr)
report={'subject':'counter-rtl','verdict':'passed' if r.returncode==0 and 'COUNTER_CHECK_PASS' in r.stdout else 'failed','repair_summary':(r.stdout+r.stderr)[-10000:]}
(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10));print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
