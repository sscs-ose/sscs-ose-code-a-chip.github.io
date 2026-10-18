#!/usr/bin/env bash
# 2026-10-17: LVS prepare/compare/evidence of t3e w1 (second try: the supply guard now splits KLayout's merged net
# names on "," as well as "|"). log: /root/t3/signoff_t3e.log
LOG=/root/t3/signoff_t3e.log; C=/mnt/d/TKVM_ATTT_2026_test/chip_v2; WK=/mnt/c/chipv2_signoff/lvs_t3e_w1
cp $C/lvs/lvs_v2.sh $WK/lvs_v2_run_20261017c.sh
export CHIPV2_LVS_TIED_PORTS="entropy_enable_o root_puf_private_mode_o mlkem_done_o mlkem_pass_o"
for s in prepare compare evidence; do
  bash $WK/lvs_v2_run_20261017c.sh /root/t3/t3e_final_w1 $WK $s > /root/t3/lvs_t3e_${s}_4.out 2>&1; rc=$?
  echo "$(date +%H:%M) LVS(4) $s rc=$rc $(grep -h -E 'GATE=|PASS|FAIL|match|ERROR' /root/t3/lvs_t3e_${s}_4.out | tail -5 | tr '\n' ' ' | cut -c1-500)" | tee -a $LOG
  [ $rc = 0 ] || break
done
