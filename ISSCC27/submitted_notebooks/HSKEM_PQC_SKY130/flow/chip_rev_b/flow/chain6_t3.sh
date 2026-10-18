#!/usr/bin/env bash
# 2026-10-16: ECO x6 from vc1 (eco_hold_io_t3.tcl): halo at the ekPKE corner lowered to y 1713.40, the nets of the last
# 2 DRCs ripped and routed again, hold repair under the SoC I/O model at ff with +-5 % derate (margin 0.05 ns);
# antenna / cleanup rounds w<k>/wc<k>, final, three-corner STA. log: /root/t3/drv_chain.log
set -u
W=/root/t3/t3e_a3grt; D=sky130hd/trustedge_asic_core/chipv2; R=$W/results/$D; Lg=$W/logs/$D; Rp=$W/reports/$D
LOG=/root/t3/drv_chain.log; F=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip
FF=$(ls /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ff_n40C_1v95.lib)
export OPENROAD_EXE=/opt/eda/openroad-t3patch/bin/openroad CHIPV2_DRT_END_ITER=20 CHIPV2_RENAME_DIODES=1
lastclean() { grep -o "last clean checkpoint: [^ ]*" $LOG | tail -1 | sed 's/.*: //'; }
HALO=""; for l in met1 met2 met3; do HALO="$HALO$l 680.87 1690.0 681.49 1713.40; "; done
SPEF=$W/spef_5_2_route_vc1.spef; cp $R/6_final.spef $SPEF && chmod a-w $SPEF
echo "$(date +%H:%M) ECO x6 from 5_2_route_vc1.odb: halo top 1713.40, rip 3 nets, SoC-model hold repair at ff (derate 0.05, margin 0.05)" | tee -a $LOG
LIB_FILES=$FF CHIPV2_SPEF=$SPEF CHIPV2_HOLD_MARGIN=0.05 CHIPV2_HOLD_DERATE=0.05 CHIPV2_DRV_TCL=$F/eco_hold_io_t3.tcl \
  CHIPV2_CLEAR_BOX="680.8 1689.0 681.5 1713.7" CHIPV2_ROUTE_BLOCKAGES="$HALO" \
  CHIPV2_ECO_NETS='u_common.u_mlkem512_kpke_partial.u_matrix_mac.gamma_index[0] net31550 _175347_' \
  bash $F/drv_spef_round_t3.sh $W x6 5_2_route_vc1.odb > /root/t3/t3e_x6.out 2>&1
grep -h -E "CHIPV2_ECO|CHIPV2_HOLD|^worst slack|RSZ-00(32|46)" $Lg/5_2_route_x6.log | tail -16 | tee -a $LOG
rc=$(grep -o "DRT_DONE session=x6 rc=[0-9]*" /root/t3/t3e_x6.out | sed 's/.*rc=//')
echo "$(date +%H:%M) x6 rc=$rc DRC: $(grep DRT-0199 $Lg/5_2_route_x6.log | sed 's/.*= //' | tr '\n' ' ') $(grep -o 'antenna_violations_after=[0-9]*' $Lg/5_2_route_x6.log)" | tee -a $LOG
[ "$rc" = 0 ] && [ -f $R/5_2_route_x6.odb ] || { echo "STOP: x6 failed" | tee -a $LOG; exit 1; }
chmod a-w $R/5_2_route_x6.odb
PFX=w CPFX=wc bash $F/ant_chain_t3.sh 5_2_route_x6.odb 1 >> $LOG 2>&1
C=$(lastclean); echo "$(date +%H:%M) after x6 rounds: $C" | tee -a $LOG
case "$C" in 5_2_route_x6.odb|5_2_route_w[0-9]*.odb|5_2_route_wc[0-9]*.odb) ;; *) echo "STOP: no clean checkpoint from x6 rounds ($C)" | tee -a $LOG; exit 1;; esac
bash $F/final_after_drv_t3.sh vc1 $C >> $LOG 2>&1
bash $F/final_sta_t3.sh $R /root/t3/sta_final_x6 > /dev/null 2>&1
grep -v "^[0-9a-f]\{64\}" /root/t3/sta_final_x6/summary.txt | sed 's/clock_latency/lat/g; s/violating_endpoints/viol/g' | tee -a $LOG
echo "$(date +%H:%M) chain6 end; final from $C" | tee -a $LOG
