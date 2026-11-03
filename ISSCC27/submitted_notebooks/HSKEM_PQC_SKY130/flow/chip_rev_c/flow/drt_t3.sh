#!/usr/bin/env bash
# (tier-3 clone copy of chip_v2/drt_chipv2.sh: the clone's run_chip_v2.sh, config and RTL root)
# Session 1 of the split detailed route of a chip v2 global-route checkpoint: the main detailed route only
# (ORFS stage 5_2 with the post-route antenna repair switched off), capped at CHIPV2_DRT_END_ITER
# iterations (default 30; the old chip's main route converged at iteration 15). It writes
# results/.../5_2_route.odb, the checkpoint from which drt_round.sh runs the antenna rounds, one session
# each. The log goes to <work home>/drt_console.log as well as to the terminal.
# usage: drt_t3.sh <work home that holds results/.../5_1_grt.odb>
set -uo pipefail
readonly WH="${1:?work home}"
readonly ROOT="/mnt/d/TKVM_ATTT_2026_test"
readonly D="sky130hd/trustedge_asic_core/chipv2"
if [[ ! -f "${WH}/results/${D}/5_1_grt.odb" || -e "${WH}/results/${D}/5_2_route.odb" ]]; then
    echo "DRT_INPUT_GATE=FAIL"; exit 2
fi
{
    sha256sum "${WH}/results/${D}/5_1_grt.odb" "${WH}/results/${D}/5_1_grt.sdc"
    export SKIP_DETAILED_ROUTE=0 SKIP_ANTENNA_REPAIR_POST_DRT="${CHIPV2_SKIP_ANT_POST:-1}"
    # CHIPV2_SKIP_ANT_POST=0 + MAX_REPAIR_ANTENNAS_ITER_DRT=N: the ORFS antenna loop in the same session (the resumed
    # rounds of drt_round_t3.sh fail on t3e: DRT-1231, a pin without access point after reloading the routed odb)
    [[ -n "${MAX_REPAIR_ANTENNAS_ITER_DRT:-}" ]] && export MAX_REPAIR_ANTENNAS_ITER_DRT
    export DETAILED_ROUTE_END_ITERATION="${CHIPV2_DRT_END_ITER:-30}"
    unset DETAILED_ROUTE_ARGS || true
    export CHIPV2_WORK_HOME="${WH}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl"
    echo "DRT_INPUT_GATE=PASS session=main end_iter=${DETAILED_ROUTE_END_ITERATION} wh=${WH} start=$(date -Is)"
    rc=0
    T3_ROOT="${T3_ROOT:-${ROOT}/codeachip_t3/build_t3e/root}" bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" do-5_2_route || rc=$?
    [[ ${rc} -eq 0 ]] && sha256sum "${WH}/results/${D}/5_2_route.odb"
    echo "DRT_DONE session=main rc=${rc} end=$(date -Is)"
} 2>&1 | tee -a "${WH}/drt_console.log"
