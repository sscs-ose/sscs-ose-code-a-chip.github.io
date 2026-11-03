#!/usr/bin/env bash
# Rev C sign-off of the final now in place (rev B's signoff_t3e.sh + chain_20261017.sh with the published copies of the
# scripts in codeachip/flow/chip_rev_b/signoff), one job after another: park the final as a read-only copy, LVS (4
# stages, scratch on C; the conb-tied outputs read from the final netlist), FEOL, the BEOL + OFFGRID DRC as eight part
# decks, and the key scan of the text outputs (counts only).
# usage: revc_signoff.sh <tag of the final, e.g. jc2>   log: /root/t3/revc_signoff.log
set -u
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
TAG=${1:?tag}; LOG=/root/t3/revc_signoff.log; S=$ROOT/codeachip/flow/chip_rev_b/signoff
P=/root/t3/revc_final_$TAG; WK=/mnt/c/chipv2_signoff/lvs_revc_$TAG; DRC=/root/t3/drc_revc_$TAG
[ -e $P ] && { echo "STOP: $P exists" | tee -a $LOG; exit 1; }
mkdir -p $P/results $P/objects $WK
cp $W/results/sky130hd/trustedge_asic_core/chipv2/6_final.{gds,def,v,spef,odb,sdc} $P/results/ && \
  cp $W/objects/sky130hd/trustedge_asic_core/chipv2/6_final_concat.cdl $P/objects/ || { echo "STOP: copy failed" | tee -a $LOG; exit 1; }
chmod -R a-w $P; sha256sum $P/results/* $P/objects/* > /root/t3/revc_final_$TAG.sha256
echo "$(date +%H:%M) parked final under $P" | tee -a $LOG
export CHIPV2_LVS_TIED_PORTS="$(python3 $ROOT/hskem_revc/flow/revc_tied_ports.py $P/results/6_final.v)"
echo "$(date +%H:%M) tied outputs: $CHIPV2_LVS_TIED_PORTS" | tee -a $LOG
for s in extract prepare compare evidence; do
  bash $S/lvs/lvs_v2.sh $P $WK $s > /root/t3/lvs_revc_$s.out 2>&1; rc=$?
  echo "$(date +%H:%M) LVS $s rc=$rc $(grep -h -E 'GATE=|RESULT|PASS|FAIL|match' /root/t3/lvs_revc_$s.out | tail -4 | tr '\n' ' ' | cut -c1-400)" | tee -a $LOG
  [ $rc = 0 ] || break
done
bash $S/feol_chipv2.sh $P/results/6_final.gds /root/t3/feol_revc_$TAG > /root/t3/feol_revc.out 2>&1
echo "$(date +%H:%M) FEOL rc=$? $(tail -4 /root/t3/feol_revc.out | tr '\n' ' ' | cut -c1-300)" | tee -a $LOG
echo "$(date +%H:%M) DRC start" | tee -a $LOG
bash $S/signoff_drc_split.sh run $P/results/6_final.gds $DRC > /root/t3/drc_revc.out 2>&1
echo "$(date +%H:%M) DRC rc=$? $(tail -12 /root/t3/drc_revc.out | tr '\n' ' ' | cut -c1-600)" | tee -a $LOG
python3 $ROOT/codeachip_t3/flow_chip/keyscan_t3.py $P/results/6_final.v $P/results/6_final.def $P/objects/6_final_concat.cdl 2>&1 \
  | grep -E '^/|KEYSCAN|private keys' | tee -a $LOG
echo "$(date +%H:%M) revc signoff end" | tee -a $LOG
