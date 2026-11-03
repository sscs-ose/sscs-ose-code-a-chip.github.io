#!/bin/bash
# memory-gated 128-row queue: wait for >= 7 GB available before each layout; retry once on a crash, util 30 on the CTS dropped-pin bug
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
clk=$1; shift
waitmem() { while [ $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo) -lt 7 ]; do sleep 60; done; }
for n in "$@"; do
  d=flow/p128/c${clk}_$n
  for attempt in 1 2 3; do
    [ -f $d/runs/layout/final/metrics.json ] && break
    waitmem
    rm -rf $d/runs/layout
    librelane --docker-no-tty --dockerized --run-tag layout $d/config.json > flow/logs/p128_c${clk}_$n.log 2>&1
    [ -f $d/runs/layout/final/metrics.json ] && break
    if grep -q "disconnected pin" flow/logs/p128_c${clk}_$n.log; then
      python3 - $d <<'P'
import json,sys
p=sys.argv[1]+"/config.json"; c=json.load(open(p)); c["FP_CORE_UTIL"]=30
json.dump(c,open(p,"w"),indent=2)
P
      echo "c${clk}_$n util 30 (CTS dropped-pin)" >> flow/logs/p128.status
    else echo "c${clk}_$n attempt $attempt crashed, retrying" >> flow/logs/p128.status; fi
  done
  echo "c${clk}_$n $(grep -E '"timing__setup__ws"|"timing__setup_vio__count"|"timing__hold_vio__count"' $d/runs/layout/final/metrics.json 2>/dev/null | tr -d ' \n')" >> flow/logs/p128.status
done
echo "clk$clk done" >> flow/logs/p128.status
