#!/usr/bin/env bash
# (28/10) The rev C runs that rev B's notebook results need and the sign-off extras did not make, on the final ga1
# (/root/t3/revc_final_ga1), one job after another, in the order of rev B's scripts (codeachip/flow/chip_rev_b/analysis):
#   stage  cells.csv.gz (dump_cells.tcl), blocks.csv (fullchip_blocks.py in a mirror), fullchip_layout.png (render_gds.py)
#   sram   SRAM accesses of one decapsulation: the system simulation of power_revc.sh with sram_access_counter_v2.sv,
#          then collect_sram_accesses.py and sram_energy_model.py; its log is also the rev C full-system log
#   hold   hold paths into the SRAM macro inputs at ss/tt/ff (final_sta.tcl MACRO_HOLD=1)
#   fmax   fmax by bisection on the clock period at ss/tt/ff and ss +-5 % (final_sta.tcl FMAX_SEARCH=1)
#   acvp   byte-exact ACVP-derived encapsulation/decapsulation of the rev C RTL (acvp_encdec_t3e.py, 25 cases)
#   iru    static IR drop with the uniform 0.1 activity (rev B's ir_w1_edge run)
# usage (WSL, root): revc_collect_runs.sh [step ...]   default: all steps; log /root/t3/revc_collect_runs.log
set -uo pipefail
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test CAC=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3
readonly FINAL=/root/t3/revc_final_ga1 B=/root/t3/revc_final_ga1/results
readonly STAGE=$ROOT/hskem_revc/results/fullchip_stage MIRROR=$ROOT/hskem_revc/results/stage_root
readonly OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad V=/root/t3/sta_revc2_fix2/views
readonly LOG=/root/t3/revc_collect_runs.log
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
STEPS="${*:-stage sram hold fmax acvp iru}"
mkdir -p $STAGE

# the chip's defines: those of power_revc.sh (rev B's 14 tier-3 defines + TRUSTEDGE_REVC)
H="-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP -DTRUSTEDGE_STREAM_IO"
H="$H -DTRUSTEDGE_FAST_BASEMUL -DTRUSTEDGE_FAST_FEED -DTRUSTEDGE_STREAM_OUT -DTRUSTEDGE_FOLD_READBACK"
H="$H -DTRUSTEDGE_PREFETCH -DTRUSTEDGE_TIGHT_LOOPS -DTRUSTEDGE_FAST_CHECK -DTRUSTEDGE_FAST_Y"
H="$H -DTRUSTEDGE_PACKED2 -DTRUSTEDGE_FAST_PRF -DTRUSTEDGE_FUSED_CMP -DTRUSTEDGE_FAST_READ"
H="$H -DTRUSTEDGE_PIPE_CHECK -DTRUSTEDGE_PAIR_PORT -DTRUSTEDGE_DEFER_J -DTRUSTEDGE_PIPE_MAC -DTRUSTEDGE_FAST_HASH"
H="$H -DTRUSTEDGE_DEC_STREAM -DTRUSTEDGE_SEG_CHECK -DTRUSTEDGE_BG_PRF -DTRUSTEDGE_STREAM_INV -DTRUSTEDGE_STREAM_FWD"
H="$H -DTRUSTEDGE_PRF_TO_NTT -DTRUSTEDGE_STREAM_DEC_INV -DTRUSTEDGE_PRF_FINE_HOLD -DTRUSTEDGE_POLY_GUARD"
DEFS="-DFUNCTIONAL -DUNIT_DELAY=#0 -DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS"
DEFS="$DEFS $H -DTRUSTEDGE_PMAC_RETIME -DTRUSTEDGE_SO_PIPE"
for d in MAC_DEEP MM_PIPE CRC_SERIAL BARRETT_1C SA_PIPE PMAC_RAW CODEC_RETIME MSG_PIPE PP_EARLY LOAD_PIPE MARGIN MUL_SEL SEL_REP EK_PREF; do
  DEFS="$DEFS -DTRUSTEDGE_T3_$d"; done
DEFS="$DEFS -DTRUSTEDGE_REVC"
F=$(sed -n '/^F=(/,/)$/p' "${CAC}/scripts/run_system_sim.sh" | tr -d '()"' | sed 's/^F=//; s#\${CAC_TB:-sim/tb/tb_trustedge_spi.sv}#sim/tb/tb_trustedge_spi.sv#')
F="$F rtl/kyber/barrett_reduce_1c.v rtl/kyber/kyber_ntt_engine_packed.sv rtl/kyber/kyber_ntt_engine_packed2.sv"
SRC=/root/real_gls_revc/hskem_rtl   # rev C root + the GLS-only kyber_zeta qualification (SOURCE_EDITS.txt), as power_revc.sh

