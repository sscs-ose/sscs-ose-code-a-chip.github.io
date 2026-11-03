#!/usr/bin/env bash
# The eight full-system builds with the packed NTT (Section 8), in parallel, then their summary
# (results/system_sim/packed_system.json). Each build is made from the published RTL by
# scripts/make_packed_system.py; R repeats the chip's configuration without the new defines.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
R=results/system_sim; mkdir -p "$R"
run() {  # configuration, tag, defines, contract checker
  ( CAC_PACKED_SYSTEM=1 CAC_EXTRA_DEFS="$3" CAC_SIM_TAG=$2 CAC_PROFILE=1 CAC_STATE_PROF=1 CAC_PACKED_CHECK=$4 \
    bash scripts/run_system_sim.sh "$1" > "$R/run_$1$2.out" 2>&1 ) &
}
run asic _sysR "" 0
run asic _sysA "-DTRUSTEDGE_PACKED_NTT" 1
run sram_only _sysB "-DTRUSTEDGE_PACKED_NTT" 1
run sram_only _sysBC "-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP" 1
run asic _sysAC "-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP" 1
run fpga _sysFC "-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP" 1
run sram_only _sysBCD "-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP -DTRUSTEDGE_STREAM_IO" 1
run fpga _sysFCD "-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP -DTRUSTEDGE_STREAM_IO" 1
wait
python3 scripts/collect_packed_system.py
