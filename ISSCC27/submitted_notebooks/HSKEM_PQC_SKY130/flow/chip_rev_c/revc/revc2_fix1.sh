#!/usr/bin/env bash
# Rev C rebuild, targeted fix 1 of 2 (budget of plan C), 26/10: from b5 (antenna 0, 10 router markers, final + STA done:
# timing clean, 343/37 slew/cap violations at tt). f1 = eco_fix_revc2.tcl: met4 obstruction over the ekPKE vccd1 met4 pin
# strip at the corner (x 679.75-681.49, y 1690.0-1713.61; the nearest PDN via sits at y 1689.12, below it), the six
# signal nets of the markers ripped (not the clock net), slew/cap repair with b5's SPEF, detailed route (30 iterations).
# Then antenna rounds fa/fc (clean-up skipped once it stops helping), final, STA.   log: /root/t3/revc2.log
set -u
export REVC_W=/root/t3/revc2_a3grt
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
export CHIPV2_RENAME_DIODES=1
H=$ROOT/hskem_revc/flow; LOG=/root/t3/revc2.log
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
stop() { say "STOP: $*"; exit 1; }
SPEF=$W/spef_b5.spef; [ -f $SPEF ] || { cp $R/6_final.spef $SPEF; chmod a-w $SPEF; }
NETS="net31530 net29885 net27508 _040770_ net30576 net27412"
say "fix 1: f1 from 5_2_route_b5.odb: met4 block on the ekPKE vccd1 pin strip at the corner, rip [$NETS], slew/cap repair with b5's SPEF"
CHIPV2_SPEF=$SPEF CHIPV2_DRV_TCL=$H/eco_fix_revc2.tcl CHIPV2_DRT_END_ITER=30 CHIPV2_ECO_NETS="$NETS" \
  CHIPV2_ROUTE_BLOCKAGES="met4 679.75 1690.0 681.49 1713.61" \
  bash $H/revc_drv_round.sh $W f1 5_2_route_b5.odb > /root/t3/revc2_f1.out 2>&1
grep -h -E "CHIPV2_(ECO|DRV|ROUND)=f1" $Lg/5_2_route_f1.log | grep -v 'net=' | tee -a $LOG
[ -f $R/5_2_route_f1.odb ] || stop "f1 failed"; chmod a-w $R/5_2_route_f1.odb
say "f1: router markers $(grep -c 'violation type' $Rp/5_route_drc_f1.rpt), iterations: $(grep DRT-0199 $Lg/5_2_route_f1.log | sed 's/.*= //' | tr '\n' ' ')"
ANT_LOG=/root/t3/revc2_fix1_ant.log PFX=fa CPFX=fc bash $H/revc_ant_chain.sh 5_2_route_f1.odb 1 >> $LOG 2>&1
C=$(grep -o "last clean checkpoint: [^ ]*" /root/t3/revc2_fix1_ant.log | tail -1 | sed 's/.*: //')
case "$C" in 5_2_route_f1.odb|5_2_route_fa[0-9]*.odb|5_2_route_fc[0-9]*.odb) ;; *) stop "no checkpoint from fa/fc rounds ($C)";; esac
T=${C#5_2_route_}; T=${T%.odb}
A=$(grep -o 'antenna_violations_after=[0-9]*' $Lg/5_2_route_$T.log | tail -1 | sed 's/.*=//'); M=$(grep -c 'violation type' $Rp/5_route_drc_$T.rpt)
say "after fa/fc rounds: $C antenna ${A:-?}, router markers $M"
[ "${A:-1}" = 0 ] || stop "$C has antenna ${A:-?}"
bash $H/revc_final.sh $C b5 | tee -a $LOG
mkdir -p /root/t3/sta_revc2_fix1
bash $FC/final_sta_t3.sh $R /root/t3/sta_revc2_fix1 > /dev/null 2>&1
grep -v "^[0-9a-f]\{64\}" /root/t3/sta_revc2_fix1/summary.txt | grep soc | sed -E 's/clock_latency_(min|max) [0-9.]+ //g; s/io_clk_ports in [0-9]+ out [0-9]+ //' | tee -a $LOG
bad=$(grep soc /root/t3/sta_revc2_fix1/summary.txt | grep -c -v -E 'setup_violating_endpoints 0 hold_violating_endpoints 0')
grep 'violation type' $Rp/5_route_drc_$T.rpt | sort | uniq -c | tee -a $LOG
[ "$M" = 0 ] && [ "$bad" = 0 ] && say "revc2 CLEAN after fix 1: final from $C; ready for sign-off" || say "fix 1 end: router markers $M, SoC timing rows with violations $bad"
