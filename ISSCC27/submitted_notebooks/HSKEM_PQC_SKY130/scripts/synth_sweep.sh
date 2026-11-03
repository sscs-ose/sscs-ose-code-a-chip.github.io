#!/usr/bin/env bash
# Synthesis-level design-space sweep (runs in Colab).
# SPDX-License-Identifier: Apache-2.0
HERE="$(cd "$(dirname "$0")" && pwd)"
for v in ${1:-ntt_dp ntt_sp keccak_r1 keccak_s7}; do
  for t in ${2:-10 20 40}; do
    echo "$v $t $(bash "$HERE/synth_sky130.sh" "$v" "$t" 2>&1 | tail -1)"
  done
done
