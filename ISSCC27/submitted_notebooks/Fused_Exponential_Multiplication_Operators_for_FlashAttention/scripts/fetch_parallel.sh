#!/usr/bin/env bash
# Parallel ranged download of model.safetensors from hf-mirror (per-connection
# throttling is the bottleneck; 16 connections aggregate much better).
set -u
D=$HOME/flashattn_expmul/models/flan-t5-base
URL=https://hf-mirror.com/google/flan-t5-base/resolve/main/model.safetensors
cd "$D" || exit 1
SIZE=$(curl -4 -sIL "$URL" | grep -i '^content-length' | tail -1 | tr -d '\r' | awk '{print $2}')
echo "size=$SIZE"
N=16
CH=$(( (SIZE + N - 1) / N ))
rm -f part_* 
for i in $(seq 0 $((N-1))); do
  s=$(( i * CH ))
  e=$(( (i + 1) * CH - 1 ))
  [ "$e" -ge "$SIZE" ] && e=$(( SIZE - 1 ))
  curl -4 -sL --retry 5 --retry-delay 2 -r "$s-$e" -o "part_$i" "$URL" &
done
wait
ls -la part_* | head -3
cat $(for i in $(seq 0 $((N-1))); do echo -n "part_$i "; done) > model.safetensors
rm -f part_*
ls -la model.safetensors
echo PARALLEL_DONE
