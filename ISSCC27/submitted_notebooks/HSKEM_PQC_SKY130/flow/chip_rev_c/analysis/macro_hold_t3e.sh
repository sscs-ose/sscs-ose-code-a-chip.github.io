#!/usr/bin/env bash
# (18/10) Hold paths into the SRAM macro inputs of the final w1 database at ss/tt/ff (SoC I/O model, SPICE views of
# /root/t3/sta_final_x6/views), with final_sta.tcl MACRO_HOLD=1. Output /root/t3/macro_hold_w1/.
set -uo pipefail
OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad; V=/root/t3/sta_final_x6/views
export RUN=/root/t3/t3e_final_w1/results; O=/root/t3/macro_hold_w1; mkdir -p "$O"
for c in ss:ss_100C_1v60 tt:tt_025C_1v80 ff:ff_n40C_1v95; do
  k=${c%%:*}; CORNER=${c#*:} MACRO_LIB_DIR=$V/$k IO_MODE=soc MACRO_HOLD=1 "$OR" -no_splash -exit \
    /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/final_sta.tcl > "$O/sta_$k.log" 2>&1
  echo "$k $(grep -E 'RESULT (hold_wns|setup_wns|macro_input_pins)' "$O/sta_$k.log" | tr '\n' ' ')"
  awk '/SECTION MACRO_HOLD$/{f=1;next} /SECTION MACRO_HOLD_PATH/{f=0} f' "$O/sta_$k.log" | grep -E "u_macro" | head -5
  awk '/SECTION MACRO_HOLD_PATH/{f=1} /SECTION WORST_SETUP_PATH/{f=0} f' "$O/sta_$k.log" | grep -E "library hold|slack|Endpoint|clock network|data arrival" | head -8
done
