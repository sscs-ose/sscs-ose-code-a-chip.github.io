#!/bin/bash
# W7A4 / W4A8: compute power (real + random), reload power, gating slack, CSVs
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
for v in w7a4 w4a8; do
  d=dcim_${v}_ff
  bash flow/gl_npz.sh $d dcim_core $v python/vectors/${v}_real_layer.npz real 2>&1 | grep -E "compared|Total"
  bash flow/gl_npz.sh $d dcim_core $v python/vectors/${v}_random.npz random 2>&1 | grep -E "compared|Total"
  WIN_SIG=load_en NCASES=50 bash flow/gl_npz.sh $d dcim_core $v python/vectors/${v}_real_layer.npz load 2>&1 | grep -E "compared|Total"
  bash flow/cgcheck.sh $d 2>&1 | python3 flow/cgcsv.py $d
done
python3 flow/extract_ppa.py > /dev/null
python3 flow/extract_area.py > /dev/null
.venv/bin/python flow/extract_activity.py > /dev/null
python3 flow/extract_load.py > /dev/null
grep -E "w7a4|w4a8" results/ppa.csv | cut -d, -f1-13,15,16
grep -E "w7a4|w4a8" results/energy_activity.csv | cut -d, -f1-5
grep -E "w7a4|w4a8" results/load_energy.csv | cut -d, -f1-7
python3 - <<'P'
import csv
for dd in ("dcim_w7a4_ff","dcim_w4a8_ff"):
    d=[r for r in csv.DictReader(open('results/cg_slack.csv')) if r['design']==dd]
    print(dd,len(d),'worst gating setup',min(float(r['clock_gating_setup_slack_ns']) for r in d),'hold',min(float(r['clock_gating_hold_slack_ns']) for r in d))
P
