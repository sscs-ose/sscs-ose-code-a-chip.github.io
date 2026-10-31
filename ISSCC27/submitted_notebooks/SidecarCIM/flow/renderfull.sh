#!/bin/bash
# usage: renderfull.sh <design> <out.png> [cells.txt legend.txt]
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
r=$(python3 -c "import csv;print([x['run_dir'] for x in csv.DictReader(open('results/ppa.csv')) if x['design']=='$1'][0])")
g=$(ls $r/final/klayout_gds/*.gds)
X=""; [ -n "$3" ] && X="-rd cells=$ROOT/$3 -rd legend=$ROOT/$4"
docker run --rm -v $ROOT:$ROOT -w $ROOT ghcr.io/librelane/librelane:3.0.16 \
  klayout -b -r flow/klayout_full.py -rd gds=$ROOT/$g -rd out=$ROOT/$2 $X 2>&1 | grep -v QObject
