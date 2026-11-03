#!/usr/bin/env bash
# Compile + run the vendored 5-sequence SHA-256 top testbench against the
# parameterized core, for a given UNROLL, using Icarus Verilog.
#
#   tools/run_icarus_top_tb.sh [UNROLL]
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNROLL="${1:-1}"
OUT="/tmp/hashpareto_top_u${UNROLL}.vvp"

iverilog -g2012 -o "$OUT" \
  -Psha_top.UNROLL="$UNROLL" \
  "$ROOT/rtl/generated/sha_top.sv" \
  "$ROOT/rtl/generated/sha256_core.sv" \
  "$ROOT/rtl/original/rtl/core/message_padder.sv" \
  "$ROOT/rtl/original/rtl/core/digest_buffer.sv" \
  "$ROOT/rtl/generated/tb/sha_top_seq_tb.sv"

vvp "$OUT"
