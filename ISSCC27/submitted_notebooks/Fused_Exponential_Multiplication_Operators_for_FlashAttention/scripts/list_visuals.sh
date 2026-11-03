#!/usr/bin/env bash
F=$HOME/orfs-src/flow
for d in fa_lane_b_top fa_lane_e_top fa_bf16_b_top fa_bf16_e_top; do
  echo "=== $d ==="
  find $F/results/nangate45/$d $F/reports/nangate45/$d -maxdepth 2 \( -name '*.png' -o -name '*.webp' -o -name '*.svg' -o -name '*.gds' \) 2>/dev/null | sed "s#$F/##"
done
echo "=== klayout ==="
ls /usr/bin/klayout 2>/dev/null
docker run --rm openroad/orfs:local which klayout 2>/dev/null
