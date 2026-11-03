#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
PY="${HASHPARETO_PYTHON:-${PYTHON:-python3}}"

for u in 1 2 4 8 16; do
    echo "==== UNROLL=$u ===="
    "$PY" verif/cocotb/run.py --sim verilator --unroll "$u" 2>&1 | tr '\r' '\n' | grep -E 'PASS |FAIL |TESTS='
done