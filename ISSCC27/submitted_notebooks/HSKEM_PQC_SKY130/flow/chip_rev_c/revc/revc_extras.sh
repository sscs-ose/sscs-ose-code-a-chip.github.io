#!/usr/bin/env bash
# Rev C sign-off extras, the set of rev B's notebook (Appendix C.2), one job after another after the Magic DRC (19 GB):
#   magic  classify the Magic markers (classify_magic_drc.py): inside the OpenRAM macros or not, cell under each one
#   drv    slew / capacitance violators at tt with the SPEF (drv_list.tcl)
#   gls    gate-level run of the final netlist over the decapsulation window next to the RTL (real_gls_window.sh) on the
#          rev C RTL (hskem_revc/revc/root, + TRUSTEDGE_REVC; the GLS-only kyber_pkg::kyber_zeta qualification of rev B),
#          starting from rev B's shadow skip list (the generator adds unresolved references itself)
#   power  logic power over a decapsulation from the shadow VCD (power_revc.sh)
#   ir     static IR drop with that activity, SPICE macro power and edge sources (rev B's ir_w1_spice / ir_w1_edge inputs:
#          same floorplan and power grid)
# log: /root/t3/revc_extras.log
set -u
ROOT=/mnt/d/TKVM_ATTT_2026_test; S=$ROOT/codeachip/flow/chip_rev_b; T3=$ROOT/codeachip_t3; H=$ROOT/hskem_revc/flow
B=/root/t3/revc_final_ga1/results; LOG=/root/t3/revc_extras.log; MG=/root/magic_drc_revc
OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad
M=$ROOT/report/a2_macro_link_smoke/run.rjfysF/derived_liberty
say() { echo "$(date +%m-%d_%H:%M) $*" | tee -a $LOG; }
# --- magic -----------------------------------------------------------------------------------------------------------
while pgrep -f "magic -dnull" > /dev/null; do sleep 120; done
say "magic: $(grep -E 'MAGIC_DRC total|Elapsed|Maximum resident' $MG/magic.log | tr '\n' ' ')"
# macro sizes from the derived LEFs of all seven SRAM types (codeachip/flow/macros, the default, holds two of them)
python3 $S/signoff/classify_magic_drc.py $MG/drc_boxes.txt $B/6_final.def $MG/magic_drc.json \
  $ROOT/report/a2_macro_link_smoke/run.rjfysF/derived_lef > $MG/classify.log 2>&1
say "magic classified: $(python3 -c "import json; d=json.load(open('$MG/magic_drc.json')); print('inside macros', d['inside_openram_macros'], 'outside', d['outside_macros'], d.get('outside_by_rule_and_cell'))")"
# --- drv -------------------------------------------------------------------------------------------------------------
RUN=$B MACRO_LIB_DIR=$M OUT=/root/t3/drv_revc.txt $OR -no_splash -exit $S/analysis/drv_list.tcl > /root/t3/drv_revc.log 2>&1
say "drv: $(grep -c VIOLATED /root/t3/drv_revc.txt) violating pins, $(grep VIOLATED /root/t3/drv_revc.txt | grep -c '_macro/') at SRAM pins"
# --- gls -------------------------------------------------------------------------------------------------------------
W=/root/real_gls_revc; mkdir -p $W
if [ ! -d $W/hskem_rtl ]; then
  cp -r $ROOT/hskem_revc/revc/root $W/hskem_rtl
  for f in rtl/mlkem512/mlkem512_kpke_encrypt_selftest.sv rtl/mlkem512/mlkem512_matrix_mac_selftest.sv rtl/mlkem512/mlkem512_partial_kem_selftests.sv; do
    perl -pi -e 's/(?<!::)\bkyber_zeta\(/kyber_pkg::kyber_zeta(/g' $W/hskem_rtl/$f
  done
  echo "GLS-only source edit (as rev B, 17/10): kyber_zeta( -> kyber_pkg::kyber_zeta( in 3 files (iverilog did not resolve the wildcard import)" > $W/SOURCE_EDITS.txt
fi
D=""; for d in MAC_DEEP MM_PIPE CRC_SERIAL BARRETT_1C SA_PIPE PMAC_RAW CODEC_RETIME MSG_PIPE PP_EARLY LOAD_PIPE MARGIN MUL_SEL SEL_REP EK_PREF; do D="$D -DTRUSTEDGE_T3_$d"; done
D="$D -DTRUSTEDGE_REVC"
say "gls start"
FULLCHIP_DIR=$B REAL_GLS_WORK=$W T3_GLS_DEFS="$D" SHADOW_SKIP=/root/real_gls_t3e/shadow_skip.txt bash $T3/scripts/real_gls_window.sh > $W/run.out 2>&1
say "gls rc=$? $(grep -h -E 'REAL_CHIP end|DECAPS|compile failed|Elapsed' $W/run.out | tail -4 | tr '\n' ' ' | cut -c1-500)"
# --- power -----------------------------------------------------------------------------------------------------------
bash $H/power_revc.sh run > /root/t3/power_revc.out 2>&1
say "power rc=$? $(grep -E '"logic_power_mw"|"logic_energy_per_decaps_uj"|POWER_COMPILE|window_cycles' /root/t3/power_revc.out | tr '\n' ' ' | cut -c1-400)"
# --- ir --------------------------------------------------------------------------------------------------------------
O=/root/t3/ir_revc_vcd; mkdir -p $O
RUN=$B MACRO_LIB_DIR=/root/t3/ir_w1_spice/views_nopower OUT=$O CHIPV2_VCD=/mnt/c/chipv2_signoff/power_revc/shadow0.vcd \
CHIPV2_MACRO_POWER=/root/t3/ir_w1_spice/macro_power.tcl CHIPV2_VSRC_DIR=/root/t3/ir_w1_edge \
  $OR -no_splash -exit $T3/flow_chip/ir_drop.tcl > $O/ir.log 2>&1
say "ir rc=$? $(grep -E 'CHIPV2_IR|IR drop|^Total' $O/ir.log | tr '\n' ' ' | cut -c1-500)"
say "revc extras end"
