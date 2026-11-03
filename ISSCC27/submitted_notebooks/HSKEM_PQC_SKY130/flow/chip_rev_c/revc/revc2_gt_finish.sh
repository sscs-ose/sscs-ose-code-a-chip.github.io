#!/usr/bin/env bash
# Rev C rebuild: the end of stage gt for a given global-route result: ss and ff checks (gate: ss setup >= +0.2 ns, ff hold
# >= +0.05 ns, SoC model, derate 0.05), then the swap into 5_1_grt.odb (ORFS original kept) and the global-route STA.
# 25/10: used for 5_1_grt_g2f.odb (g2 + delay cells in front of the three hold endpoints repair_timing left, see
# revc2.log), after revc2_gt_hold2.sh showed a second repair pass does not move them.
# usage: revc2_gt_finish.sh <global-route odb, e.g. 5_1_grt_g2f.odb>
set -u
export REVC_W=/root/t3/revc2_a3grt
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
H=$ROOT/hskem_revc/flow; MV=/root/t3/revc_macro_views; LOG=/root/t3/revc2.log; G=${1:?odb}; T=${G#5_1_grt_}; T=${T%.odb}
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
stop() { say "STOP: $*"; exit 1; }
grt_line() { grep -h "CHIPV2_GRT=$1 $2" $Lg/5_1_grt_$1.log | tail -1; }
val() { echo "$1" | grep -o "$2 [-0-9.]*" | awk '{print $2}'; }
[ -f $R/5_1_grt_orfs.odb ] && stop "timing at the global route already done"
[ -f $R/$G ] || stop "no $G"
LIB_FILES=$SS CHIPV2_MACRO_LIB_DIR=$MV/ss CHIPV2_GRT_MODE=report CHIPV2_DERATE=0.05 \
  bash $H/revc_grt_eco.sh $W ${T}s $G > /root/t3/revc2_${T}s.out 2>&1
s=$(val "$(grt_line ${T}s before)" setup_wns); say "$G ss check: $(grt_line ${T}s before)"
LIB_FILES=$FF CHIPV2_GRT_MODE=report CHIPV2_DERATE=0.05 bash $H/revc_grt_eco.sh $W ${T}f $G > /root/t3/revc2_${T}f.out 2>&1
h=$(val "$(grt_line ${T}f before)" hold_wns); say "$G ff check: $(grt_line ${T}f before)"
awk "BEGIN{exit !($s >= 0.2 && $h >= 0.05)}" || stop "global-route timing gate: ss setup $s (need >= 0.2), ff hold $h (need >= 0.05)"
chmod u+w $R/5_1_grt.odb; mv $R/5_1_grt.odb $R/5_1_grt_orfs.odb; cp -p $R/$G $R/5_1_grt.odb; chmod a-w $R/5_1_grt.odb $R/5_1_grt_orfs.odb
say "global route with closed timing: $G -> 5_1_grt.odb (ORFS original kept as 5_1_grt_orfs.odb)"
bash $ROOT/codeachip_t3/scripts/t3_spice_sta.sh $R /root/t3/sta_revc2_grt > /dev/null 2>&1
say "grt STA after g-steps (sdc mode): $(grep -E '^(ss_spice|ff_view) ' /root/t3/sta_revc2_grt/summary.txt | tr '\n' ' ' | cut -c1-400)"
say "stage gt done; next: revc2_chain.sh drt fin"
