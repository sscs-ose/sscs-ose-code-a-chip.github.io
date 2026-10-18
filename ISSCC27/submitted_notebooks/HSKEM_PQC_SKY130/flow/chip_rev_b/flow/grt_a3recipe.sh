#!/usr/bin/env bash
# Re-run only the global route of a chip v2 run with the recipe of the old chip's accepted global route
# (asic/run_a3_p82.sh, stage grt): incremental repair with 10 % slew and capacitance margins, no power
# recovery, the 0.13 layer-adjustment hook, and no antenna repair before the detailed route (the detailed
# route repairs antennas, as it did for the old chip).
# usage: grt_a3recipe.sh <source work home> <new work home>
set -euo pipefail
readonly SRC="${1:?source work home}"
readonly DST="${2:?new work home}"
readonly ROOT="/mnt/d/TKVM_ATTT_2026_test"
readonly D="sky130hd/trustedge_asic_core/chipv2"
[[ -f "${SRC}/results/${D}/4_cts.odb" && ! -e "${DST}" ]] || { echo "GRT_A3_INPUT_GATE=FAIL"; exit 2; }
mkdir -p "${DST}/results/${D}" "${DST}/logs/${D}" "${DST}/reports/${D}" "${DST}/objects/${D}"
cp "${SRC}/results/${D}/4_cts.odb" "${SRC}/results/${D}/4_cts.sdc" "${DST}/results/${D}/"
cp -r "${SRC}/objects/${D}/." "${DST}/objects/${D}/"
export SKIP_INCREMENTAL_REPAIR=0 SKIP_ANTENNA_REPAIR=1 DETAILED_METRICS=1 RECOVER_POWER=0
export SLEW_MARGIN=10 CAP_MARGIN=10 ENABLE_RESISTANCE_AWARE=0
# layer adjustment hook: the old chip's fixed 0.13 unless CHIPV2_PRE_GRT_TCL selects another (pre_grt_adj.tcl)
export PRE_GLOBAL_ROUTE_TCL="${CHIPV2_PRE_GRT_TCL:-${ROOT}/asic/orfs/pre_global_route_a3_013.tcl}"
# antenna jumpers right after the global route (no cells; see post_grt_jumpers.tcl)
export POST_GLOBAL_ROUTE_TCL="${CHIPV2_POST_GRT_TCL:-${ROOT}/codeachip_t3/flow_chip/post_grt_jumpers.tcl}"
export CHIPV2_WORK_HOME="${DST}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl"
echo "GRT_A3_INPUT_GATE=PASS src=${SRC} dst=${DST}"
exec bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" do-grt
