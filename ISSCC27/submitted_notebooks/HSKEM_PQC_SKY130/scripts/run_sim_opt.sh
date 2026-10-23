#!/usr/bin/env bash
# Simulate the design-iteration NTT variants against the golden vectors.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; R="$ROOT/rtl"
OUT="$ROOT/results/sim_opt"; mkdir -p "$OUT"
VEC="$ROOT/vectors"; [ -f "$VEC/ntt_in.hex" ] || (cd "$ROOT/golden" && python3 gen_vectors.py --out "$VEC")
cd "$VEC"
# name  BARRETT_1C PIPE_MUL COEFF_W
while read -r name b1 pipe cw; do
  iverilog -g2012 -I . -DNTT_OPT -DB1C=$b1 -DPIPE=$pipe -DCW=$cw -o "$OUT/$name.vvp" \
      "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/barrett_reduce_1c.v" "$R/te_sram_models.sv" \
      "$R/kyber_ntt_engine_opt.sv" "$ROOT/tb/tb_ntt.sv"
  vvp -n "$OUT/$name.vvp" > "$OUT/$name.log"; rm -f "$OUT/$name.vvp"
  echo "$name $(grep -E 'NTT_RESULT' "$OUT/$name.log") $(grep -cx PASS "$OUT/$name.log")"
done <<'LIST'
opt_ref      0 0 16
opt_b1       1 0 16
opt_b1_w12   1 0 12
opt_pipe_w12 1 1 12
LIST
