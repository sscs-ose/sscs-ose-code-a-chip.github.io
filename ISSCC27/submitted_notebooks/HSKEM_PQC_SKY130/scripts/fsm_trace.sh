#!/usr/bin/env bash
# Record the NTT controller's state, cycle by cycle, for the first butterflies
# of a forward transform in both memory variants (Icarus Verilog + VCD), and
# write the traces to results/fsm_trace/<variant>.csv.
# usage: fsm_trace.sh [cycles to keep, default 40]
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; KEEP=${1:-40}
OUT="$ROOT/results/fsm_trace"; TMP="$(mktemp -d)"; mkdir -p "$OUT"
# four corner-case polynomials plus one random one; the trace covers vector 4
(cd "$ROOT/golden" && python3 gen_vectors.py --out "$TMP" --ntt 1 --keccak 1 > /dev/null)
R="$ROOT/rtl"
cd "$TMP"
iverilog -g2012 -I . -DVCD_OUT='"dp.vcd"' -DVCD_VEC=4 -o dp.vvp \
    "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/kyber_ntt_engine.sv" "$ROOT/tb/tb_ntt.sv"
iverilog -g2012 -I . -DVCD_OUT='"sp.vcd"' -DVCD_VEC=4 -DTRUSTEDGE_ASIC_SRAM -o sp.vvp \
    "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/te_sram_models.sv" "$R/kyber_ntt_engine.sv" "$ROOT/tb/tb_ntt.sv"
vvp -n dp.vvp | grep -E "NTT_RESULT|PASS|FAIL"
vvp -n sp.vvp | grep -E "NTT_RESULT|PASS|FAIL"
python3 "$ROOT/scripts/fsm_trace.py" dp.vcd "$OUT/ntt_dp.csv" "$KEEP"
python3 "$ROOT/scripts/fsm_trace.py" sp.vcd "$OUT/ntt_sp.csv" "$KEEP"
rm -rf "$TMP"
