#!/usr/bin/env bash
# Rev C rebuild (revc2): one timing-repair session on a global-route database (grt_eco_revc.tcl), through make run with
# hskem_revc/flow/revc_run_chip.sh (LIB_FILES and CHIPV2_MACRO_LIB_DIR pick the corner). Reads results/.../<input odb>,
# writes results/.../5_1_grt_<tag>.odb (not in report mode). Pattern of revc_drv_round.sh, without the detailed route.
# usage: CHIPV2_GRT_MODE=setup|hold|report CHIPV2_DERATE=0.05 CHIPV2_MARGIN=0.3 revc_grt_eco.sh <work home> <tag> <input odb>
set -uo pipefail
readonly WH="${1:?work home}" TAG="${2:?tag}" IN="${3:?input odb name}"
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test
readonly RES="${WH}/results/sky130hd/trustedge_asic_core/chipv2"
if [[ ! -f "${RES}/${IN}" || -e "${RES}/5_1_grt_${TAG}.odb" ]]; then echo "GRT_ECO_INPUT_GATE=FAIL"; exit 2; fi
{
    sha256sum "${RES}/${IN}"
    export CHIPV2_IN="${IN}" CHIPV2_OUT="5_1_grt_${TAG}.odb" CHIPV2_TAG="${TAG}"
    export CHIPV2_GRT_MODE="${CHIPV2_GRT_MODE:?mode}" CHIPV2_DERATE="${CHIPV2_DERATE:?derate}" CHIPV2_MARGIN="${CHIPV2_MARGIN:-0}"
    export CELL_PAD_IN_SITES_DETAIL_PLACEMENT=1
    export RUN_SCRIPT="${ROOT}/hskem_revc/flow/grt_eco_revc.tcl" RUN_LOG_NAME_STEM="5_1_grt_${TAG}"
    export CHIPV2_WORK_HOME="${WH}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl"
    export OPENROAD_EXE="${OPENROAD_EXE:-/opt/eda/openroad-t3patch/bin/openroad}"
    echo "GRT_ECO_INPUT_GATE=PASS session=${TAG} mode=${CHIPV2_GRT_MODE} lib=$(basename "${LIB_FILES:-typical}") macro_libs=${CHIPV2_MACRO_LIB_DIR:-typical} derate=${CHIPV2_DERATE} margin=${CHIPV2_MARGIN} in=${IN} start=$(date -Is)"
    rc=0
    T3_ROOT="${T3_ROOT:?T3_ROOT}" bash "${ROOT}/hskem_revc/flow/revc_run_chip.sh" run || rc=$?
    [[ ${rc} -eq 0 && -f "${RES}/5_1_grt_${TAG}.odb" ]] && sha256sum "${RES}/5_1_grt_${TAG}.odb"
    echo "GRT_ECO_DONE session=${TAG} rc=${rc} end=$(date -Is)"
} 2>&1 | tee -a "${WH}/grt_eco_console.log"