say "start: $STEPS (final $(sha256sum $B/6_final.odb | cut -c1-16))"
for s in $STEPS; do case $s in
stage)
  PDK="$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)"
  mkdir -p $MIRROR/scripts $MIRROR/results/fullchip; TMP=$(mktemp -d /root/stagecells.XXXX)
  ODB=$B/6_final.odb OUT=$TMP/cells.csv $OR -no_splash -exit $ROOT/codeachip/flow/dump_cells.tcl > $TMP/dump.log 2>&1
  say "stage cells rows=$(wc -l < $TMP/cells.csv) macros=$(awk -F, '$6==1' $TMP/cells.csv | wc -l)"
  gzip -9 -n -c $TMP/cells.csv > $STAGE/cells.csv.gz; rm -rf $TMP
  cp $ROOT/codeachip/scripts/fullchip_blocks.py $MIRROR/scripts/
  cp $STAGE/cells.csv.gz $MIRROR/results/fullchip/cells.csv.gz
  python3 $MIRROR/scripts/fullchip_blocks.py $B/6_final.v $PDK/sky130_fd_sc_hd__tt_025C_1v80.lib | tail -3
  cp $MIRROR/results/fullchip/blocks.csv $STAGE/blocks.csv
  /usr/bin/time -v klayout -zz -r $ROOT/codeachip/scripts/render_gds.py -rd gds=$B/6_final.gds \
    -rd png=$STAGE/fullchip_layout.png -rd px=2400 2>&1 | grep -E "Maximum resident|Elapsed|rror" | tee -a $LOG
  say "stage done: $(ls $STAGE | tr '\n' ' ')" ;;
sram)
  O=/root/sram_access_revc; mkdir -p $O
  (cd $SRC && iverilog -g2012 -I rtl/kyber $DEFS -s tb_trustedge_spi -s sram_access_counter -o $O/tb.vvp \
     $F $CAC/tb/sram_access_counter_v2.sv) > $O/compile.log 2>&1 || { say "sram compile failed"; tail -20 $O/compile.log; continue; }
  (cd $CAC/results/system_sim && vvp -n $O/tb.vvp +skip=1 > $O/sim.log 2>&1) || true
  say "sram sim: $(grep -E 'TB_TRUSTEDGE_SPI_RESULT|U1 Decaps busy' $O/sim.log | tr '\n' ' ' | cut -c1-300)"
  python3 $CAC/scripts/collect_sram_accesses.py $O/sim.log $STAGE/sram_accesses.json
  python3 $CAC/scripts/sram_energy_model.py $ROOT/codeachip/results/fullchip/sram_macro_spice.json $STAGE/sram_accesses.json \
    $STAGE/sram_energy.json | tail -3 | tee -a $LOG ;;
hold)
  O=/root/t3/macro_hold_revc; mkdir -p $O
  for c in ss:ss_100C_1v60 tt:tt_025C_1v80 ff:ff_n40C_1v95; do
    k=${c%%:*}; RUN=$B CORNER=${c#*:} MACRO_LIB_DIR=$V/$k IO_MODE=soc MACRO_HOLD=1 $OR -no_splash -exit \
      $CAC/flow_chip/final_sta.tcl > $O/sta_$k.log 2>&1
    say "hold $k $(grep -E 'RESULT (hold_wns|setup_wns|macro_input_pins)' $O/sta_$k.log | tr '\n' ' ')"
  done ;;
fmax)
  O=/root/t3/fmax_revc; mkdir -p $O
  for r in "ss ss_100C_1v60 ss 0" "tt tt_025C_1v80 tt 0" "ff ff_n40C_1v95 ff 0" "ss_derate5 ss_100C_1v60 ss 0.05"; do
    set -- $r
    RUN=$B CORNER=$2 MACRO_LIB_DIR=$V/$3 IO_MODE=soc DERATE=$4 FMAX_SEARCH=1 $OR -no_splash -exit \
      $CAC/flow_chip/final_sta.tcl > $O/$1.log 2>&1
    say "fmax $1 $(grep 'RESULT fmax_search' $O/$1.log)"
  done ;;
acvp)
  W=/root/acvp_encdec_revc; rm -rf $W; mkdir -p $W/run; cp -r $SRC $W/src
  python3 $CAC/flow_chip/acvp_encdec_t3e.py prepare $W/run 25 || { say "acvp prepare failed"; continue; }
  # the testbench patch of acvp_encdec_t3e.sh (its embedded Python, unchanged)
  sed -n "/^python3 - \"\$W\/src\/sim\/tb\/tb_trustedge_spi.sv\"/,/^PY$/p" $CAC/flow_chip/acvp_encdec_t3e.sh > $W/patch.sh
  W=$W N=25 bash $W/patch.sh
  (cd $W/src && iverilog -g2012 -I rtl/kyber $DEFS -DCAC_ACVP_ENCDEC -s tb_trustedge_spi -o $W/tb.vvp $F) > $W/compile.log 2>&1 \
    || { say "acvp compile failed"; grep -m5 -i error $W/compile.log; continue; }
  (cd $W/run && vvp -n $W/tb.vvp > $W/sim.log 2>&1)
  python3 $CAC/flow_chip/acvp_encdec_t3e.py check $W/run $W/sim.log 25 | tail -3 | tee -a $LOG
  say "acvp done: $W/run/acvp_encdec_t3e.json" ;;
iru)
  O=/root/t3/ir_revc_edge; mkdir -p $O
  RUN=$B MACRO_LIB_DIR=/root/t3/ir_w1_spice/views_nopower OUT=$O CHIPV2_MACRO_POWER=/root/t3/ir_w1_spice/macro_power.tcl \
    CHIPV2_VSRC_DIR=/root/t3/ir_w1_edge $OR -no_splash -exit $CAC/flow_chip/ir_drop.tcl > $O/ir.log 2>&1
  say "iru rc=$? $(grep -E 'Worstcase IR drop|Total power' $O/ir.log | tr '\n' ' ')" ;;
*) say "unknown step $s" ;;
esac; done
say "end"
