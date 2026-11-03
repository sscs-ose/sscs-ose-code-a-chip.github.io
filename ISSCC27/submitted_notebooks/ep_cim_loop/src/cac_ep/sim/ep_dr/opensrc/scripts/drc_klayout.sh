#!/bin/bash
# KLayout DRC (open_pdks sky130A_mr.drc = OpenLane 2 의 KLayout DRC 덱) — 블록 하나.
# 쓰임: drc_klayout.sh <gds> <top> <outdir> [threads]
#   → <outdir>/<top>.klayout.lyrdb (위반 DB, KLayout 에서 열림) + <top>.klayout.sum (규칙별 개수) + drc_klayout.log
# 환경: OSS (기본 ~/opt/oss_eda), PDK_ROOT (기본 ~/work/ep_dr/opensrc/pdk)
set -u
GDS=$(readlink -f "$1"); TOP=$2; OUT=$3; THR=${4:-4}; HERE=$(dirname "$(readlink -f "$0")")
OSS=${OSS:-$HOME/opt/oss_eda}; PDK_ROOT=${PDK_ROOT:-$HOME/work/ep_dr/opensrc/pdk}
DECK=$PDK_ROOT/sky130A/libs.tech/klayout/drc/sky130A_mr.drc
mkdir -p "$OUT"; cd "$OUT" || exit 1
t0=$(date +%s.%N)
"$HERE/klayout_rb.sh" -b -r "$DECK" -rd input="$GDS" -rd top_cell="$TOP" -rd report="$PWD/$TOP.klayout.lyrdb" \
  -rd feol=true -rd beol=true -rd offgrid=true -rd seal=false -rd floating_met=false -rd thr="$THR" > drc_klayout.log 2>&1
rc=$?
t1=$(date +%s.%N)
"$OSS/bin/python" -I "$HERE/lyrdb_sum.py" "$TOP.klayout.lyrdb" > "$TOP.klayout.sum"
printf 'klayout_drc top=%s exit=%s wall_s=%.1f\n' "$TOP" "$rc" "$(echo "$t1 - $t0" | bc)" | tee -a "$TOP.klayout.sum"
