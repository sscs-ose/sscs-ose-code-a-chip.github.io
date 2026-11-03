#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/sync_clock.py >/dev/null
for d in dcim_w7a4_ff dcim_w4a8_ff; do
  bash flow/runflow.sh $d
  r=$(ls -d flow/$d/runs/RUN_*|tail -1)
  echo "$d $r $(grep -E '"timing__setup__ws"|"timing__setup_vio__count"|"timing__hold_vio__count"' $r/final/metrics.json | tr -d ' \n')" >> flow/logs/runw2.status
done
echo done > flow/logs/runw2.done
