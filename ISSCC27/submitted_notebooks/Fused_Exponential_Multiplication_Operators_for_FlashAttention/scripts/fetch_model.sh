#!/usr/bin/env bash
# fetch flan-t5-base into a local directory (hf-mirror.com; IPv4)
set -u
D=$HOME/flashattn_expmul/models/flan-t5-base
BASE=https://hf-mirror.com/google/flan-t5-base/resolve/main
mkdir -p "$D"
cd "$D" || exit 1
for f in config.json generation_config.json tokenizer_config.json tokenizer.json \
         spiece.model special_tokens_map.json model.safetensors; do
  echo "fetch $f"
  curl -4 -sL --retry 5 --retry-delay 3 -o "$f" "$BASE/$f"
done
ls -la
echo DL_DONE
