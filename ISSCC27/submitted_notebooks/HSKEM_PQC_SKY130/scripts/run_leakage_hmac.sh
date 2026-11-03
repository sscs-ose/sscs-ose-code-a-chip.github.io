#!/usr/bin/env bash
# Simulated-leakage TVLA for the session HMAC (fixed vs random key, random messages; tb/tb_hmac_leak.sv).
# usage: run_leakage_hmac.sh [N traces] [noise sigma]          results: results/leakage_hmac/
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
N=${1:-2000}; SIGMA=${2:-4.0}
OUT="$ROOT/results/leakage_hmac"; mkdir -p "$OUT"
H="$ROOT/hskem_rtl/rtl/hsm"
cd "$ROOT/golden" && python3 leakage_hmac.py gen --out "$OUT" -n "$N"
iverilog -g2012 -I "$OUT" -o "$OUT/leak.vvp" "$H/sha256_compress.sv" "$H/hmac_sha256_fixed.sv" "$ROOT/tb/tb_hmac_leak.sv"
(cd "$OUT" && vvp -n leak.vvp | grep HMAC_LEAK)
cd "$ROOT/golden" && python3 leakage_hmac.py analyze --out "$OUT" --sigma "$SIGMA"
rm -f "$OUT/leak.vvp"
