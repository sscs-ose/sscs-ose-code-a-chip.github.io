#!/usr/bin/env bash
# (tier-3 clone copy of chip_v2/final_chipv2.sh: the clone's run_chip_v2.sh, macro placement file and RTL root)
# Final stage of a chip v2 work home from a clean routed checkpoint (0 DRC, 0 antenna): the routed database
# becomes 5_2_route.odb (the main-route result stays in the write-protected 5_2_route_main.odb), then fill
# cells, the final report (RC extraction with the platform rules, 6_final.spef, and timing with it), the
# merged GDS (6_final.gds) and the CDL netlists for LVS (6_final.cdl, 6_final_concat.cdl).
# usage: final_t3.sh <work home> <clean routed odb name in results/, e.g. 5_2_route_r3.odb>
set -uo pipefail
readonly WH="${1:?work home}" IN="${2:?routed odb name}"
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test
readonly RES="${WH}/results/sky130hd/trustedge_asic_core/chipv2"
readonly OBJ="${WH}/objects/sky130hd/trustedge_asic_core/chipv2"
if [[ ! -f "${RES}/${IN}" || -e "${RES}/6_final.odb" ]]; then echo "FINAL_INPUT_GATE=FAIL"; exit 2; fi
{
  echo "FINAL_START $(date -Is) in=${IN}"
  sha256sum "${RES}/${IN}"
  # the routed checkpoints are write-protected and cp -p keeps that mode, so a plain copy over an earlier
  # 5_2_route.odb fails; replace the destination and check that the flow input is the requested database
  if [[ "${IN}" != 5_2_route.odb ]]; then
    cp --remove-destination "${RES}/${IN}" "${RES}/5_2_route.odb" && chmod u+w "${RES}/5_2_route.odb" \
      || { echo "FINAL_INPUT_COPY=FAIL"; exit 3; }
  fi
  if [[ "$(sha256sum < "${RES}/${IN}")" != "$(sha256sum < "${RES}/5_2_route.odb")" ]]; then
    echo "FINAL_INPUT_HASH=MISMATCH"; exit 3
  fi
  echo "FINAL_INPUT_HASH=MATCH"
  export CHIPV2_WORK_HOME="${WH}" CHIPV2_MACRO_TCL="${ROOT}/codeachip_t3/flow_chip/macros_chipv2.tcl" T3_ROOT="${T3_ROOT:-${ROOT}/codeachip_t3/build_t3e/root}"
  rc=0
  # do- targets only: a file target makes make walk the dependency chain back to synthesis (this work
  # home starts at CTS); the CDL netlists come from cdl_concat.tcl through `make run`
  for t in do-5_3_fillcell do-5_route do-5_route.sdc do-finish do-gds cdl; do
    echo "FINAL_STEP ${t} $(date -Is)"
    if [[ "${t}" == cdl ]]; then
      RUN_SCRIPT="${ROOT}/chip_v2/cdl_concat.tcl" RUN_LOG_NAME_STEM=6_cdl         bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" run || { rc=$?; echo "FINAL_STEP_FAIL ${t} rc=${rc}"; break; }
    else
      bash "${ROOT}/codeachip_t3/flow_chip/run_chip_v2.sh" "${t}" || { rc=$?; echo "FINAL_STEP_FAIL ${t} rc=${rc}"; break; }
    fi
  done
  [[ ${rc} -eq 0 ]] && ( cd "${RES}" && sha256sum 6_final.odb 6_final.gds 6_final.spef 6_final.v 6_final.sdc 2>/dev/null )
  echo "FINAL_DONE rc=${rc} $(date -Is)"
} 2>&1 | tee -a "${WH}/final_console.log"
