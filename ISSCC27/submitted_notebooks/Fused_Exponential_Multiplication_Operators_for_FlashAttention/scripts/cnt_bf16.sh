#!/usr/bin/env bash
for d in fa_bf16_b_top fa_bf16_e_top; do
  f=$HOME/orfs-src/flow/results/nangate45/$d/base/6_final.v
  n=$(grep -cE '^ [A-Z][A-Z0-9_]+_X[0-9]+ ' "$f")
  mux=$(grep -c 'MUX2_X1' "$f")
  echo "$d instances=$n mux2=$mux"
done
