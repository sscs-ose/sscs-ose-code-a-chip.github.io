#!/usr/bin/env bash
# Re-run the baseline lane under a distinct DESIGN_NAME (results dirs are keyed
# by DESIGN_NAME, so the two variants must not share it).
set -eu
F=$HOME/orfs-src/flow
SRC="$F/designs/src/fa_lane_b"
DES="$F/designs/nangate45/fa_lane_b"
mkdir -p "$SRC" "$DES"
cp "$F/designs/src/fa_lane_base/"*.v "$SRC"/
cp "$F/designs/src/fa_lane_base/fp32_funcs.vh" "$SRC"/ 2>/dev/null || true
sed -i 's/module fa_lane_top/module fa_lane_b_top/' "$SRC/fa_lane_top.v"
mv "$SRC/fa_lane_top.v" "$SRC/fa_lane_b_top.v"
cp "$F/designs/nangate45/fa_lane_base/constraint.sdc" "$DES"/
sed -i 's/current_design fa_lane_top/current_design fa_lane_b_top/' "$DES/constraint.sdc"
cat > "$DES/config.mk" <<EOF
export DESIGN_NAME = fa_lane_b_top
export PLATFORM    = nangate45
export VERILOG_FILES = \$(sort \$(wildcard \$(DESIGN_HOME)/src/fa_lane_b/*.v))
export SDC_FILE      = \$(DESIGN_HOME)/nangate45/fa_lane_b/constraint.sdc
export CORE_UTILIZATION = 40
export PLACE_DENSITY    = 0.55
EOF
echo installed
