#!/usr/bin/env bash
# Worst slack of the paths starting and ending at the SRAM macros, for the macro views scaled by each factor
# (scripts/scale_macro_lib.py; the scaled copies written by sta_macro_bound.sh are reused when present).
# usage: FULLCHIP_DIR=... MACRO_LIB_DIR=... scripts/sta_macro_paths.sh <out dir> <corner> <factor> [<factor> ...]
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; OPENROAD="$ORFS/tools/install/OpenROAD/bin/openroad"
PDK="${SKY130_LIBS:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
OUT="${1:?out dir}"; CORNER="${2:?corner}"; shift 2
for k in "$@"; do
  D="$OUT/libs_x$k"; mkdir -p "$D"
  [ -n "$(ls "$D"/*.physical.lib 2>/dev/null)" ] || for f in "$M"/*.physical.lib; do
    python3 "$ROOT/scripts/scale_macro_lib.py" "$f" "$D/$(basename "$f")" "$k" > /dev/null; done
  LIB="$PDK/sky130_fd_sc_hd__$CORNER.lib" EXTRA_LIBS="$(ls "$D"/*.physical.lib | tr '\n' ' ')" ODB="$B/6_final.odb" \
    SDC="$B/6_final.sdc" SPEF="$B/6_final.spef" "$OPENROAD" -no_splash -exit "$ROOT/flow/sta_macro_paths.tcl" \
    > "$OUT/macro_paths_${CORNER}_x$k.log" 2>&1
  echo "x$k"; awk '/^SECTION/{s=$2} /\(MET\)|\(VIOLATED\)/{print s, $0}' "$OUT/macro_paths_${CORNER}_x$k.log" | cut -c1-200
done
