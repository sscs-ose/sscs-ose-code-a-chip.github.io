#!/usr/bin/env bash
# Run one design-space point through ORFS (sky130hd) and collect metrics.
# usage: run_orfs.sh <ntt_dp|ntt_sp|keccak_r1|keccak_s7> <clock_ns>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
V=$1; T=$2
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
export PATH="$ORFS/tools/install/OpenROAD/bin:$ORFS/tools/install/yosys/bin:$PATH"
# a relocated tool bundle (scripts/make_orfs_bundle.sh) supplies wrapper scripts through these two variables
export YOSYS_EXE="${YOSYS_EXE:-$ORFS/tools/install/yosys/bin/yosys}"
export OPENROAD_EXE="${OPENROAD_EXE:-$ORFS/tools/install/OpenROAD/bin/openroad}"
TAG="${V}_${T/./p}ns${CAC_TAG_SUFFIX:-}"
WORK="${CAC_WORK:-$HOME/cac_runs}/$TAG"; mkdir -p "$WORK"
DST="$ROOT/results/asic/$TAG"; mkdir -p "$DST"
start=$(date +%s)
set +e
make -C "$ORFS/flow" DESIGN_CONFIG="$ROOT/flow/config.mk" \
     CAC_ROOT="$ROOT" CAC_VARIANT="$V" CAC_CLK_NS="$T" \
     WORK_HOME="$WORK" ${CAC_MAKE_ARGS:-} ${CAC_TARGET:-finish} > "$WORK/make.log" 2>&1
rc=$?
set -e
echo "$rc $(( $(date +%s) - start ))" > "$DST/status.txt"
# keep only small, reviewable artifacts in the repository
for d in logs reports; do        # (find + cp rather than rsync, which minimal systems lack)
  [ -d "$WORK/$d" ] || continue
  (cd "$WORK/$d" && find . -type f \( -name '*.log' -o -name '*.rpt' -o -name '*.json' -o -name '*.txt' \) |
     while read -r f; do mkdir -p "$DST/$d/$(dirname "$f")"; cp -p "$f" "$DST/$d/$f"; done)
done
find "$WORK/results" -name '6_final.gds' -exec cp {} "$DST/" \; 2>/dev/null || true
find "$WORK/results" -name '6_final.v' -exec cp {} "$DST/" \; 2>/dev/null || true
tail -5 "$WORK/make.log" > "$DST/make_tail.log"
echo "$TAG rc=$rc"
