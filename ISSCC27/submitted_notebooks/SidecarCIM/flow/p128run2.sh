#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
clk=$1; shift
for n in "$@"; do
  d=flow/p128/c${clk}_$n
  librelane --docker-no-tty --dockerized --run-tag layout $d/config.json > flow/logs/p128_c${clk}_$n.log 2>&1
  if [ ! -f $d/runs/layout/final/metrics.json ]; then
    mv $d/runs/layout $d/runs/failed_util40
    python3 - $d <<'P'
import json,sys
p=sys.argv[1]+"/config.json"; c=json.load(open(p)); c["FP_CORE_UTIL"]=30
json.dump(c,open(p,"w"),indent=2)
P
    echo "c${clk}_$n retried util 30" >> flow/logs/p128.status
    librelane --docker-no-tty --dockerized --run-tag layout $d/config.json > flow/logs/p128_c${clk}_$n.log 2>&1
  fi
  echo "c${clk}_$n $(grep -E '"timing__setup__ws"|"timing__setup_vio__count"|"timing__hold_vio__count"' $d/runs/layout/final/metrics.json | tr -d ' \n')" >> flow/logs/p128.status
done
