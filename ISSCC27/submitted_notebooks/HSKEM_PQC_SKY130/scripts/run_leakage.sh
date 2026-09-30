#!/usr/bin/env bash
# Simulated-leakage TVLA for the NTT engine (dual-port FPGA-style RAM).
# usage: run_leakage.sh [N traces] [noise sigma] [plain|masked]
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
N=${1:-400}; SIGMA=${2:-4.0}; MODE=${3:-plain}
OUT="$ROOT/results/leakage"; MFLAG=""
if [ "$MODE" = masked ]; then OUT="$ROOT/results/leakage_masked"; MFLAG="--masked"; fi
mkdir -p "$OUT"
cd "$ROOT/golden" && python3 leakage.py gen --out "$OUT" -n "$N" $MFLAG
R="$ROOT/rtl"
iverilog -g2012 -I "$OUT" -o "$OUT/leak.vvp" "$R/kyber_pkg.sv" "$R/barrett_reduce.v" \
    "$R/kyber_ntt_engine.sv" "$ROOT/tb/tb_ntt_leak.sv"
(cd "$OUT" && vvp -n leak.vvp | grep LEAK)
cd "$ROOT/golden" && python3 leakage.py analyze --out "$OUT" --sigma "$SIGMA"
rm -f "$OUT/leak.vvp"
