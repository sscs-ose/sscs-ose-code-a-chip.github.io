#!/usr/bin/env bash
# STA of a global-route result with the macros' SPICE clock-to-output delays (the tier-3 gate's macro views).
#   usage: t3_spice_sta.sh <results dir containing 5_1_grt.odb> <out dir> [sweep dir, default /root/sram_timing]
# ss and tt: setup and hold with the SPICE views (scripts/t3_spice_views.py; unmeasured types provisional, see views.json).
# ff: with the original views (the smaller output delay is the pessimistic side for hold) and, when ff was measured, with
# the SPICE views too. Then the per-macro reports at ss with the SPICE views. Summary: <out dir>/summary.txt
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad
RUN="${1:?results dir}"; OUT="${2:?out dir}"; SWEEP="${3:-/root/sram_timing}"
mkdir -p "$OUT"; export MIN_ROUTING_LAYER=met1 MIN_CLK_ROUTING_LAYER=met3 MAX_ROUTING_LAYER=met5 RUN
python3 "$HERE/scripts/t3_spice_views.py" "$SWEEP" "$OUT/views" ss tt ff | tee "$OUT/views.log"
sta() {   # corner view-dir tag
  CORNER=$1 MACRO_LIB_DIR=$2 "$OR" -no_splash -exit "$HERE/flow_chip/grt_sta.tcl" > "$OUT/sta_$3.log" 2>&1
  echo "$3 $(grep RESULT "$OUT/sta_$3.log" | grep -v macro_views | tr '\n' ' ')"
}
{
  echo "t3_spice_sta $(date -Is) run=$RUN sweep=$SWEEP"
  sta ss_100C_1v60 "$OUT/views/ss" ss_spice
  sta tt_025C_1v80 "$OUT/views/tt" tt_spice
  sta ff_n40C_1v95 /mnt/d/TKVM_ATTT_2026_test/report/a2_macro_link_smoke/run.rjfysF/derived_liberty ff_view
  [ -d "$OUT/views/ff" ] && sta ff_n40C_1v95 "$OUT/views/ff" ff_spice
  CORNER=ss_100C_1v60 MACRO_LIB_DIR="$OUT/views/ss" "$OR" -no_splash -exit "$HERE/flow_chip/grt_macro_io.tcl" > "$OUT/macro_io_ss_spice.log" 2>&1
  CORNER=ss_100C_1v60 MACRO_LIB_DIR="$OUT/views/ss" "$OR" -no_splash -exit "$HERE/flow_chip/grt_macro_endpoints.tcl" > "$OUT/macro_endpoints_ss_spice.log" 2>&1
  echo "note: hold with the SPICE views is optimistic (longer clk->dout); read hold from the original-view STA (sta_*/grt_sta_*.log, ff_view)"
  echo "provisional macro types: $(grep -l provisional "$OUT"/views/*/views.json 2>/dev/null | wc -l) corner(s) with at least one (see views.log)"
  echo "done $(date -Is)"
} 2>&1 | tee "$OUT/summary.txt"
