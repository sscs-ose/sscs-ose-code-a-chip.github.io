#!/usr/bin/env bash
# Simulated-leakage TVLA for the NTT engine (dual-port FPGA-style RAM; LEAK_ASIC=1 for the single-port store).
# usage: run_leakage.sh [N traces] [noise sigma] [plain|masked]
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
N=${1:-400}; SIGMA=${2:-4.0}; MODE=${3:-plain}
OUT="$ROOT/results/leakage"; MFLAG=""
if [ "$MODE" = masked ]; then OUT="$ROOT/results/leakage_masked"; MFLAG="--masked"; fi
# LEAK_ASIC=1: the ASIC configuration of the engine (single-port store), written next to the FPGA results
DEF=""; SRAM=""; if [ "${LEAK_ASIC:-0}" = 1 ]; then OUT="${OUT}_asic"; DEF="-DTRUSTEDGE_ASIC_SRAM"; SRAM="$ROOT/rtl/te_sram_models.sv"; fi
# LEAK_PACKED=1: the packed-pair NTT (rtl/kyber_ntt_engine_packed.sv), written with a _packed suffix
ENGINE="$ROOT/rtl/kyber_ntt_engine.sv"; RED="$ROOT/rtl/barrett_reduce.v"
if [ "${LEAK_PACKED:-0}" = 1 ]; then OUT="${OUT}_packed"; DEF="$DEF -DNTT_PACKED"
  ENGINE="$ROOT/rtl/kyber_ntt_engine_packed.sv"; RED="$ROOT/rtl/barrett_reduce_1c.v"; fi
mkdir -p "$OUT"
cd "$ROOT/golden" && python3 leakage.py gen --out "$OUT" -n "$N" $MFLAG
R="$ROOT/rtl"
iverilog -g2012 $DEF -I "$OUT" -o "$OUT/leak.vvp" "$R/kyber_pkg.sv" "$RED" $SRAM \
    "$ENGINE" "$ROOT/tb/tb_ntt_leak.sv"
(cd "$OUT" && vvp -n leak.vvp | grep LEAK)
cd "$ROOT/golden" && python3 leakage.py analyze --out "$OUT" --sigma "$SIGMA"
rm -f "$OUT/leak.vvp"
