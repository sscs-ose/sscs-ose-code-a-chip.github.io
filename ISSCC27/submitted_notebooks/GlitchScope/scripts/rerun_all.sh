#!/bin/bash
# Re-run every model-dependent study after a change of the glitch model, in two parallel lanes.
# Cached SPICE references, GLOW's own runs and the SPICE calibration sweeps are reused.  Lane 1 starts with the
# GlitchFix studies because the layouts, corners and mismatch studies use their placements.
#
#   bash scripts/rerun_all.sh [lane1|lane2]        (no argument: both lanes in the background)
#   logs: rerun_logs/<step>.log, progress: rerun_logs/progress.txt
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd); cd "$ROOT"
[ -f tools.env ] && set -a && . ./tools.env && set +a
L=$ROOT/rerun_logs; mkdir -p "$L"
PY=python3
PEX=data/pdk/pex/sky130_fd_sc_hd_pex.spice
step() {  # step <name> <command...>
  local n=$1; shift
  echo "$(date +%H:%M) start $n" >> "$L/progress.txt"
  if "$@" > "$L/$n.log" 2>&1; then echo "$(date +%H:%M) done  $n" >> "$L/progress.txt"
  else echo "$(date +%H:%M) FAIL  $n" >> "$L/progress.txt"; fi
}

