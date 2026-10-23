#!/usr/bin/env bash
# Run all RTL-vs-golden simulations with Icarus Verilog.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# relative overrides are taken relative to the submission root
abs() { (cd "$ROOT" && mkdir -p "$1" && cd "$1" && pwd); }
OUT="$(abs "${CAC_SIM_OUT:-results/sim}")"
VEC="$(abs "${CAC_VEC_OUT:-vectors}")"
cd "$ROOT/golden" && python3 gen_vectors.py --out "$VEC" "$@"
cd "$VEC"
R="$ROOT/rtl"; TB="$ROOT/tb"
run() { local name=$1; shift
  iverilog -g2012 -I . -o "$OUT/$name.vvp" "$@"
  vvp -n "$OUT/$name.vvp" | tee "$OUT/$name.log" | grep -E "RESULT|PASS|FAIL|MISMATCH"; }
# NTT, FPGA-style true-dual-port coefficient RAM
run ntt_dualport  "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/kyber_ntt_engine.sv" "$TB/tb_ntt.sv"
# NTT, ASIC-style single-port SRAM (serialized butterfly)
run ntt_singleport -DTRUSTEDGE_ASIC_SRAM "$R/kyber_pkg.sv" "$R/barrett_reduce.v" \
    "$R/te_sram_models.sv" "$R/kyber_ntt_engine.sv" "$TB/tb_ntt.sv"
run keccak_round  -DSERIAL=0 "$R/keccak_f1600_iter.sv" "$TB/tb_keccak.sv"
run keccak_serial -DSERIAL=1 "$R/keccak_f1600_iter.sv" "$TB/tb_keccak.sv"
rm -f "$OUT"/*.vvp
