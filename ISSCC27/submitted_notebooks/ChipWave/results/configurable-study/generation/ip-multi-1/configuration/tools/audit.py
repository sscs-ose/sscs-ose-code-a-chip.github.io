from pathlib import Path
import subprocess,json
root=Path.cwd();out=root/'build/audit';out.mkdir(parents=True,exist_ok=True)
sources=sorted(root.glob('rtl/**/*.sv'))+sorted(root.glob('rtl/**/*.v'))+sorted(root.glob('ip/**/*.sv'))+sorted(root.glob('ip/**/*.v'))
commands=[['iverilog','-g2012','-s','npu_smoke_tb','-o',str(out/'sim'),*map(str,sources),'tb/npu_smoke_tb.sv'],['vvp',str(out/'sim')]]
text='';code=1
for command in commands:
 r=subprocess.run(command,text=True,capture_output=True,timeout=90);text+=r.stdout+r.stderr;code=r.returncode
 if code:break
(out/'audit.log').write_text(text)
report={'subject':'generated-rtl','verdict':'passed' if code==0 and 'NPU_SMOKE_PASS' in text else 'failed','repair_summary':text[-12000:]}
(out/'report.json').write_text(json.dumps(report,indent=2)+chr(10))
print('NEBULA_OUTPUT: '+json.dumps({'report':report}))
