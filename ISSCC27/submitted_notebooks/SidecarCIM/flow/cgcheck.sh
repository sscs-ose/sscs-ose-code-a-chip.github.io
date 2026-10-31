#!/bin/bash
# usage: cgcheck.sh <design> [run_dir]   -> results/cg_slack.csv rows (design,corner,setup_slack_ns,hold_slack_ns)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
d=$1
r=${2:-$(python3 -c "import csv;print([x['run_dir'] for x in csv.DictReader(open('results/ppa.csv')) if x['design']=='$d'][0])")}
top=$(python3 -c "import json;print(json.load(open('flow/$d/config.json'))['DESIGN_NAME'])")
P=$HOME/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71
for c in min_tt_025C_1v80 min_ss_100C_1v60 min_ff_n40C_1v95 nom_tt_025C_1v80 nom_ss_100C_1v60 nom_ff_n40C_1v95 max_tt_025C_1v80 max_ss_100C_1v60 max_ff_n40C_1v95; do
  k=${c%%_*}; lib=$P/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__${c#*_}.lib
  docker run --rm -v $ROOT:$ROOT -v $P:$P -e LIB=$lib -e SPEF=$ROOT/$r/final/spef/$k/$top.$k.spef -e ODB=$ROOT/$r/final/odb/$top.odb -e SDC=$ROOT/$r/final/sdc/$top.sdc -e TAG=$c ghcr.io/librelane/librelane:3.0.16 openroad -no_splash -exit $ROOT/flow/cgcheck.tcl 2>&1 | grep -E "^CG|rror"
done
