#!/usr/bin/env bash
# Finish part_1 with 8 parallel sub-ranges (single connections get throttled).
set -u
D=$HOME/flashattn_expmul/models/flan-t5-base
cd "$D" || exit 1
URL=https://hf-mirror.com/google/flan-t5-base/resolve/main/model.safetensors
pkill -f fetch_finish.sh 2>/dev/null
pkill -f 'model.safetensors' 2>/dev/null
sleep 1
S=61896567          # part_1 start
E=123793133         # part_1 end
HAVE=$(stat -c %s part_1)
START=$(( S + HAVE ))
REM=$(( E - START + 1 ))
echo "part_1 have=$HAVE start=$START rem=$REM"
N=8
CH=$(( (REM + N - 1) / N ))
for i in $(seq 0 $((N-1))); do
  s=$(( START + i * CH ))
  e=$(( START + (i + 1) * CH - 1 ))
  [ "$e" -gt "$E" ] && e=$E
  [ "$s" -gt "$E" ] && continue
  curl -4 -sL --retry 4 -r "$s-$e" -o "sub_$i" "$URL" &
done
wait
for i in $(seq 0 $((N-1))); do [ -f "sub_$i" ] && cat "sub_$i" >> part_1; done
rm -f sub_*
ls -la part_1
cat $(for i in $(seq 0 15); do echo -n "part_$i "; done) > model.safetensors
ls -la model.safetensors
echo PART1_DONE
