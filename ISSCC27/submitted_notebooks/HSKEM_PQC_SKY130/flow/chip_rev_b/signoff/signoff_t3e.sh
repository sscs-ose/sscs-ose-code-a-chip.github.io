#!/usr/bin/env bash
# 2026-10-16: sign-off of the t3e final from 5_2_route_w1 (x6: DRC 0, antenna 0, SoC-model STA clean at ss/tt/ff incl.
# +-5 % derate). The final is parked as a copy, then LVS (chip_v2/lvs/lvs_v2.sh, 4 stages, scratch on C) and FEOL
# (chip_v2/feol_chipv2.sh) run side by side, then the BEOL + OFFGRID DRC (chip_v2/signoff_drc_split.sh) runs alone.
# log: /root/t3/signoff_t3e.log
set -u
W=/root/t3/t3e_a3grt; D=sky130hd/trustedge_asic_core/chipv2; P=/root/t3/t3e_final_w1; C=/mnt/d/TKVM_ATTT_2026_test/chip_v2
LOG=/root/t3/signoff_t3e.log
mkdir -p $P/results $P/objects
cp $W/results/$D/6_final.{gds,def,v,spef,odb,sdc} $P/results/ && cp $W/objects/$D/6_final_concat.cdl $P/objects/
chmod -R a-w $P; sha256sum $P/results/* $P/objects/* > /root/t3/t3e_final_w1.sha256
echo "$(date +%H:%M) parked final under $P" | tee -a $LOG
( for s in extract prepare compare evidence; do
    bash $C/lvs/lvs_v2.sh $P /mnt/c/chipv2_signoff/lvs_t3e_w1 $s > /root/t3/lvs_t3e_$s.out 2>&1; rc=$?
    echo "$(date +%H:%M) LVS $s rc=$rc $(grep -h -E 'GATE=|RESULT|PASS|FAIL' /root/t3/lvs_t3e_$s.out | tail -3 | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
    [ $rc = 0 ] || break
  done ) &
L=$!
bash $C/feol_chipv2.sh $P/results/6_final.gds /root/t3/feol_t3e_w1 > /root/t3/feol_t3e.out 2>&1
echo "$(date +%H:%M) FEOL rc=$? $(tail -4 /root/t3/feol_t3e.out | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
wait $L
echo "$(date +%H:%M) DRC start" | tee -a $LOG
bash $C/signoff_drc_split.sh run $P/results/6_final.gds /root/t3/drc_t3e_w1 > /root/t3/drc_t3e.out 2>&1
echo "$(date +%H:%M) DRC rc=$? $(tail -12 /root/t3/drc_t3e.out | tr '\n' ' ' | cut -c1-600)" | tee -a $LOG
echo "$(date +%H:%M) signoff_t3e end" | tee -a $LOG
