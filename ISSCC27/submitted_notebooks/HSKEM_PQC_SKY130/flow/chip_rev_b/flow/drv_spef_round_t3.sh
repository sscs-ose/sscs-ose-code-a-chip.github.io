#!/usr/bin/env bash
# (tier-3 clone copy of chip_v2/drv_spef_round.sh: the clone's run_chip_v2.sh, macro file, RTL root and the DRT-1231-patched OpenROAD)
# One post-route DRV round of chip v2 with the extracted parasitics (drv_spef_round.tcl), as its own
# session: CHIPV2_SPEF is the SPEF of the final stage run on the input database; the resizer repairs the
# slew and capacitance violations it shows, then legalization, incremental global route and a detailed
# route from the existing routes (CHIPV2_DRT_END_ITER, default 20). Reads results/.../<input odb>,
# writes results/.../5_2_route_<tag>.odb. (drv_round.sh handles the SRAM address drivers.)
# (CHIPV2_DRV_TCL=chip_v2/drv_resize_round.tcl: resize-only round, no new nets)
# usage: CHIPV2_SPEF=<spef> drv_spef_round_t3.sh <work home> <tag, e.g. d2> <input odb name>
set -uo pipefail
readonly WH="${1:?work home}" TAG="${2:?tag}" IN="${3:?input odb name}"
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test
readonly RES="${WH}/results/sky130hd/trustedge_asic_core/chipv2"
if [[ ! -f "${RES}/${IN}" || -e "${RES}/5_2_route_${TAG}.odb" ]]; then echo "DRV_ROUND_INPUT_GATE=FAIL"; exit 2; fi
{
    sha256sum "${RES}/${IN}"
    export CHIPV2_IN="${IN}" CHIPV2_OUT="5_2_route_${TAG}.odb" CHIPV2_TAG="${TAG}"
    export CHIPV2_SRAM_DRV_CELL="${CHIPV2_SRAM_DRV_CELL:-sky130_fd_sc_hd__buf_12}"
    export DETAILED_ROUTE_END_ITERATION="${CHIPV2_DRT_END_ITER:-20}"
    export CELL_PAD_IN_SITES_DETAIL_PLACEMENT=1
    export RUN_SCRIPT="${CHIPV2_DRV_TCL:-${ROOT}/chip_v2/drv_spef_round.tcl}" RUN_LOG_NAME_STEM="5_2_route_${TAG}"
    export CHIPV2_WORK_HOME="${WH}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl"
    export OPENROAD_EXE="${OPENROAD_EXE:-/opt/eda/openroad-t3patch/bin/openroad}"   # reloads a routed odb: DRT-1231 patch
    echo "DRT_INPUT_GATE=PASS session=${TAG} mode=drv_spef spef=${CHIPV2_SPEF:?CHIPV2_SPEF} in=${IN} cell=${CHIPV2_SRAM_DRV_CELL} end_iter=${DETAILED_ROUTE_END_ITERATION} start=$(date -Is)"
    rc=0
    T3_ROOT="${T3_ROOT:-${ROOT}/codeachip_t3/build_t3e/root}" bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" run || rc=$?
    [[ ${rc} -eq 0 && -f "${RES}/5_2_route_${TAG}.odb" ]] && sha256sum "${RES}/5_2_route_${TAG}.odb"
    echo "DRT_DONE session=${TAG} rc=${rc} end=$(date -Is)"
} 2>&1 | tee -a "${WH}/drt_console.log"
