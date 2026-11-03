#!/usr/bin/env bash
for v in base exp; do
  R=$HOME/orfs-src/flow/reports/nangate45/fa_lane_top/$v/6_finish.rpt
  echo "=== $v ==="
  grep -E "Design area|Chip area" "$R" | head -2
  grep -A2 "Group *Internal" "$R" | head -3
  grep "^Total" "$R" | head -2
  grep -E "worst slack|WNS" $HOME/orfs-src/flow/logs/nangate45/fa_lane_top/$v/*.log 2>/dev/null | tail -1
done
