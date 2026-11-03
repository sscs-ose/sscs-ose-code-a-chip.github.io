from pathlib import Path
import subprocess
root=Path.cwd();out=root/'build';out.mkdir(exist_ok=True)
sources=sorted((root/'rtl').glob('*.sv'))+sorted((root/'rtl').glob('*.v'))
if not sources:raise RuntimeError('missing RTL')
subprocess.run(['iverilog','-g2012','-s','npu_smoke_tb','-o',str(out/'smoke'),*map(str,sources),'tb/npu_smoke_tb.sv'],check=True)
r=subprocess.run(['vvp',str(out/'smoke')],text=True,capture_output=True,timeout=60)
(out/'smoke.log').write_text(r.stdout+r.stderr);print(r.stdout,end='')
if r.returncode or 'NPU_SMOKE_PASS' not in r.stdout:raise RuntimeError('public smoke failed')
