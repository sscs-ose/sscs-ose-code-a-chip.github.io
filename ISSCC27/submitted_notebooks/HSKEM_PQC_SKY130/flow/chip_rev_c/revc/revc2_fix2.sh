#!/usr/bin/env bash
# Rev C rebuild, targeted fix 2 of 2 (last of plan C's budget), 27/10: from fc2 (antenna 0, timing clean, 2 router
# markers: net31530 met1 at the ekPKE frame corner, net23770/net25652 met2 short at x 683.7). f2 = eco_fix_revc2.tcl with
# no new obstruction (added ones made slots before), the three nets ripped, slew/cap repair with fc2's SPEF, detailed
# route (30 iterations). Then antenna rounds ga/gc, final, STA.   log: /root/t3/revc2.log
set -u
export REVC_W=/root/t3/revc2_a3grt
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
export CHIPV2_RENAME_DIODES=1
H=$ROOT/hskem_revc/flow; LOG=/root/t3/revc2.log
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
stop() { say "STOP: $*"; exit 1; }
SPEF=$W/spef_fc2.spef; [ -f $SPEF ] || { cp $R/6_final.spef $SPEF; chmod a-w $SPEF; }
NETS="net31530 net23770 net25652"
say "fix 2: f2 from 5_2_route_fc2.odb: rip [$NETS], no new obstruction, slew/cap repair with fc2's SPEF"
CHIPV2_SPEF=$SPEF CHIPV2_DRV_TCL=$H/eco_fix_revc2.tcl CHIPV2_DRT_END_ITER=30 CHIPV2_ECO_NETS="$NETS" CHIPV2_ROUTE_BLOCKAGES="" \
  bash $H/revc_drv_round.sh $W f2 5_2_route_fc2.odb > /root/t3/revc2_f2.out 2>&1
grep -h -E "CHIPV2_(ECO|DRV|ROUND)=f2" $Lg/5_2_route_f2.log | grep -v 'net=' | tee -a $LOG
[ -f $R/5_2_route_f2.odb ] || stop "f2 failed"; chmod a-w $R/5_2_route_f2.odb
say "f2: router markers $(grep -c 'violation type' $Rp/5_route_drc_f2.rpt), iterations: $(grep DRT-0199 $Lg/5_2_route_f2.log | sed 's/.*= //' | tr '\n' ' ')"
ANT_LOG=/root/t3/revc2_fix2_ant.log PFX=ga CPFX=gc bash $H/revc_ant_chain.sh 5_2_route_f2.odb 1 >> $LOG 2>&1
C=$(grep -o "last clean checkpoint: [^ ]*" /root/t3/revc2_fix2_ant.log | tail -1 | sed 's/.*: //')
case "$C" in 5_2_route_f2.odb|5_2_route_ga[0-9]*.odb|5_2_route_gc[0-9]*.odb) ;; *) stop "no checkpoint from ga/gc rounds ($C)";; esac
T=${C#5_2_route_}; T=${T%.odb}
A=$(grep -o 'antenna_violations_after=[0-9]*' $Lg/5_2_route_$T.log | tail -1 | sed 's/.*=//'); M=$(grep -c 'violation type' $Rp/5_route_drc_$T.rpt)
say "after ga/gc rounds: $C antenna ${A:-?}, router markers $M"
[ "${A:-1}" = 0 ] || stop "$C has antenna ${A:-?}"
bash $H/revc_final.sh $C fc2 | tee -a $LOG
mkdir -p /root/t3/sta_revc2_fix2
bash $FC/final_sta_t3.sh $R /root/t3/sta_revc2_fix2 > /dev/null 2>&1
grep -v "^[0-9a-f]\{64\}" /root/t3/sta_revc2_fix2/summary.txt | grep soc | sed -E 's/clock_latency_(min|max) [0-9.]+ //g; s/io_clk_ports in [0-9]+ out [0-9]+ //' | tee -a $LOG
bad=$(grep soc /root/t3/sta_revc2_fix2/summary.txt | grep -c -v -E 'setup_violating_endpoints 0 hold_violating_endpoints 0')
grep 'violation type' $Rp/5_route_drc_$T.rpt | sort | uniq -c | tee -a $LOG
[ "$M" = 0 ] && [ "$bad" = 0 ] && say "revc2 CLEAN after fix 2: final from $C; ready for sign-off" || say "fix 2 end: router markers $M, SoC timing rows with violations $bad"
