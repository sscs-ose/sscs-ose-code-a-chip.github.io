#!/usr/bin/env bash
# Rev C copy of codeachip_t3/flow_chip/run_chip_v2.sh: CHIPV2_MACRO_LIB_DIR replaces the macro Liberty folder (the ECO
# rounds read the SPICE-swept corner views of final_sta_t3.sh instead of the typical-corner views).
set -euo pipefail
readonly TARGET="${1:-synth}"
readonly ROOT="/mnt/d/TKVM_ATTT_2026_test"
readonly ORFS_ROOT="/opt/eda/orfs-6101364b"
readonly WORK_HOME="${CHIPV2_WORK_HOME:-/root/t3/default}"
readonly LEF_DIR="${ROOT}/report/a2_macro_link_smoke/run.rjfysF/derived_lef"
readonly LIB_DIR="${CHIPV2_MACRO_LIB_DIR:-${ROOT}/report/a2_macro_link_smoke/run.rjfysF/derived_liberty}"
mapfile -t macro_lefs < <(find "${LEF_DIR}" -maxdepth 1 -type f -name '*.lef' -print | sort)
mapfile -t macro_libs < <(find "${LIB_DIR}" -maxdepth 1 -type f -name '*.physical.lib' -print | sort)
[[ "${#macro_lefs[@]}" -eq 8 && "${#macro_libs[@]}" -eq 8 ]] || { echo "CHIPV2_INPUT_GATE=FAIL"; exit 2; }
export M5_MACRO_LEFS="${macro_lefs[*]}"
export M5_MACRO_LIBS="${macro_libs[*]}"
export DIE_AREA="0 0 3351.335 3351.335"
export CORE_AREA="1.380 2.720 3350.180 3348.320"
[[ -n "${CHIPV2_MACRO_TCL:-}" ]] && export MACRO_PLACEMENT_TCL="${CHIPV2_MACRO_TCL}"
echo "CHIPV2_INPUT_GATE=PASS target=${TARGET}"
export T3_DEFINES_EXTRA="${T3_DEFINES_EXTRA:-}"
exec make -C "${ORFS_ROOT}/flow" TRUSTEDGE_ROOT="${T3_ROOT:-/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/build_pub_t3/root}" DESIGN_CONFIG="${ROOT}/codeachip_t3/flow_chip/config.mk" WORK_HOME="${WORK_HOME}" \
    FLOW_VARIANT=chipv2 CORE_UTILIZATION= "${TARGET}"
