#!/bin/bash
# after all five gated runs: gate-level power (real+random), cg slack, CSVs, cell mix, renders
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
GL_UD=0 bash flow/pow_all.sh dcim_core_ff dcim_core dense real_layer random 2>&1 | grep -E "compared|Total"
GL_UD=0 bash flow/pow_all.sh dcim_8bit_ff dcim_8bit dense8 dense8_real_layer dense8_random 2>&1 | grep -E "compared|Total"
GL_UD=0 bash flow/pow_all.sh sidecarcim_top_ff sidecarcim_top top sidecar_real_layer sidecar_random 2>&1 | grep -E "compared|Total"
GL_UD=0 bash flow/gl_npz.sh sidecarcim_top_ff_par sidecarcim_top top python/vectors/sidecar_real_layer.npz real 2>&1 | grep -E "compared|Total"
m=$(ls -d flow/mac_baseline/runs/RUN_*|tail -1)
GL_UD=0 bash flow/gl_all.sh mac_baseline $m results/vcd/mac_baseline.vcd mac_baseline 7400 2>&1 | grep -E "compared"
python3 flow/extract_area.py > /dev/null
python3 flow/extract_ppa.py | grep -i skip
.venv/bin/python flow/extract_activity.py > /dev/null
python3 flow/cell_mix.py > /dev/null
rm -f results/cg_slack.csv
for d in dcim_core_ff dcim_8bit_ff sidecarcim_top_ff sidecarcim_top_ff_par mac_baseline; do bash flow/cgcheck.sh $d 2>&1 | python3 flow/cgcsv.py $d; done
cut -d, -f1-13,15,16 results/ppa.csv; cut -d, -f1-5 results/energy_activity.csv; cat results/area_breakdown.csv
bash flow/finalrender.sh 2>&1 | tail -3
