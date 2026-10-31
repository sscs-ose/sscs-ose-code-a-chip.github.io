#!/bin/bash
# run_synth.sh — locate the sky130 PDK via volare, run Yosys, save log.
set -e
cd "$(dirname "$0")"
LIB=$(find ~/.volare -name "sky130_fd_sc_hd__tt_100C_1v80.lib" 2>/dev/null | head -1)
if [ -z "$LIB" ]; then
  echo "PDK liberty not found. Run: volare fetch --pdk sky130 <version> && volare enable --pdk sky130 <version>" >&2
  exit 1
fi
echo "Using liberty: $LIB"
mkdir -p synth
sed "s|@PDK_LIB@|$LIB|g" synth.ys > synth/synth_run.ys
yosys synth/synth_run.ys 2>&1 | tee synth/synth.log | tail -45
