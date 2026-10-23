#!/usr/bin/env bash
# (18/10) fmax of the final w1 database by bisection on the clock period (final_sta.tcl FMAX_SEARCH=1), SoC I/O model,
# SPICE macro views, at ss/tt/ff and ss with the +-5 % derate. Output /root/t3/fmax_w1/.
set -uo pipefail
OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad; V=/root/t3/sta_final_x6/views
export RUN=/root/t3/t3e_final_w1/results; O=/root/t3/fmax_w1; mkdir -p "$O"
run() {   # tag corner views derate
  CORNER=$2 MACRO_LIB_DIR=$3 IO_MODE=soc DERATE=$4 FMAX_SEARCH=1 "$OR" -no_splash -exit \
    /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/final_sta.tcl > "$O/$1.log" 2>&1
  echo "$1 $(grep 'RESULT fmax_search' "$O/$1.log")"
}
export -f run; export OR V O RUN
printf '%s\n' "ss ss_100C_1v60 $V/ss 0" "tt tt_025C_1v80 $V/tt 0" "ff ff_n40C_1v95 $V/ff 0" "ss_derate5 ss_100C_1v60 $V/ss 0.05" \
  | xargs -P 2 -L 1 bash -c 'run $0 $1 $2 $3'
