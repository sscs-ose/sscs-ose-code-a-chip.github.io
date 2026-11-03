#!/usr/bin/env bash
# Staging of the HSKEM-2 rev B (t3e w1) notebook integration: cells.csv.gz (dump_cells.tcl), blocks.csv
# (fullchip_blocks.py in a mirror of the codeachip layout) and fullchip_layout.png (render_gds.py) of the parked final
# /root/t3/t3e_final_w1, into chip_v2/signoff/fullchip_stage_t3e. Same steps as stage_cells/blocks/render.sh of rev A.
set -euo pipefail
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test FINAL=/root/t3/t3e_final_w1
readonly STAGE="${ROOT}/chip_v2/signoff/fullchip_stage_t3e" MIRROR="${ROOT}/chip_v2/signoff/stage_root_t3e"
PDK="$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)"
mkdir -p "${STAGE}" "${MIRROR}/scripts" "${MIRROR}/results/fullchip"
TMP=$(mktemp -d /root/stagecells.XXXX)
ODB="${FINAL}/results/6_final.odb" OUT="${TMP}/cells.csv" \
  /opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad -no_splash -exit "${ROOT}/codeachip/flow/dump_cells.tcl" > "${TMP}/dump.log" 2>&1
echo "cells rows=$(wc -l < "${TMP}/cells.csv") macros=$(awk -F, '$6==1' "${TMP}/cells.csv" | wc -l)"
gzip -9 -n -c "${TMP}/cells.csv" > "${STAGE}/cells.csv.gz"; rm -rf "${TMP}"
cp "${ROOT}/codeachip/scripts/fullchip_blocks.py" "${MIRROR}/scripts/"
cp "${STAGE}/cells.csv.gz" "${MIRROR}/results/fullchip/cells.csv.gz"
python3 "${MIRROR}/scripts/fullchip_blocks.py" "${FINAL}/results/6_final.v" "${PDK}/sky130_fd_sc_hd__tt_025C_1v80.lib"
cp "${MIRROR}/results/fullchip/blocks.csv" "${STAGE}/blocks.csv"
/usr/bin/time -v klayout -zz -r "${ROOT}/codeachip/scripts/render_gds.py" -rd gds="${FINAL}/results/6_final.gds" \
  -rd png="${STAGE}/fullchip_layout.png" -rd px=2400 2>&1 | grep -E "Maximum resident|Elapsed|rror" || true
sha256sum "${FINAL}/results/6_final.odb" "${FINAL}/results/6_final.v" "${FINAL}/results/6_final.gds" "${STAGE}"/*
