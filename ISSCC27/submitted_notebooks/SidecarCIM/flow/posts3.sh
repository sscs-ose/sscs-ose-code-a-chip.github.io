#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
d=sidecarcim_top_ff_pipe_s3
librelane --docker-no-tty --dockerized --to Yosys.Synthesis --run-tag hier flow/$d/hier.json > flow/logs/hier_$d.log 2>&1
bash flow/pows3.sh 2>&1 | tail -12
python3 flow/extract_area.py > /dev/null
python3 flow/cell_mix.py $d > /dev/null
bash flow/renderfull.sh $d results/gds/${d}_full.png
bash flow/render.sh ${d}_z $d sidecarcim_top; mv results/gds/${d}_z_zoom.png results/gds/${d}_zoom.png; rm -f results/gds/${d}_z_full.png results/gds/${d}_z_nofill.png
bash flow/modrender.sh $d sidecarcim_top results/gds/${d}_modules.png
grep -E "pipe_s3" results/area_breakdown.csv
r=$(ls -d flow/$d/runs/RUN_*|tail -1)
python3 - $r <<'P'
import re,sys
t=open(sys.argv[1]+'/55-openroad-stapostpnr/max_ss_100C_1v60/max.rpt',encoding='utf-8',errors='ignore').read()
nl=open(next(__import__('pathlib').Path(sys.argv[1],'final','nl').glob('*.nl.v')),encoding='utf-8').read()
def q(n):
    m=re.search(r'sky130_fd_sc_hd__\w+\s+'+re.escape(n)+r'\s*\((.*?)\);',nl,re.S)
    x=re.findall(r'\.Q\(([^)]*)\)',m.group(1)) if m else []
    return x[0].strip() if x else n
for p in re.split(r'\n(?=Startpoint:)',t)[:8]:
    s=re.search(r'Startpoint: (\S+)',p); e=re.search(r'Endpoint: (\S+)',p); sl=re.search(r'([-\d.]+)\s+slack',p)
    if s and e and sl: print(q(s.group(1)),'->',q(e.group(1)),sl.group(1))
P
