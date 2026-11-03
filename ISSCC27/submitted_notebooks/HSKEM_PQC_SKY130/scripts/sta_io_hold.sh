#!/usr/bin/env bash
# Hold slack of the routed chip at one corner for several minimum input delays (the external launch delay of the inputs).
# The chip's SDC sets 2.0 ns for every input, minimum and maximum; this writes SDC copies whose minimum is the given value.
# usage: FULLCHIP_DIR=... MACRO_LIB_DIR=... scripts/sta_io_hold.sh <corner> <min input delay ns> [<ns> ...]
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; OPENROAD="$ORFS/tools/install/OpenROAD/bin/openroad"
PDK="${SKY130_LIBS:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
CORNER="${1:?corner}"; shift
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
for X in "$@"; do
  awk -v x="$X" '/^set_input_delay 2\.0000 /{ l=$0; sub(/^set_input_delay 2\.0000 /,"set_input_delay 2.0000 -max ",l); print l;
        m=$0; sub(/^set_input_delay 2\.0000 /,"set_input_delay " x " -min ",m); print m; next } {print}' "$B/6_final.sdc" > "$T/in.sdc"
  LIB="$PDK/sky130_fd_sc_hd__$CORNER.lib" EXTRA_LIBS="$(ls "$M"/*.physical.lib | tr '\n' ' ')" ODB="$B/6_final.odb" SDC="$T/in.sdc" \
    SPEF="$B/6_final.spef" MIN_IN="$X" "$OPENROAD" -no_splash -exit "$ROOT/flow/sta_io_hold.tcl" 2>&1 | grep RESULT | tr '\n' ' '; echo
done
