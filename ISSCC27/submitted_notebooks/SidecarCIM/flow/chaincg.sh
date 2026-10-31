#!/bin/bash
# one flow at a time; stop at the first design with setup violations
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/sync_clock.py
for d in dcim_core_ff sidecarcim_top_ff sidecarcim_top_ff_par mac_baseline; do
  bash flow/runflow.sh $d
  r=$(ls -d flow/$d/runs/RUN_*|tail -1)
  v=$(grep -E '"timing__setup_vio__count": ' $r/final/metrics.json | tr -dc 0-9)
  echo "$d $r setup_vio=$v" >> flow/logs/chaincg.status
  if [ -f flow/$d/hier.json ]; then
    mv flow/$d/runs/hier flow/$d/hier_old_$(date +%s) 2>/dev/null
    librelane --docker-no-tty --dockerized --to Yosys.Synthesis --run-tag hier flow/$d/hier.json > flow/logs/hier_$d.log 2>&1
  fi
  if [ "$v" != "0" ]; then echo "FAIL $d" >> flow/logs/chaincg.status; break; fi
done
echo done > flow/logs/chaincg.done
