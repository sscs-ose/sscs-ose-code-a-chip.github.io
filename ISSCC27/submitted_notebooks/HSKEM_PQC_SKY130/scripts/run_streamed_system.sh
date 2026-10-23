#!/usr/bin/env bash
# The streamed system (Section 8): four cumulative milestones of scripts/make_packed_system.py's further
# defines, each in the three configurations, in parallel, then their summary
# (results/system_sim/streamed_system.json). Every build starts from step D (packed NTT, overlapped hashes,
# streamed read loops); the configurations differ only in the NTT store and the Keccak core.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
R=results/system_sim; mkdir -p "$R"
D="-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP -DTRUSTEDGE_STREAM_IO"
# E: the datapath moves one element per cycle
E="$D -DTRUSTEDGE_FAST_BASEMUL -DTRUSTEDGE_FAST_FEED -DTRUSTEDGE_STREAM_OUT -DTRUSTEDGE_FOLD_READBACK"
E="$E -DTRUSTEDGE_PREFETCH -DTRUSTEDGE_TIGHT_LOOPS -DTRUSTEDGE_FAST_CHECK -DTRUSTEDGE_FAST_Y"
# F: a two-lane engine and data in pairs
F="$E -DTRUSTEDGE_PACKED2 -DTRUSTEDGE_FAST_PRF -DTRUSTEDGE_FUSED_CMP -DTRUSTEDGE_FAST_READ"
# G: pipelined checks and products
G="$F -DTRUSTEDGE_PIPE_CHECK -DTRUSTEDGE_PAIR_PORT -DTRUSTEDGE_DEFER_J -DTRUSTEDGE_PIPE_MAC -DTRUSTEDGE_FAST_HASH"
# H: data streams between the engine and the datapath
H="$G -DTRUSTEDGE_DEC_STREAM -DTRUSTEDGE_SEG_CHECK -DTRUSTEDGE_BG_PRF -DTRUSTEDGE_STREAM_INV -DTRUSTEDGE_STREAM_FWD"
H="$H -DTRUSTEDGE_PRF_TO_NTT -DTRUSTEDGE_STREAM_DEC_INV -DTRUSTEDGE_PRF_FINE_HOLD -DTRUSTEDGE_POLY_GUARD"
run() {  # configuration, tag, defines
  ( CAC_PACKED_SYSTEM=1 CAC_EXTRA_DEFS="$3" CAC_SIM_TAG=$2 CAC_PROFILE=1 CAC_STATE_PROF=1 CAC_PACKED_CHECK=1 \
    CAC_J_PROBE=1 bash scripts/run_system_sim.sh "$1" > "$R/run_$1$2.out" 2>&1 ) &
}
for m in E F G H; do
  run sram_only "_str$m" "${!m}"
  run fpga "_str$m" "${!m}"
  run asic "_str$m" "${!m}"
done
wait
python3 scripts/collect_streamed_system.py
