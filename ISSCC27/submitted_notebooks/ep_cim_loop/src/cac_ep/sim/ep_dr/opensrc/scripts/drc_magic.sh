#!/bin/bash
# Magic DRC — 블록 하나. 쓰임: drc_magic.sh <gds> <top> <outdir>  → <outdir>/<top>.magic.sum (규칙 문구별 위반 상자 수) + drc_magic.log
set -u
HERE=$(dirname "$(readlink -f "$0")"); GDS=$(readlink -f "$1"); TOP=$2; OUT=$3
MAGIC=${MAGIC:-$HOME/opt/oss_eda/bin/magic}; export PDK_ROOT=${PDK_ROOT:-$HOME/work/ep_dr/opensrc/pdk}
mkdir -p "$OUT"; cd "$OUT" || exit 1
t0=$(date +%s.%N)
GDS=$GDS TOP=$TOP OUT=$PWD/$TOP.magic.sum "$MAGIC" -dnull -noconsole -rcfile "$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc" \
  "$HERE/drc_magic.tcl" < /dev/null > drc_magic.log 2>&1
rc=$?; t1=$(date +%s.%N)
printf 'magic_drc top=%s exit=%s wall_s=%.1f\n' "$TOP" "$rc" "$(echo "$t1 - $t0" | bc)" | tee -a "$TOP.magic.sum"
