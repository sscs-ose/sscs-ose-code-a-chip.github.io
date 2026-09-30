#!/usr/bin/env bash
# Formal proof (SAT) that rtl/barrett_reduce.v computes a mod 3329 for all
# 2^24 inputs. Uses Yosys' built-in SAT solver; no simulation involved.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="$HERE/../results/formal"; mkdir -p "$OUT"
# optional arg: an alternative implementation (used for the negative control)
IMPL=${1:-../rtl/barrett_reduce.v}; TAG=${2:-barrett_proof}
cd "$HERE"
yosys -q -l "$OUT/$TAG.log" -p "
  read_verilog $IMPL barrett_prop.v
  hierarchy -top barrett_prop
  proc; flatten; opt
  sat -prove ok 1 -show-inputs -show-outputs
"
grep -E "SAT proof finished|SUCCESS|FAIL|failed" "$OUT/$TAG.log" | head
