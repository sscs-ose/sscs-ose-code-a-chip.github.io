#!/bin/bash
# Review 4, M7: gate-level power of the existing dcim_core_ff layout (no re-layout) with the
# W4A4+mig+wclip real-layer vectors (python/vectors/w4a4_real_layer.npz, `python vectors.py w4a4`),
# the encoding of the "4-bit DCIM + migration + clip" row. Same chain, corner (tt 1.80 V 25 C,
# nominal SPEF) and OpenSTA script (flow/power.tcl, report_power -digits 6) as every other design.
# Compute: first 100 cases, busy window -> power_real.rpt. Reload: first 50 cases, load_en window
# -> power_load.rpt. The earlier naive-W4A4 runs (real_layer.npz) are kept as power_real_nomig.rpt /
# power_load_nomig.rpt and flow/vcd_compute/dcim_core_ff_{real,load}_nomig.*.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
V=python/vectors
export RUN=$(python3 -c "import csv;print([x['run_dir'] for x in csv.DictReader(open('results/ppa.csv')) if x['design']=='dcim_core_ff'][0])")
echo "run $RUN"
GL_UD=0 bash flow/gl_npz.sh dcim_core_ff dcim_core dense $V/w4a4_real_layer.npz real 2>&1 | grep -E "x_toggle|compared|mismatch|Total|rror"
bash flow/loadpow.sh dcim_core_ff dcim_core dense $V/w4a4_real_layer.npz load_en X=1
python3 flow/extract_ppa.py > /dev/null
.venv/bin/python flow/extract_activity.py > /dev/null
python3 flow/extract_load.py > /dev/null
grep -E "^design|dcim_core_ff" results/ppa.csv | cut -d, -f1,5-7,12,13
grep -E "^design|dcim_core_ff" results/energy_activity.csv
grep -E "^design|dcim_core_ff" results/load_energy.csv | cut -d, -f1-7
