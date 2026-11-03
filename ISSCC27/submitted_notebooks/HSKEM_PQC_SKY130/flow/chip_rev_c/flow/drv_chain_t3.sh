#!/usr/bin/env bash
# t3e DRV stage 1 (as the old chip's d1): wait until the DRC dry run has finished its heaviest part (p3_m1) and
# 18 GB are free, then drv_round_t3.sh d1 from the clean b4 checkpoint (SRAM address drivers + repair_design +
# incremental GR + detailed route), then antenna / cleanup rounds e<k> / ec<k> until DRC 0 and antenna 0.
# log: /root/t3/drv_chain.log
set -u
W=/root/t3/t3e_a3grt; D=sky130hd/trustedge_asic_core/chipv2; R=$W/results/$D; Lg=$W/logs/$D; Rp=$W/reports/$D
LOG=/root/t3/drv_chain.log; F=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip
echo "$(date +%H:%M) waiting for DRC part p3_m1 and 18 GB free" | tee -a $LOG
until grep -q "PART_END=p3_m1" /root/t3/t3e_drc.out 2>/dev/null && [ "$(free -g | awk 'NR==2{print $7}')" -ge 18 ]; do sleep 60; done
echo "$(date +%H:%M) d1 from 5_2_route_b4.odb ($(free -g | awk 'NR==2{print $7}') GB free)" | tee -a $LOG
bash $F/drv_round_t3.sh $W d1 5_2_route_b4.odb > /root/t3/t3e_d1.out 2>&1
rc=$(grep -o "DRT_DONE session=d1 rc=[0-9]*" /root/t3/t3e_d1.out | sed 's/.*rc=//')
grep -h "CHIPV2_DRV" $Lg/5_2_route_d1.log | tail -6 | tee -a $LOG
last=$(grep DRT-0199 $Lg/5_2_route_d1.log | tail -1 | sed 's/.*= //; s/.$//')
echo "$(date +%H:%M) d1 rc=$rc last DRC $last, report lines $(grep -c . $Rp/5_route_drc_d1.rpt 2>/dev/null), DRT-1231 skips $(grep -c DRT-1231 $Lg/5_2_route_d1.log)" | tee -a $LOG
[ "$rc" = 0 ] && [ -f $R/5_2_route_d1.odb ] || { echo "STOP: d1 failed" | tee -a $LOG; exit 1; }
chmod a-w $R/5_2_route_d1.odb; echo "   $(sha256sum $R/5_2_route_d1.odb | cut -c1-16) 5_2_route_d1.odb" | tee -a $LOG
PFX=e CPFX=ec bash $F/ant_chain_t3.sh 5_2_route_d1.odb 1 >> $LOG 2>&1
echo "$(date +%H:%M) drv chain end" | tee -a $LOG
