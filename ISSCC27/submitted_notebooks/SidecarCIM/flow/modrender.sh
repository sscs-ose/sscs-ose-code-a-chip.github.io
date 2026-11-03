#!/bin/bash
# usage: modrender.sh <design> <topmodule> <out.png>
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
r=$(python3 -c "import csv;print([x['run_dir'] for x in csv.DictReader(open('results/ppa.csv')) if x['design']=='$1'][0])")
docker run --rm -v $ROOT:$ROOT -e ODB=$ROOT/$r/final/odb/$2.odb -e OUT=$ROOT/$r/insts.txt ghcr.io/librelane/librelane:3.0.16 openroad -no_splash -exit $ROOT/flow/dump_inst.tcl >/dev/null 2>&1
python3 flow/modules.py $r $r/insts.txt $r/mod_cells.txt $r/mod_legend.txt $1
bash flow/renderfull.sh $1 $r/mod_raw.png $r/mod_cells.txt $r/mod_legend.txt

.venv/bin/python flow/add_legend.py $r/mod_raw.png $3 $r/mod_legend.txt "synthesis-level area share"
