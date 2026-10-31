#!/bin/bash
# usage: flow/power.sh <flowdir> <run_dir> [vcd] [vcd_scope]
# Post-layout (SPEF) power with OpenROAD in the LibreLane image. No vcd -> vectorless 0.1 activity.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
set -e
cd "$ROOT"
fd=$1; run=$2; vcd=${3:-}; scope=${4:-}
top=$(python3 -c "import json;print(json.load(open('flow/$fd/config.json'))['DESIGN_NAME'])")
pdk=$(grep -o '"PDK_ROOT": "[^"]*"' $run/resolved.json | head -1 | cut -d'"' -f4)
tag=vectorless; [ -n "$vcd" ] && tag=${POW_TAG:-vcd}
out=$run/power_$tag.rpt
docker run --rm -v $ROOT:$ROOT -v $pdk:$pdk -w $ROOT \
  -e TOP=$top -e RUNFINAL=$run/final -e PDKROOT=$pdk -e VCD=$vcd -e SCOPE=$scope \
  ghcr.io/librelane/librelane:3.0.16 openroad -no_splash -exit flow/power.tcl > $out 2>&1
echo "wrote $out"
