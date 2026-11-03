#!/usr/bin/env bash
# Re-time every routed design point at the ss / tt / ff corners (OpenROAD's STA on the routed database
# with the extracted SPEF; flow/sta_corner.tcl explains why the database rather than 6_final.v is read).
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"; OPENROAD="$ORFS/tools/install/OpenROAD/bin/openroad"
PDK="${SKY130_LIBS:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib | head -1)}"
OUT="$ROOT/results/sta_corners"; mkdir -p "$OUT"
for run in ${RUNS:-ntt_dp_20ns ntt_sp_20ns keccak_r1_20ns keccak_s7_20ns ntt_opt_b1_w12_20ns ntt_opt_pipe_w12_20ns ntt_opt_pipe_w12_12ns}; do
  nick=$(echo "$run" | sed -E 's/(_[0-9p]+ns)_.*$/\1/')     # experiment suffixes (e.g. _hm170) are not part of the design name
  B="${CAC_WORK:-$HOME/cac_runs}/$run/results/sky130hd/cac_$nick/base"
  for corner in ss_100C_1v60 tt_025C_1v80 ff_n40C_1v95; do
    LIB="$PDK/sky130_fd_sc_hd__$corner.lib" ODB="$B/6_final.odb" SDC="$B/6_final.sdc" \
    SPEF="$B/6_final.spef" "$OPENROAD" -no_splash -exit "$ROOT/flow/sta_corner.tcl" \
      > "$OUT/${run}_$corner.log" 2>&1
    echo "$run $corner $(grep RESULT "$OUT/${run}_$corner.log" | tr '\n' ' ')"
  done
done
