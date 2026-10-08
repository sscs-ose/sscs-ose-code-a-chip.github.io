#!/usr/bin/env bash
# Adopt an ORFS run whose launching script has died: wait for its make
# process to exit, then collect the results exactly as run_orfs.sh would.
# usage: adopt_run.sh <make pid> <tag, e.g. keccak_s7_20ns_ant10>
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
PID=${1:?pid}; TAG=${2:?tag}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${CAC_WORK:-$HOME/cac_runs}/$TAG"; DST="$ROOT/results/asic/$TAG"; mkdir -p "$DST"
start=$(stat -c %Y "$WORK/make.log")
tail --pid="$PID" -f /dev/null                     # block until the orphaned make exits
if ls "$WORK"/logs/sky130hd/*/base/6_report.log > /dev/null 2>&1; then rc=0; else rc=1; fi
echo "$rc $(( $(date +%s) - start ))" > "$DST/status.txt"
for d in logs reports; do
  [ -d "$WORK/$d" ] && rsync -a --include='*/' --include='*.log' --include='*.rpt' \
      --include='*.json' --include='*.txt' --exclude='*' "$WORK/$d/" "$DST/$d/"
done
find "$WORK/results" -name '6_final.gds' -exec cp {} "$DST/" \; 2>/dev/null || true
find "$WORK/results" -name '6_final.v' -exec cp {} "$DST/" \; 2>/dev/null || true
tail -5 "$WORK/make.log" > "$DST/make_tail.log"
echo "$TAG adopted rc=$rc"
grep -h '"detailedroute__antenna__violating__nets"\|"detailedroute__route__drc_errors"' \
     "$DST"/logs/sky130hd/*/base/5_2_route.json 2>/dev/null | tail -2
