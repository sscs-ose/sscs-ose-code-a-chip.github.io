#!/usr/bin/env bash
# 2026-10-16 (2nd try): ECO x4 from nc1. x3 (halo met1-3 reaching 0.3 um past the macro bbox and a band over the std-cell row edge) left 104 DRCs there; x4 keeps the halo strictly inside the macro bbox: met1-met3, x 680.87-681.49 (LEF obstruction edge to bbox edge), y 1690-1713.61.
# its LEF obstruction stops short of the edge and the router ran wires into that strip, 4 of the 5 DRCs of nc1;
# re-route the four nets involved), antenna / cleanup rounds p<k>/pc<k>, final; then h4 (SPEF repair_design + ff hold
# repair under +-5 % derate, margin 0.05 ns), antenna / cleanup rounds q<k>/qc<k>, final, three-corner STA.
# log: /root/t3/drv_chain.log
set -u
W=/root/t3/t3e_a3grt; D=sky130hd/trustedge_asic_core/chipv2; R=$W/results/$D; Lg=$W/logs/$D; Rp=$W/reports/$D
LOG=/root/t3/drv_chain.log; F=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip
FF=$(ls /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ff_n40C_1v95.lib)
export OPENROAD_EXE=/opt/eda/openroad-t3patch/bin/openroad CHIPV2_DRT_END_ITER=20 CHIPV2_RENAME_DIODES=1
lastclean() { grep -o "last clean checkpoint: [^ ]*" $LOG | tail -1 | sed 's/.*: //'; }
HALO=""
for l in met1 met2 met3; do HALO="$HALO$l 680.87 1690.0 681.49 1713.61; "; done
echo "$(date +%H:%M) ECO x4 from 5_2_route_nc1.odb: halo met1-3 at the ekPKE corner; nets net31460 net2666 net22909 _175349_" | tee -a $LOG
CHIPV2_TCL=$F/eco_reroute_t3.tcl CHIPV2_ECO_NETS="net31460 net2666 net22909 _175349_" CHIPV2_ROUTE_BLOCKAGES="$HALO" \
  bash $F/drt_round_t3.sh $W x4 5_2_route_nc1.odb drc > /root/t3/t3e_x4.out 2>&1
L=$Lg/5_2_route_x4.log
echo "$(date +%H:%M) x4 $(grep -h DRT_DONE /root/t3/t3e_x4.out | grep -o 'rc=[0-9]*'); blockages $(grep -c routing_blockage $L); DRC: $(grep DRT-0199 $L | sed 's/.*= //' | tr '\n' ' ') report lines $(grep -c . $Rp/5_route_drc_x4.rpt 2>/dev/null); $(grep -o 'antenna_violations_after=[0-9]*' $L)" | tee -a $LOG
[ -f $R/5_2_route_x4.odb ] || { echo "STOP: x4 failed" | tee -a $LOG; exit 1; }
chmod a-w $R/5_2_route_x4.odb
PFX=r CPFX=rc bash $F/ant_chain_t3.sh 5_2_route_x4.odb 1 >> $LOG 2>&1
C1=$(lastclean); echo "$(date +%H:%M) after x4 rounds: $C1 ($(tail -6 $LOG | grep -c 'ANTENNA CLEAN') antenna-clean)" | tee -a $LOG
case "$C1" in 5_2_route_x4.odb|5_2_route_r[0-9]*.odb|5_2_route_rc[0-9]*.odb) ;; *) echo "STOP: no clean checkpoint from x4 rounds ($C1)" | tee -a $LOG; exit 1;; esac
bash $F/final_after_drv_t3.sh x3 $C1 >> $LOG 2>&1
SPEF=$W/spef_${C1%.odb}.spef; cp $R/6_final.spef $SPEF && chmod a-w $SPEF
echo "$(date +%H:%M) h4 from $C1: ff library, SPEF repair_design + hold (derate 0.05, margin 0.05)" | tee -a $LOG
LIB_FILES=$FF CHIPV2_SPEF=$SPEF CHIPV2_HOLD_MARGIN=0.05 CHIPV2_HOLD_DERATE=0.05 CHIPV2_DRV_TCL=$F/drv_spef_round_t3.tcl \
  bash $F/drv_spef_round_t3.sh $W h4 $C1 > /root/t3/t3e_h4.out 2>&1
grep -h -E "CHIPV2_DRV|CHIPV2_HOLD|^worst slack|RSZ-00(32|46)" $Lg/5_2_route_h4.log | tail -12 | tee -a $LOG
rc=$(grep -o "DRT_DONE session=h4 rc=[0-9]*" /root/t3/t3e_h4.out | sed 's/.*rc=//')
echo "$(date +%H:%M) h4 rc=$rc last DRC $(grep DRT-0199 $Lg/5_2_route_h4.log | tail -1 | sed 's/.*= //')" | tee -a $LOG
[ "$rc" = 0 ] && [ -f $R/5_2_route_h4.odb ] || { echo "STOP: h4 failed" | tee -a $LOG; exit 1; }
chmod a-w $R/5_2_route_h4.odb
PFX=s CPFX=sc bash $F/ant_chain_t3.sh 5_2_route_h4.odb 1 >> $LOG 2>&1
C2=$(lastclean); echo "$(date +%H:%M) after h4 rounds: $C2 ($(tail -6 $LOG | grep -c 'ANTENNA CLEAN') antenna-clean)" | tee -a $LOG
case "$C2" in 5_2_route_h4.odb|5_2_route_s[0-9]*.odb|5_2_route_sc[0-9]*.odb) ;; *) echo "STOP: no clean checkpoint from h4 rounds ($C2)" | tee -a $LOG; exit 1;; esac
bash $F/final_after_drv_t3.sh ${C1%.odb} $C2 >> $LOG 2>&1
bash $F/final_sta_t3.sh $R /root/t3/sta_final_h4 > /dev/null 2>&1
grep -v "^[0-9a-f]\{64\}" /root/t3/sta_final_h4/summary.txt | sed 's/clock_latency/lat/g; s/violating_endpoints/viol/g' | tee -a $LOG
echo "$(date +%H:%M) chain4 end; final from $C2" | tee -a $LOG
