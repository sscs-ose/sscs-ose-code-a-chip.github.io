#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/sync_clock.py >/dev/null
for d in dcim_w8a4_ff dcim_w6a4_ff; do
  bash flow/runflow.sh $d
  r=$(ls -d flow/$d/runs/RUN_*|tail -1)
  v=$(grep -E '"timing__setup_vio__count": ' $r/final/metrics.json | tr -dc 0-9)
  echo "$d $r setup_vio=$v" >> flow/logs/runw.status
  if [ "$v" != "0" ]; then echo "FAIL $d" >> flow/logs/runw.status; break; fi
done
echo done > flow/logs/runw.done
