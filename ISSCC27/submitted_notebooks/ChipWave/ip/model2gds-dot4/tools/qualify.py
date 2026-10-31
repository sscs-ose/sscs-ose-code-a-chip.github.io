#!/usr/bin/env python3
from pathlib import Path
import subprocess
root=Path.cwd();out=root/'build';out.mkdir(exist_ok=True)
sources=sorted((root/'rtl').glob('*.sv'))
subprocess.run(['iverilog','-g2012','-s','npu_acceptance_tb','-o',str(out/'sim'),*map(str,sources),'tb/npu_acceptance_tb.sv'],check=True)
r=subprocess.run(['vvp',str(out/'sim')],text=True,capture_output=True,timeout=180)
print(r.stdout,end='');print(r.stderr,end='')
(out/'simulation.log').write_text(r.stdout+r.stderr)
if r.returncode or 'NPU_ACCEPTANCE_PASS cases=264202 cancellations=8' not in r.stdout:raise RuntimeError('IP acceptance failed')
print('IP_QUALIFICATION_PASSED')
