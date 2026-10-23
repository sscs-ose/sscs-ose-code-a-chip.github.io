#!/usr/bin/env bash
# 2026-10-17: rest of the t3e w1 sign-off, one job after another (no parallel runs):
# DRC KLayout parts p4..p8 (resume copy keeps p1..p3 from 16/10, same inputs), then LVS prepare/compare/evidence
# (CHIPV2_LVS_TIED_PORTS for the four conb-tied outputs). log: /root/t3/signoff_t3e.log
LOG=/root/t3/signoff_t3e.log; F=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip; C=/mnt/d/TKVM_ATTT_2026_test/chip_v2
WK=/mnt/c/chipv2_signoff/lvs_t3e_w1
echo "$(date +%H:%M) 17/10 chain start: DRC resume" | tee -a $LOG
bash $F/drc_split_resume_20261017.sh run /root/t3/t3e_final_w1/results/6_final.gds /root/t3/drc_t3e_w1 > /root/t3/drc_t3e_resume.out 2>&1
echo "$(date +%H:%M) DRC rc=$? $(grep -h -E 'KEPT|PART_END|DRC_RESULT|BLOCKED' /root/t3/drc_t3e_resume.out | tr '\n' ' ' | cut -c1-900)" | tee -a $LOG
cp $C/lvs/lvs_v2.sh $WK/lvs_v2_run_20261017.sh
export CHIPV2_LVS_TIED_PORTS="entropy_enable_o root_puf_private_mode_o mlkem_done_o mlkem_pass_o"
for s in prepare compare evidence; do
  bash $WK/lvs_v2_run_20261017.sh /root/t3/t3e_final_w1 $WK $s > /root/t3/lvs_t3e_${s}_2.out 2>&1; rc=$?
  echo "$(date +%H:%M) LVS(2) $s rc=$rc $(grep -h -E 'GATE=|PASS|FAIL|match|ERROR' /root/t3/lvs_t3e_${s}_2.out | tail -5 | tr '\n' ' ' | cut -c1-500)" | tee -a $LOG
  [ $rc = 0 ] || break
done
echo "$(date +%H:%M) 17/10 chain end" | tee -a $LOG
