#!/bin/bash
# usage: try.sh <flowdir> <cfg-name>   full flow with a knob-variant config, run tag = cfg-name
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/sync_clock.py
librelane --docker-no-tty --dockerized --run-tag $2 flow/$1/$2.json > flow/logs/$1_$2.log 2>&1
r=flow/$1/runs/$2
grep -E "\"timing__setup__ws\"|\"timing__setup_vio__count\"|\"design__instance__area__stdcell\"|drc_error__count|lvs_error\"" $r/final/metrics.json > flow/logs/$1_$2.res
echo done >> flow/logs/$1_$2.res
