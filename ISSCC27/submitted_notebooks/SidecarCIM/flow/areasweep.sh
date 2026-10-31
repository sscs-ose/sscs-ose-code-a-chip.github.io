#!/bin/bash
# AREA-strategy sweep on the seven 32-row designs (MAX_FANOUT 24 kept). dcim_8bit_ff first; stop a strategy at its first failure.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/sync_clock.py >/dev/null
D="dcim_8bit_ff dcim_core_ff dcim_w6a4_ff dcim_w8a4_ff sidecarcim_top_ff sidecarcim_top_ff_par sidecarcim_top_ff_pipe mac_baseline"
for S in area0 area2; do
  strat="AREA ${S#area}"
  ok=1
  for d in $D; do
    python3 - $d $S "$strat" <<'P'
import json,sys
d,s,st=sys.argv[1:4]
c=json.load(open("flow/%s/config.json"%d)); c["SYNTH_STRATEGY"]=st
json.dump(c,open("flow/%s/%s.json"%(d,s),"w"),indent=2)
P
    bash flow/try.sh $d $S
    v=$(grep -E '"timing__setup_vio__count"' flow/logs/${d}_$S.res | tr -dc 0-9)
    ws=$(grep -E '"timing__setup__ws"' flow/logs/${d}_$S.res | tr -d ' ,')
    echo "$S $d vio=$v $ws" >> flow/logs/areasweep.status
    if [ "$v" != "0" ]; then ok=0; echo "$S FAILS at $d" >> flow/logs/areasweep.status; break; fi
  done
  if [ $ok = 1 ]; then echo "ADOPTABLE $S" >> flow/logs/areasweep.status; break; fi
done
echo done > flow/logs/areasweep.done
