#!/usr/bin/env bash
# Parasitic corners of the signed-off revision C database (Appendix C.1 of the notebook).
# The sign-off extraction uses the flow's rcx_patterns.rules. This script
#   1. re-extracts the routed database with those rules as a control (the sign-off slacks must come back) and with the six OpenRCX
#      rule sets of the PDK (libs.tech/openlane/rules.openrcx.sky130A.{min,nom,max}.{spef_extractor,magic});
#   2. scales the sign-off parasitics (rc_scale.py) with R x1.11, x1.15, x1.18, x1.30 and C x1.10, x1.15, x1.20, x1.30, and down
#      with R x0.82, x0.70 and C x0.80, x0.70. The R factors follow the PDK's res_high and res_low models (met1, met2 +-11 %, met3,
#      met4 +-13 %, met5 +-18 %); those models give no wire capacitance corner, so the C factors are an assumption;
#   3. runs the sign-off STA (flow/final_sta.tcl, SoC I/O model, SPICE macro views) on every set;
#   4. collects the results (rc_collect.py).
# It only reads the signed-off directories; everything goes to the output directory.
# usage: rc_corners.sh <results dir with 6_final.odb/.sdc/.spef> <macro views dir with ss, tt, ff> <original macro views> <out dir> <result.json>
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad
ORFS_RULES=/opt/eda/orfs-6101364b/flow/platforms/sky130hd/rcx_patterns.rules
FINAL="${1:?results dir}"; VIEWS="${2:?macro views}"; ORIG="${3:?original macro views}"; OUT="${4:?out dir}"; JSON="${5:?result json}"
STA="$HERE/../flow/final_sta.tcl"
PDK=$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A | head -1)
mkdir -p "$OUT"
LOG="$OUT/rc_corners.log"
say() { echo "$(date +%m-%d_%H:%M:%S) $*" | tee -a "$LOG"; }

prepare() {   # tag
  mkdir -p "$OUT/$1"
  ln -sf "$FINAL/6_final.odb" "$OUT/$1/6_final.odb"
  ln -sf "$FINAL/6_final.sdc" "$OUT/$1/6_final.sdc"
}
extract() {   # tag rules
  local d="$OUT/$1"; prepare "$1"
  [ -s "$d/6_final.spef" ] && return 0
  cat > "$d/extract.tcl" <<EOF
read_db $d/6_final.odb
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $2
write_spef $d/6_final.spef.tmp
EOF
  ( cd "$d" && "$OR" -no_splash -exit extract.tcl > extract.log 2>&1 )
  [ -s "$d/6_final.spef.tmp" ] && mv "$d/6_final.spef.tmp" "$d/6_final.spef"
  say "extracted $1"
}
scale() {     # tag Rfactor Cfactor
  local d="$OUT/$1"; prepare "$1"
  [ -s "$d/6_final.spef" ] || python3 "$HERE/rc_scale.py" "$FINAL/6_final.spef" "$d/6_final.spef" "$2" "$3"
  say "scaled $1 R x$2 C x$3"
}
sta_one() {   # set tag corner views
  local d="$OUT/$1" f="$OUT/$1/sta_$2.log"
  RUN="$d" CORNER=$3 MACRO_LIB_DIR=$4 IO_MODE=soc DERATE=0 "$OR" -no_splash -exit "$STA" > "$f" 2>&1
  say "$1 $2 $(grep RESULT "$f" | grep -E 'setup_wns|hold_wns|setup_violating|hold_violating' | sed 's/RESULT //' | tr '\n' ' ')"
}
all_corners() {   # set
  sta_one "$1" ss_spice ss_100C_1v60 "$VIEWS/ss"
  sta_one "$1" tt_spice tt_025C_1v80 "$VIEWS/tt"
  sta_one "$1" ff_spice ff_n40C_1v95 "$VIEWS/ff"
  sta_one "$1" ff_view  ff_n40C_1v95 "$ORIG"
}

extract orfs "$ORFS_RULES"
for c in nom min max; do
  extract "$c" "$PDK/libs.tech/openlane/rules.openrcx.sky130A.$c.spef_extractor"
  extract "m$c" "$PDK/libs.tech/openlane/rules.openrcx.sky130A.$c.magic"
done
for s in orfs nom min max mnom mmin mmax; do all_corners "$s"; done

scale hi10 1.11 1.10
scale hi15 1.15 1.15
scale hi20 1.18 1.20
scale hi30 1.30 1.30
scale lo20 0.82 0.80
scale lo30 0.70 0.70
for s in hi10 hi15 hi20 hi30; do sta_one "$s" ss_spice ss_100C_1v60 "$VIEWS/ss"; done
sta_one hi20 tt_spice tt_025C_1v80 "$VIEWS/tt"
sta_one hi20 ff_spice ff_n40C_1v95 "$VIEWS/ff"
all_corners lo20
sta_one lo30 ff_view ff_n40C_1v95 "$ORIG"

python3 "$HERE/rc_collect.py" "$OUT" "$JSON" "$PDK" "$ORFS_RULES" | tee -a "$LOG"
say "rc corners done"
