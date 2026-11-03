#!/usr/bin/env bash
# 2026-10-17: gate-level run of the t3e final netlist (w1) over the full-system window, after the sign-off chain of the
# day (waits for "17/10 chain end"). RTL = the exact synthesized root (build_t3e/root, placeholder key) with the 14 T3
# defines; shadow skip list by instance name from the t3e FSM listing (18 recoded FSMs) on the w1 netlist. No VCD.
LOG=/root/t3/signoff_t3e.log; T3=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3
SCR=/mnt/c/Users/Win/AppData/Local/Temp/claude/D--TKVM-ATTT-2026-test/67334b5c-7dfb-4617-ac47-060070674772/scratchpad/fsmlist
W=/root/real_gls_t3e; B=/root/t3/t3e_final_w1/results
until grep -q "17/10 chain end" $LOG; do sleep 60; done
mkdir -p $W; [ -d $W/hskem_rtl ] || cp -r $T3/build_t3e/root $W/hskem_rtl
python3 $SCR/mkskip_t3e.py $B/6_final.v $W/shadow_skip.txt | tee $W/mkskip.log
D=""; for d in MAC_DEEP MM_PIPE CRC_SERIAL BARRETT_1C SA_PIPE PMAC_RAW CODEC_RETIME MSG_PIPE PP_EARLY LOAD_PIPE MARGIN MUL_SEL SEL_REP EK_PREF; do D="$D -DTRUSTEDGE_T3_$d"; done
echo "$(date +%H:%M) GLS t3e start ($(head -1 $W/mkskip.log))" | tee -a $LOG
FULLCHIP_DIR=$B REAL_GLS_WORK=$W T3_GLS_DEFS="$D" bash $T3/scripts/real_gls_window.sh > $W/run.out 2>&1
echo "$(date +%H:%M) GLS t3e rc=$? $(grep -h -E 'REAL_CHIP|DECAPS|compile failed|Elapsed' $W/run.out | tail -6 | tr '\n' ' ' | cut -c1-600)" | tee -a $LOG
