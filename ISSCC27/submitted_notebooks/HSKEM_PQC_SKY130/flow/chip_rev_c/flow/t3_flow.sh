#!/usr/bin/env bash
# Full-chip ORFS flow of this clone (the flow of chip_v2/run_chip_v2.sh with the clone's public-RTL root).
# usage: t3_flow.sh <work dir> <target: synth|floorplan|place|cts|grt|...> [extra make args]
#   env: T3_ROOT (default ../build_pub/root), T3_CLK_NS (default 40), T3_DEFINES_EXTRA (appended to VERILOG_DEFINES)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; P=/mnt/d/TKVM_ATTT_2026_test
WORK="${1:?work dir}"; TARGET="${2:?target}"; shift 2
ORFS=/opt/eda/orfs-6101364b
LEF_DIR=$P/report/a2_macro_link_smoke/run.rjfysF/derived_lef; LIB_DIR=$P/report/a2_macro_link_smoke/run.rjfysF/derived_liberty
export M5_MACRO_LEFS="$(find $LEF_DIR -maxdepth 1 -name '*.lef' | sort | tr '\n' ' ')"
export M5_MACRO_LIBS="$(find $LIB_DIR -maxdepth 1 -name '*.physical.lib' | sort | tr '\n' ' ')"
export DIE_AREA="0 0 3351.335 3351.335"; export CORE_AREA="1.380 2.720 3350.180 3348.320"
export MACRO_PLACEMENT_TCL="${T3_MACRO_TCL:-$HERE/flow_chip/macros_chipv2.tcl}"
[ -n "${T3_CLK_NS:-}" ] && sed -i "s/create_clock -name core_clk -period [0-9.]*/create_clock -name core_clk -period $T3_CLK_NS/" "$HERE/flow_chip/constraint.sdc"
export T3_DEFINES_EXTRA="${T3_DEFINES_EXTRA:-}"
exec make -C "$ORFS/flow" DESIGN_CONFIG="$HERE/flow_chip/config.mk" WORK_HOME="$WORK" TRUSTEDGE_ROOT="${T3_ROOT:-$HERE/build_pub/root}" \
     FLOW_VARIANT=t3 CORE_UTILIZATION= "$@" "$TARGET"
