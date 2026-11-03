#!/usr/bin/env bash
# Sign-off STA set of a final database (final_sta.tcl): macro views rebuilt from the SPICE sweep (t3_spice_views.py),
# then ss / tt / ff with the SPICE views, ff also with the original views (the shorter clock-to-output is the
# pessimistic side for hold), each with the SDC as written and with the SoC I/O model, plus ss and ff with a +-5 %
# cell-delay derate. Summary: <out dir>/summary.txt
# usage: final_sta_t3.sh <results dir with 6_final.*> <out dir> [sweep dir, default /root/sram_timing]
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad
RUN="${1:?results dir}"; OUT="${2:?out dir}"; SWEEP="${3:-/root/sram_timing}"
ORIG=/mnt/d/TKVM_ATTT_2026_test/report/a2_macro_link_smoke/run.rjfysF/derived_liberty
mkdir -p "$OUT"; export RUN
python3 "$HERE/scripts/t3_spice_views.py" "$SWEEP" "$OUT/views" ss tt ff | tee "$OUT/views.log"
sta() {   # tag corner views io_mode [derate]
  CORNER=$2 MACRO_LIB_DIR=$3 IO_MODE=$4 DERATE=${5:-0} "$OR" -no_splash -exit "$(dirname "$0")/final_sta.tcl" > "$OUT/sta_$1.log" 2>&1
  echo "$1 $(grep RESULT "$OUT/sta_$1.log" | grep -v -E 'macro_views|corner ' | sed 's/RESULT //' | tr '\n' ' ')"
}
{
  echo "final_sta_t3 $(date -Is) run=$RUN sweep=$SWEEP"
  sha256sum "$RUN/6_final.odb" "$RUN/6_final.spef" "$RUN/6_final.sdc"
  for m in sdc soc; do
    sta ss_spice_$m ss_100C_1v60 "$OUT/views/ss" $m
    sta tt_spice_$m tt_025C_1v80 "$OUT/views/tt" $m
    sta ff_spice_$m ff_n40C_1v95 "$OUT/views/ff" $m
    sta ff_view_$m ff_n40C_1v95 "$ORIG" $m
  done
  sta ss_spice_soc_derate5 ss_100C_1v60 "$OUT/views/ss" soc 0.05
  sta ff_view_soc_derate5 ff_n40C_1v95 "$ORIG" soc 0.05
  echo "provisional macro types: $(grep -c provisional "$OUT/views.log") lines (see views.log)"
  echo "done $(date -Is)"
} 2>&1 | tee "$OUT/summary.txt"
