#!/usr/bin/env bash
# Finish the stalled model.safetensors download: re-fetch parts 1/5/7 with
# fresh connections, then concatenate the 16 parts.
set -u
D=$HOME/flashattn_expmul/models/flan-t5-base
cd "$D" || exit 1
URL=https://hf-mirror.com/google/flan-t5-base/resolve/main/model.safetensors
SIZE=990345061
N=16
CH=$(( (SIZE + N - 1) / N ))

pkill -f fetch_parallel.sh 2>/dev/null
pkill -f 'model.safetensors' 2>/dev/null
sleep 1

for i in 1 5 7; do
  s=$(( i * CH )); e=$(( (i + 1) * CH - 1 ))
  [ "$e" -ge "$SIZE" ] && e=$(( SIZE - 1 ))
  (
    for try in 1 2 3 4 5 6; do
      have=$(stat -c %s "part_$i" 2>/dev/null || echo 0)
      need=$(( e - s + 1 ))
      if [ "$have" -ge "$need" ]; then break; fi
      curl -4 -sL --retry 3 -r "$(( s + have ))-$e" "$URL" >> "part_$i"
    done
  ) &
done
wait
ls -la part_1 part_5 part_7
cat $(for i in $(seq 0 $((N-1))); do echo -n "part_$i "; done) > model.safetensors
rm -f part_*
ls -la model.safetensors
echo FIX_DONE
