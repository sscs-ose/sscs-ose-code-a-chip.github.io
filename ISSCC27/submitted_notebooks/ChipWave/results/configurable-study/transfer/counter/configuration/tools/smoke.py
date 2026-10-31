from pathlib import Path
import subprocess
root=Path.cwd();out=root/'build/smoke';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))
subprocess.run(['iverilog','-g2012','-s','counter_check_tb','-o',str(out/'sim'),*map(str,sources),'tb/counter_smoke_tb.sv'],check=True)
subprocess.run(['vvp',str(out/'sim')],check=True,timeout=60)
