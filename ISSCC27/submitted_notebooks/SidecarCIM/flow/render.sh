#!/bin/bash
# usage: render.sh <design-name> <flowdir> <top>   (latest run; uses final/klayout_gds, sky130A.lyp from the PDK)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
P=$HOME/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71
r=$(ls -d flow/$2/runs/RUN_*|tail -1)
g=$(ls $r/final/klayout_gds/*.gds 2>/dev/null || ls $r/final/gds/*.gds)
docker run --rm -v $ROOT:$ROOT -v $P:$P -w $ROOT ghcr.io/librelane/librelane:3.0.16 \
  klayout -b -r flow/klayout_render.py -rd gds=$ROOT/$g -rd lyp=$P/sky130A/libs.tech/klayout/tech/sky130A.lyp -rd out=$ROOT/results/gds/$1 2>&1 | grep -v QObject
