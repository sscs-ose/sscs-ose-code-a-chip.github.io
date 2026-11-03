#!/usr/bin/env bash
# Rev C rebuild, 25/10 22:30: stage gt stopped at its gate with one hold endpoint at -0.006 ns at ff after g2 (a direct
# flop-to-flop connection, decaps dy_odd[2] -> db_c1[2], 0.19 ns clock skew; 1,831 endpoints were inside the margin and
# one pass left it). A second hold pass on g2 (g2b, same settings), the ss and ff checks of stage gt, then, if both pass,
# the swap into 5_1_grt.odb and the global-route STA, exactly as the rest of stage gt.
set -u
export REVC_W=/root/t3/revc2_a3grt
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
H=$ROOT/hskem_revc/flow; MV=/root/t3/revc_macro_views; LOG=/root/t3/revc2.log
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
stop() { say "STOP: $*"; exit 1; }
grt_line() { grep -h "CHIPV2_GRT=$1 $2" $Lg/5_1_grt_$1.log | tail -1; }
val() { echo "$1" | grep -o "$2 [-0-9.]*" | awk '{print $2}'; }
[ -f $R/5_1_grt_orfs.odb ] && stop "timing at the global route already done"
LIB_FILES=$FF CHIPV2_GRT_MODE=hold CHIPV2_DERATE=0.05 CHIPV2_MARGIN=0.1 \
  bash $H/revc_grt_eco.sh $W g2b 5_1_grt_g2.odb > /root/t3/revc2_g2b.out 2>&1
[ -f $R/5_1_grt_g2b.odb ] || stop "g2b failed"
say "g2b (ff hold, second pass): $(grt_line g2b before) -> $(grt_line g2b after)"
G=5_1_grt_g2b.odb
LIB_FILES=$SS CHIPV2_MACRO_LIB_DIR=$MV/ss CHIPV2_GRT_MODE=report CHIPV2_DERATE=0.05 \
  bash $H/revc_grt_eco.sh $W g3s2 $G > /root/t3/revc2_g3s2.out 2>&1
s=$(val "$(grt_line g3s2 before)" setup_wns); say "g3 ss check: $(grt_line g3s2 before)"
LIB_FILES=$FF CHIPV2_GRT_MODE=report CHIPV2_DERATE=0.05 bash $H/revc_grt_eco.sh $W g3f4 $G > /root/t3/revc2_g3f4.out 2>&1
h=$(val "$(grt_line g3f4 before)" hold_wns); say "g3 ff check: $(grt_line g3f4 before)"
awk "BEGIN{exit !($s >= 0.2 && $h >= 0.05)}" || stop "global-route timing gate: ss setup $s (need >= 0.2), ff hold $h (need >= 0.05)"
chmod u+w $R/5_1_grt.odb; mv $R/5_1_grt.odb $R/5_1_grt_orfs.odb; cp -p $R/$G $R/5_1_grt.odb; chmod a-w $R/5_1_grt.odb $R/5_1_grt_orfs.odb
say "global route with closed timing: $G -> 5_1_grt.odb (ORFS original kept as 5_1_grt_orfs.odb)"
bash $ROOT/codeachip_t3/scripts/t3_spice_sta.sh $R /root/t3/sta_revc2_grt > /dev/null 2>&1
say "grt STA after g-steps (sdc mode): $(grep -E '^(ss_spice|ff_view) ' /root/t3/sta_revc2_grt/summary.txt | tr '\n' ' ' | cut -c1-400)"
say "stage gt done (with g2b); next: revc2_chain.sh drt fin"
