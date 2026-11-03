#!/usr/bin/env bash
# Rev C rebuild (plan C, 25/10): rev C's placed and clock-tree-synthesized database (/root/t3/revc1, unchanged netlist and
# placement) routed again with the root-cause fix and the timing closed before routing. Stages:
#   grt     global route with rev B's recipe (grt_a3recipe.sh) and the macro frame obstructions (pre_grt_revc2.tcl)
#   grtchk  gate on the frame obstructions, STA of the global route (SPICE views)
#   gt      g1 setup repair at ss on the global route (ss SPICE macro views, SoC I/O model, derate 0.05, margin 0.3 ns);
#           g2 hold repair at ff (original macro views, the pessimistic side; SoC model, derate 0.05, margin 0.1 ns);
#           g3 check at ss (one more setup pass if it fell below +0.2 ns) and at ff; the result becomes 5_1_grt.odb
#   drt     main detailed route, up to 64 iterations
#   ant     antenna / clean-up rounds (revc_ant_chain.sh, diode renaming on)
#   fin     final stage, sign-off STA at three corners (final_sta_t3.sh)
# Every stage has a gate; the chain stops at the first failure. Work home /root/t3/revc2_a3grt, log /root/t3/revc2.log.
# usage: revc2_chain.sh [first stage] [last stage]   (default grt fin; 25/10: grtchk gt tonight, drt fin next morning)
set -u
export REVC_W=/root/t3/revc2_a3grt
source /mnt/d/TKVM_ATTT_2026_test/hskem_revc/flow/revc_env.sh
export CHIPV2_RENAME_DIODES=1
H=$ROOT/hskem_revc/flow; MV=/root/t3/revc_macro_views; LOG=/root/t3/revc2.log
STAGES="grt grtchk gt drt ant fin"
idx() { local i=0 s; for s in $STAGES; do [ $s = $1 ] && { echo $i; return; }; i=$((i + 1)); done; echo -1; }
I0=$(idx ${1:-grt}); I1=$(idx ${2:-fin})
[ $I0 -ge 0 ] && [ $I1 -ge $I0 ] || { echo "usage: revc2_chain.sh [first] [last] with stages: $STAGES"; exit 2; }
on() { local i=$(idx $1); [ $i -ge $I0 ] && [ $i -le $I1 ]; }
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
stop() { say "STOP: $*"; exit 1; }
dguard() { local f=$(df -Pk /mnt/d | awk 'NR==2{print int($4/1048576)}'); [ "$f" -ge 9 ] || stop "drive D has only ${f} GB free"; }
grt_line() { grep -h "CHIPV2_GRT=$1 $2" $Lg/5_1_grt_$1.log | tail -1; }
val() { echo "$1" | grep -o "$2 [-0-9.]*" | awk '{print $2}'; }
checkpoint() {   # sets C (last clean checkpoint of the antenna chain, or REVC2_CKPT), T, A (antenna), M (router markers)
  C=${REVC2_CKPT:-}; [ -n "$C" ] || C=$(grep -o "last clean checkpoint: [^ ]*" /root/t3/revc2_ant_chain.log 2>/dev/null | tail -1 | sed 's/.*: //')
  case "$C" in 5_2_route.odb) T=main;; 5_2_route_b[0-9]*.odb|5_2_route_cl[0-9]*.odb) T=${C#5_2_route_}; T=${T%.odb};; *) stop "no checkpoint from the antenna chain ($C)";; esac
  if [ $T = main ]; then A=$(grep -o 'antenna_violations_after=[0-9]*' $Lg/5_2_route.log | tail -1 | sed 's/.*=//'); M=$(grep -c 'violation type' $Rp/5_route_drc.rpt)
  else A=$(grep -o 'antenna_violations_after=[0-9]*' $Lg/5_2_route_$T.log | tail -1 | sed 's/.*=//'); M=$(grep -c 'violation type' $Rp/5_route_drc_$T.rpt); fi
}

say "revc2 stages ${1:-grt}..${2:-fin}"
dguard
if on grt; then
  say "grt: global route with frame obstructions, from /root/t3/revc1 (4_cts)"
  CHIPV2_PRE_GRT_TCL=$H/pre_grt_revc2.tcl bash $FC/grt_a3recipe.sh /root/t3/revc1 $W > /root/t3/revc2_grt.out 2>&1
fi
if on grtchk; then
  [ -f $R/5_1_grt.odb ] || stop "global route failed (revc2_grt.out)"
  F=$(grep -h "REVC2_FRAME macros" $Lg/5_1_grt.log | tail -1); say "grt: $F"
  echo "$F" | grep -q "macros=18 obstructions_added=180 obstructions_before=0" || stop "frame obstructions not as expected"
  chmod a-w $R/5_1_grt.odb
  bash $ROOT/codeachip_t3/scripts/t3_spice_sta.sh $R /root/t3/sta_revc2_grt0 > /dev/null 2>&1
  say "grt STA (sdc mode, SPICE views): $(grep -E '^(ss_spice|ff_view) ' /root/t3/sta_revc2_grt0/summary.txt | tr '\n' ' ' | cut -c1-400)"
