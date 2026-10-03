#!/usr/bin/env bash
# Simulate the packed-pair, layer-fused NTT engine against the golden vectors.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; R="$ROOT/rtl"
OUT="$ROOT/results/sim_packed"; mkdir -p "$OUT"
VEC="$ROOT/vectors"; [ -f "$VEC/ntt_in.hex" ] || (cd "$ROOT/golden" && python3 gen_vectors.py --out "$VEC")
cd "$VEC"
for x in 0 1; do
  name=packed_x$x
  iverilog -g2012 -I . -DNTT_PACKED -DXSTAGE=$x -o "$OUT/$name.vvp" \
      "$R/kyber_pkg.sv" "$R/barrett_reduce_1c.v" "$R/kyber_ntt_engine_packed.sv" "$ROOT/tb/tb_ntt.sv"
  vvp -n "$OUT/$name.vvp" > "$OUT/$name.log"; rm -f "$OUT/$name.vvp"
  echo "$name $(grep -E 'NTT_RESULT' "$OUT/$name.log") $(grep -cx PASS "$OUT/$name.log")"
done
