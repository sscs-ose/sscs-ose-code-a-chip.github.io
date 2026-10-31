#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
while pgrep -f "ghcr.io/librelane" >/dev/null; do sleep 30; done
d=flow/p128/c35_s3k4
if [ -f $d/runs/layout/final/metrics.json ]; then
  echo "c35_s3k4 $(grep -E '"timing__setup__ws"|"timing__setup_vio__count"|"timing__hold_vio__count"' $d/runs/layout/final/metrics.json | tr -d ' \n')" >> flow/logs/p128.status
else
  echo "c35_s3k4 FAILED (no metrics)" >> flow/logs/p128.status
fi
bash flow/p128run2.sh 35 w6a4 w4a4
echo "clk35 done" >> flow/logs/p128.status