fi
if on gt; then
  [ -f $R/5_1_grt_orfs.odb ] && stop "timing at the global route already done (5_1_grt_orfs.odb exists)"
  LIB_FILES=$SS CHIPV2_MACRO_LIB_DIR=$MV/ss CHIPV2_GRT_MODE=setup CHIPV2_DERATE=0.05 CHIPV2_MARGIN=0.3 \
    bash $H/revc_grt_eco.sh $W g1 5_1_grt.odb > /root/t3/revc2_g1.out 2>&1
  [ -f $R/5_1_grt_g1.odb ] || stop "g1 failed"
  say "g1 (ss setup): $(grt_line g1 before) -> $(grt_line g1 after)"
  LIB_FILES=$FF CHIPV2_GRT_MODE=hold CHIPV2_DERATE=0.05 CHIPV2_MARGIN=0.1 \
    bash $H/revc_grt_eco.sh $W g2 5_1_grt_g1.odb > /root/t3/revc2_g2.out 2>&1
  [ -f $R/5_1_grt_g2.odb ] || stop "g2 failed"
  say "g2 (ff hold): $(grt_line g2 before) -> $(grt_line g2 after)"
  G=5_1_grt_g2.odb
  LIB_FILES=$SS CHIPV2_MACRO_LIB_DIR=$MV/ss CHIPV2_GRT_MODE=report CHIPV2_DERATE=0.05 \
    bash $H/revc_grt_eco.sh $W g3s $G > /root/t3/revc2_g3s.out 2>&1
  s=$(val "$(grt_line g3s before)" setup_wns); say "g3 ss check after hold repair: $(grt_line g3s before)"
  if awk "BEGIN{exit !($s < 0.2)}"; then
    LIB_FILES=$SS CHIPV2_MACRO_LIB_DIR=$MV/ss CHIPV2_GRT_MODE=setup CHIPV2_DERATE=0.05 CHIPV2_MARGIN=0.3 \
      bash $H/revc_grt_eco.sh $W g4 $G > /root/t3/revc2_g4.out 2>&1
    [ -f $R/5_1_grt_g4.odb ] || stop "g4 failed"
    say "g4 (ss setup again): $(grt_line g4 before) -> $(grt_line g4 after)"; G=5_1_grt_g4.odb
    s=$(val "$(grt_line g4 after)" setup_wns)
  fi
  LIB_FILES=$FF CHIPV2_GRT_MODE=report CHIPV2_DERATE=0.05 bash $H/revc_grt_eco.sh $W g3f $G > /root/t3/revc2_g3f.out 2>&1
  h=$(val "$(grt_line g3f before)" hold_wns); say "g3 ff check: $(grt_line g3f before)"
  awk "BEGIN{exit !($s >= 0.2 && $h >= 0.05)}" || stop "global-route timing gate: ss setup $s (need >= 0.2), ff hold $h (need >= 0.05)"
  chmod u+w $R/5_1_grt.odb; mv $R/5_1_grt.odb $R/5_1_grt_orfs.odb; cp -p $R/$G $R/5_1_grt.odb; chmod a-w $R/5_1_grt.odb $R/5_1_grt_orfs.odb
  say "global route with closed timing: $G -> 5_1_grt.odb (ORFS original kept as 5_1_grt_orfs.odb)"
  bash $ROOT/codeachip_t3/scripts/t3_spice_sta.sh $R /root/t3/sta_revc2_grt > /dev/null 2>&1
  say "grt STA after g-steps (sdc mode): $(grep -E '^(ss_spice|ff_view) ' /root/t3/sta_revc2_grt/summary.txt | tr '\n' ' ' | cut -c1-400)"
fi
if on drt; then
  dguard
  [ -f $R/5_1_grt_orfs.odb ] || stop "timing at the global route not done yet (stage gt)"
  say "drt: main detailed route (64 iterations)"
  CHIPV2_DRT_END_ITER=64 bash $FC/drt_t3.sh $W > /root/t3/revc2_drt.out 2>&1
  [ -f $R/5_2_route.odb ] || stop "main detailed route failed (revc2_drt.out)"
  say "drt done: router markers $(grep -c 'violation type' $Rp/5_route_drc.rpt 2>/dev/null), iterations: $(grep DRT-0199 $Lg/5_2_route.log | sed 's/.*= //' | tr '\n' ' ')"
fi
if on ant; then
  dguard
  ANT_LOG=/root/t3/revc2_ant_chain.log PFX=b CPFX=cl bash $H/revc_ant_chain.sh 5_2_route.odb 1 >> $LOG 2>&1
  checkpoint
  say "after antenna rounds: $C antenna ${A:-?}, router markers $M"
  [ "${A:-1}" = 0 ] || stop "$C has antenna ${A:-?}"
fi
if on fin; then
  checkpoint
  bash $H/revc_final.sh $C none | tee -a $LOG
  mkdir -p /root/t3/sta_revc2_final
  bash $FC/final_sta_t3.sh $R /root/t3/sta_revc2_final > /dev/null 2>&1
  grep -v "^[0-9a-f]\{64\}" /root/t3/sta_revc2_final/summary.txt | grep soc | sed -E 's/clock_latency_(min|max) [0-9.]+ //g; s/io_clk_ports in [0-9]+ out [0-9]+ //' | tee -a $LOG
  bad=$(grep soc /root/t3/sta_revc2_final/summary.txt | grep -c -v -E 'setup_violating_endpoints 0 hold_violating_endpoints 0')
  [ "$M" = 0 ] || stop "final from $C: router markers $M (targeted fix needed, at most 2 tries); timing rows with violations: $bad"
  [ "$bad" = 0 ] || stop "final from $C: $bad SoC timing rows with violations"
  say "revc2 CLEAN: final from $C, router markers 0, antenna 0, SoC timing clean at every corner incl. derate; ready for sign-off"
fi
say "revc2 stages ${1:-grt}..${2:-fin} end"
