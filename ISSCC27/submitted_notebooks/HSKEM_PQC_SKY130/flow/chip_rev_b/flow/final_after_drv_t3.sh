#!/usr/bin/env bash
# Park the current final outputs (6_final.*, 6_*.cdl, 6_finish.rpt) under final_from_<tag>/, then run final_t3.sh on
# the given clean checkpoint and print the post-RCX timing and DRV counts. usage: final_after_drv_t3.sh <prev tag> <odb>
set -u
W=/root/t3/t3e_a3grt; D=sky130hd/trustedge_asic_core/chipv2; R=$W/results/$D; Rp=$W/reports/$D
PREV=${1:?previous final tag}; IN=${2:?odb}; P=$W/final_from_$PREV
[ "$(df -Pk /mnt/d | awk 'NR==2{print int($4/1048576)}')" -ge 8 ] || { echo "STOP: drive D below 8 GB, final not run"; exit 3; }
mkdir -p $P/results $P/reports
for f in $R/6_* $R/5_3_fillcell.odb $R/5_route.odb $R/5_route.sdc; do [ -e "$f" ] && mv "$f" $P/results/; done
for f in $Rp/6_*; do [ -e "$f" ] && mv "$f" $P/reports/; done
chmod -R a-w $P; echo "parked previous final under $P: $(ls $P/results | wc -l) result files"
export CHIPV2_CDL_MASTERS=/mnt/d/TKVM_ATTT_2026_test/report/orfs_a3_p82/control/r4_connfix216_rcx0114_lvs_fix/sky130hd_with_openram_masters_v3.cdl
bash /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/final_t3.sh $W $IN > /root/t3/t3e_final_$IN.out 2>&1
grep -E "FINAL_(INPUT_HASH|DONE)|FINAL_STEP_FAIL" /root/t3/t3e_final_$IN.out
f=$Rp/6_finish.rpt
grep -E "^(tns|wns|worst slack) max|period_min|violation count" $f
