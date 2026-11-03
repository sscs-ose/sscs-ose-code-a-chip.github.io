#!/usr/bin/env bash
# (tier-3 clone copy of chip_v2/drt_round.sh: the clone's run_chip_v2.sh and RTL root; same drt_round.tcl)
# One round of the split detailed route of chip v2 (drt_round.tcl), as its own session: an antenna round
# (diodes, then detailed route from the existing routes) or a DRC clean-up round, capped at
# CHIPV2_DRT_END_ITER iterations (default 30). It reads results/.../<input odb> and writes
# results/.../5_2_route_<tag>.odb; an interrupted round is simply rerun from the same input.
# usage: drt_round_t3.sh <work home> <tag, e.g. r1> <input odb name, e.g. 5_2_route.odb> [antenna|drc]
set -uo pipefail
readonly WH="${1:?work home}" TAG="${2:?tag}" IN="${3:?input odb name}" MODE="${4:-antenna}"
readonly ROOT="/mnt/d/TKVM_ATTT_2026_test"
readonly RES="${WH}/results/sky130hd/trustedge_asic_core/chipv2"
if [[ ! -f "${RES}/${IN}" || -e "${RES}/5_2_route_${TAG}.odb" || ! "${MODE}" =~ ^(antenna|drc)$ ]]; then
    echo "DRT_ROUND_INPUT_GATE=FAIL"; exit 2
fi
{
    sha256sum "${RES}/${IN}"
    export CHIPV2_IN="${IN}" CHIPV2_OUT="5_2_route_${TAG}.odb" CHIPV2_TAG="${TAG}" CHIPV2_MODE="${MODE}"
    export DETAILED_ROUTE_END_ITERATION="${CHIPV2_DRT_END_ITER:-30}"
    export RUN_SCRIPT="${CHIPV2_TCL:-${ROOT}/codeachip_t3/flow_chip/drt_round_t3.tcl}" RUN_LOG_NAME_STEM="5_2_route_${TAG}"
    export CHIPV2_WORK_HOME="${WH}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl"
    echo "DRT_INPUT_GATE=PASS session=${TAG} mode=${MODE} in=${IN} end_iter=${DETAILED_ROUTE_END_ITERATION} start=$(date -Is)"
    rc=0
    T3_ROOT="${T3_ROOT:-${ROOT}/codeachip_t3/build_t3e/root}" bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" run || rc=$?
    [[ ${rc} -eq 0 && -f "${RES}/5_2_route_${TAG}.odb" ]] && sha256sum "${RES}/5_2_route_${TAG}.odb"
    echo "DRT_DONE session=${TAG} rc=${rc} end=$(date -Is)"
} 2>&1 | tee -a "${WH}/drt_console.log"
