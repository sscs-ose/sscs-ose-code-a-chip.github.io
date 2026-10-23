#!/usr/bin/env bash
# What-if STA of the routed full chip at one corner with the macro arcs scaled: how slow can the SRAM clock-to-output
# and setup arcs get before a path through a macro is the chip's worst path? Runs flow/sta_corner_fullchip.tcl once per
# factor on copies of the macro views scaled by scale_macro_lib.py, and writes <out dir>/bound_<corner>_x<factor>.log.
# usage: FULLCHIP_DIR=<ORFS results dir> MACRO_LIB_DIR=<*.physical.lib dir> scripts/sta_macro_bound.sh <out dir> <corner> <factor> [<factor> ...]
# The routed database is private (see README); only the summary of the results is published.
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; OPENROAD="$ORFS/tools/install/OpenROAD/bin/openroad"
PDK="${SKY130_LIBS:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
OUT="${1:?out dir}"; CORNER="${2:?corner, e.g. ss_100C_1v60}"; shift 2
mkdir -p "$OUT"
for k in "$@"; do
  D="$OUT/libs_x$k"; mkdir -p "$D"
  for f in "$M"/*.physical.lib; do python3 "$ROOT/scripts/scale_macro_lib.py" "$f" "$D/$(basename "$f")" "$k" > /dev/null; done
  LIB="$PDK/sky130_fd_sc_hd__$CORNER.lib" EXTRA_LIBS="$(ls "$D"/*.physical.lib | tr '\n' ' ')" ODB="$B/6_final.odb" \
    SDC="$B/6_final.sdc" SPEF="$B/6_final.spef" /usr/bin/time -f "%e s %M kB" -o "$OUT/bound_${CORNER}_x$k.time" \
    "$OPENROAD" -no_splash -exit "$ROOT/flow/sta_corner_fullchip.tcl" > "$OUT/bound_${CORNER}_x$k.log" 2>&1
  echo "x$k $(grep RESULT "$OUT/bound_${CORNER}_x$k.log" | tr '\n' ' ') $(cat "$OUT/bound_${CORNER}_x$k.time")"
done