lane1() {
  # section 5: whole-circuit validation (cached SPICE references; schematic and SPICE-characterised library)
  for b in rca8:60 ks8:40 mul4:40; do
    step val_${b%%:*} $PY scripts/validate_vs_spice.py "$GS_LIB" ${b%%:*} ${b##*:}
    step valc_${b%%:*} $PY scripts/validate_vs_spice.py bench/basic_cells_spice.lib ${b%%:*} ${b##*:}
  done
  for b in c432 c880; do
    step val_$b $PY scripts/validate_vs_spice.py "$GS_LIB" bench/external/netlists/$b.v 30 6000
    step valc_$b $PY scripts/validate_vs_spice.py bench/basic_cells_spice.lib bench/external/netlists/$b.v 30 6000
  done
  step val_arraymul8 $PY scripts/validate_vs_spice.py "$GS_LIB" arraymul8 20 7000
  step valc_arraymul8 $PY scripts/validate_vs_spice.py bench/basic_cells_spice.lib arraymul8 20 7000
  step val_mac $PY scripts/validate_design_vs_spice.py "$GS_LIB" bench/netlists/mac.v bench/sim/mac.vcd 15
  # attribution, what-ifs, sampling, notebook data, reports
  step skew $PY scripts/skew_study.py "$GS_LIB" mul4 rca8
  step naive $PY scripts/naive_compare.py "$GS_LIB" 300
  step attr_shift $PY scripts/attribution_shift.py "$GS_LIB" 300
  step cf_rca8 $PY scripts/counterfactual.py "$GS_LIB" rca8 300
  step cf_mul4 $PY scripts/counterfactual.py "$GS_LIB" mul4 300
  step fix_mul4 $PY scripts/fix_study.py "$GS_LIB" mul4
  step sampling $PY scripts/sampling_study.py "$GS_LIB"
  step nbdata $PY scripts/make_notebook_data.py
  step mac_flow $PY -m glitchscope.flow --netlist bench/netlists/mac.v --vcd bench/sim/mac.vcd --lib "$GS_LIB" \
       --groups level:8 --out data/notebook/mac_flow
  step saif_check bash scripts/opensta_saif_check.sh
  step native_eq $PY scripts/check_native_equivalence.py "$GS_LIB"
  step native_speed $PY scripts/native_speed.py "$GS_LIB"
  # sections 10, 11, 13: automatic fix, layouts, corners, mismatch
  step glitchfix $PY scripts/glitchfix_study.py "$GS_LIB"
  cp data/glitchfix/mul16_r/best_cuts.v bench/layout/mul16_r_ga.v
  cp data/glitchfix/mul16_r/best_milp.v bench/layout/mul16_r_milp.v
  cp data/glitchfix/mul16_r/timing_driven.v bench/layout/mul16_r_td.v
  cp data/glitchfix/dot4_plain/optimized.v bench/layout/dot4_i8_pe_plain_ga.v
  cp data/glitchfix/dot4_booth/optimized.v bench/layout/dot4_i8_pe_booth_ga.v
  for v in v0 v1 v2 r_td r_ga r_milp; do step layout_$v bash scripts/layout_flow.sh $v; done
  for v in pe_plain_v0 pe_plain_ga pe_booth_v0 pe_booth_ga; do
    step layout_$v env DESIGN=dot4_i8 PERIOD_PS=7500 bash scripts/layout_flow.sh $v
  done
  step layout_summary $PY scripts/layout_summary.py --pre
  step pe_summary $PY scripts/pe_layout_summary.py
  step pvt $PY scripts/pvt_study.py "$GS_PDK_ROOT/libs.ref/sky130_fd_sc_hd/lib"
  step pvt_cal $PY scripts/pvt_study.py "$GS_PDK_ROOT/libs.ref/sky130_fd_sc_hd/lib" --compare-calibration ss_n40C_1v28
  step mismatch $PY scripts/mismatch_study.py "$GS_LIB" 30
  # sections 9, 14
  rm -f data/bench/arraymul16_study.json data/pdk/trend.json        # both scripts resume from their caches
  step arraymul16 $PY scripts/arraymul_study.py "$GS_LIB" 24
  step arraymul16_report $PY -m glitchscope.flow --netlist bench/netlists/arraymul16.v --random-vectors 24 --seed 7 \
       --lib "$GS_LIB" --groups 'regex:^(pp|r\d\d|rf)' --max-screen 12 --fixes 2 --perms 4 \
       --out data/notebook/arraymul16_report
  step pdk_study $PY scripts/pdk_study.py "$GS_LIBDIR" 24 16
  step overcount $PY scripts/overcount_diagnosis.py "$GS_LIB"
  for x in "bench/layout/mul16_v0.v data/glitchfix/mul16_r/best_cuts.v 0" "bench/layout/mul16_v0.v data/glitchfix/mul16_r/best_milp.v 0" \
           "bench/layout/mul16_v0.v data/glitchfix/mul16_p/optimized.v 1" "bench/netlists/mul8_v0.v data/glitchfix/mul8_r/optimized.v 0" \
           "bench/netlists/dot4_plain.v data/glitchfix/dot4_plain/optimized.v 0" "bench/netlists/dot4_booth.v data/glitchfix/dot4_booth/optimized.v 0"; do
    set -- $x; $PY scripts/iverilog_equivalence.py "$GS_LIB" $1 $2 $3 2000
  done > "$L/iverilog.log" 2>&1; grep -E "RESULT|PASS|FAIL" "$L/iverilog.log" > data/glitchfix/iverilog_check.txt
  echo "$(date +%H:%M) LANE1_DONE" >> "$L/progress.txt"
}

lane2() {
  # 8x8 transistor-level confirmation: GlitchScope side for the unchanged designs, SPICE for the new placement
  # whole-circuit validation against the extracted-cell references (cached; SPICE runs only if missing)
  for b in rca8:60 ks8:40 mul4:40; do
    step valpex_${b%%:*} env GS_CELL_SPICE=$PEX $PY scripts/validate_vs_spice.py "$GS_LIB" ${b%%:*} ${b##*:}
    step valcpex_${b%%:*} env GS_CELL_SPICE=$PEX $PY scripts/validate_vs_spice.py bench/basic_cells_spice.lib ${b%%:*} ${b##*:}
  done
  for b in c432 c880; do
    step valpex_$b env GS_CELL_SPICE=$PEX $PY scripts/validate_vs_spice.py "$GS_LIB" bench/external/netlists/$b.v 30 6000
    step valcpex_$b env GS_CELL_SPICE=$PEX $PY scripts/validate_vs_spice.py bench/basic_cells_spice.lib bench/external/netlists/$b.v 30 6000
  done
  step valpex_arraymul8 env GS_CELL_SPICE=$PEX GS_SPICE_CHUNK=1 $PY scripts/validate_vs_spice.py "$GS_LIB" arraymul8 20 7000
  step valcpex_arraymul8 env GS_CELL_SPICE=$PEX $PY scripts/validate_vs_spice.py bench/basic_cells_spice.lib arraymul8 20 7000
  step valpex_mac env GS_CELL_SPICE=$PEX $PY scripts/validate_design_vs_spice.py "$GS_LIB" bench/netlists/mac.v bench/sim/mac.vcd 15
  step trail_eval $PY scripts/trail_slew_eval.py "$GS_LIB" 0 model --pex
  # 8x8 transistor-level confirmation (schematic cells, one long run each; the extracted-cell runs are
  # scripts/spice_confirm_parallel.py, see scripts/server_spice_kit.sh)
  until grep -qE "(done|FAIL)  glitchfix$" "$L/progress.txt"; do sleep 60; done     # needs lane 1's new placements
  step spice_mul8 $PY scripts/spice_confirm_fix.py "$GS_LIB" mul8_r 16
  # section 12: standard suites, register placement, GLOW re-measurement
  step suite $PY scripts/benchmark_suite.py "$GS_LIB" --cycles 30 --max-cells 20000
  step retime_itc $PY scripts/retiming_benchmarks.py "$GS_LIB" b03 b04 b08 b11 b14 b20 b21 b22
  step retime_arith $PY scripts/retiming_benchmarks.py "$GS_LIB" --factor 0 mul16_v0 c6288_r c5315_r c7552_r c3540_r \
       adder_r max_r bar_r sin_r
  step retime_arith11 $PY scripts/retiming_benchmarks.py "$GS_LIB" mul16_v0 c6288_r c5315_r c7552_r c3540_r \
       adder_r max_r bar_r sin_r
  for c in b03 b04 b08 b11 b14; do step glow_$c $PY scripts/glow_compare.py import "$GS_LIB" $c --factor 1.1; done
  for c in c6288_r mul16_v0 sin_r; do step glow_$c $PY scripts/glow_compare.py import "$GS_LIB" $c --factor 0; done
  echo "$(date +%H:%M) LANE2_DONE" >> "$L/progress.txt"
}

case "${1:-}" in
  lane1) lane1 ;;
  lane2) lane2 ;;
  *) nohup bash "$0" lane1 > "$L/lane1.out" 2>&1 &
     nohup bash "$0" lane2 > "$L/lane2.out" 2>&1 &
     echo "started both lanes; progress: $L/progress.txt" ;;
esac
