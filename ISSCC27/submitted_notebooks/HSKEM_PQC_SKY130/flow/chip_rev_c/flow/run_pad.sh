#!/usr/bin/env bash
# Chip v2 routability rebuild: the 40 ns flow from synthesis to CTS, then the old chip's global-route recipe
# (grt_a3recipe.sh, which now ends with antenna jumpers, post_grt_jumpers.tcl). Two placement changes:
#  * I/O pins: no pin on an edge segment that a macro covers (PLACE_PINS_ARGS -exclude, 20 um margin).
#    The first build put 203 of 411 pins behind macros, 120 of them behind the ekPKE macro, whose corner
#    became the detailed-route hotspot (x 600-800, y 1400-1800 um).
#  * cell padding: 2 sites on each side in global placement, 1 in detailed placement (CTS and global
#    route keep the latter), room for pin access and for the antenna diodes.
# usage: run_pad.sh [tag]   (work homes report/orfs_chip_v2_<tag> and report/orfs_chip_v2_<tag>_a3grt;
#                            log chip_v2/<tag>_flow.log; default tag r2)
set -uo pipefail
readonly TAG="${1:-r2}"
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test
readonly WH="${T3_WORK:-/root/t3}/${TAG}" WG="${T3_WORK:-/root/t3}/${TAG}_a3grt"
readonly D=sky130hd/trustedge_asic_core/chipv2 LOG="${T3_WORK:-/root/t3}/${TAG}_flow.log"
[[ ! -e "${WH}" && ! -e "${WG}" ]] || { echo "PAD_INPUT_GATE=FAIL"; exit 2; }
export CELL_PAD_IN_SITES_GLOBAL_PLACEMENT=2 CELL_PAD_IN_SITES_DETAIL_PLACEMENT=1
# macro-covered edge segments (um) from chip_v2/io_blocked.tcl on the first build, widened by 20 um
export PLACE_PINS_ARGS="-exclude left:0-400 -exclude left:440-706 -exclude left:746-1428 -exclude left:1468-1734 \
-exclude left:2190-2444 -exclude left:2484-2738 -exclude left:2777-3031 -exclude right:22-1455 \
-exclude bottom:0-376 -exclude bottom:416-771 -exclude bottom:2417-2854 -exclude bottom:2900-3351 \
-exclude top:575-1977"
{
    echo "PAD_FLOW_START $(date -Is) tag=${TAG} pad_gpl=2 pad_dpl=1 pins_excluded=13_segments"
    rc=0
    CHIPV2_WORK_HOME="${WH}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl" \
        bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" "${WH}/results/${D}/4_cts.odb" || rc=$?
    echo "PAD_CTS_DONE rc=${rc} $(date -Is)"
    if [[ ${rc} -eq 0 ]]; then
        bash "${ROOT}/codeachip_t3/flow_chip/grt_a3recipe.sh" "${WH}" "${WG}" || rc=$?
        echo "PAD_GRT_DONE rc=${rc} $(date -Is)"
    fi
    echo "PAD_FLOW_END rc=${rc}"
} 2>&1 | tee -a "${LOG}"
