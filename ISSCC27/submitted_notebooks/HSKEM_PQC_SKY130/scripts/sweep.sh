#!/usr/bin/env bash
# Design-space sweep: every variant x every clock target, N jobs in parallel.
# usage: sweep.sh "<variants>" "<clocks_ns>" [jobs]
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VARS=${1:-"ntt_dp ntt_sp keccak_r1 keccak_s7"}; CLKS=${2:-"20"}; J=${3:-4}
for v in $VARS; do for t in $CLKS; do echo "$v $t"; done; done |
  xargs -P "$J" -L 1 bash "$HERE/run_orfs.sh"
