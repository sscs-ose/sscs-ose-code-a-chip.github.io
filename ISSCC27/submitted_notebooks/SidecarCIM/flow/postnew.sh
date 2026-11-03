#!/bin/bash
# after the two dense variants ran: power (real+random), CSVs, gating slack
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
GL_UD=0 bash flow/pownew.sh
python3 flow/extract_ppa.py | grep -i skip
python3 flow/extract_area.py > /dev/null
.venv/bin/python flow/extract_activity.py > /dev/null
for d in dcim_w8a4_ff dcim_w6a4_ff; do bash flow/cgcheck.sh $d 2>&1 | python3 flow/cgcsv.py $d; done
grep -E "w8a4|w6a4" results/ppa.csv | cut -d, -f1-13
grep -E "w8a4|w6a4" results/energy_activity.csv | cut -d, -f1-6
grep -E "w8a4|w6a4" results/area_breakdown.csv
python3 - <<'P'
import csv
from collections import defaultdict
d=defaultdict(list)
for r in csv.DictReader(open('results/cg_slack.csv')):
    d[r['design']].append((float(r['clock_gating_setup_slack_ns']),float(r['clock_gating_hold_slack_ns']),r['corner']))
for k,v in d.items(): print(k,len(v),'worst gating setup %.2f hold %.2f'%(min(x[0] for x in v),min(x[1] for x in v)))
P
