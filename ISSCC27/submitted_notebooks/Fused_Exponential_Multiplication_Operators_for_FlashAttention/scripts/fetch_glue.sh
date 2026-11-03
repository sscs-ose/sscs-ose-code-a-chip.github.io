#!/usr/bin/env bash
# Fetch the GLUE validation parquet files from hf-mirror (no hub access needed).
set -u
D=$HOME/flashattn_expmul/data/glue
BASE=https://hf-mirror.com/datasets/nyu-mll/glue/resolve/main
mkdir -p "$D"
cd "$D" || exit 1
for spec in \
  "sst2/validation-00000-of-00001.parquet sst2.parquet" \
  "cola/validation-00000-of-00001.parquet cola.parquet" \
  "mnli/validation_matched-00000-of-00001.parquet mnli_m.parquet" \
  "mnli/validation_mismatched-00000-of-00001.parquet mnli_mm.parquet" \
  "qqp/validation-00000-of-00001.parquet qqp.parquet" \
  "qnli/validation-00000-of-00001.parquet qnli.parquet" \
  "rte/validation-00000-of-00001.parquet rte.parquet" \
  "wnli/validation-00000-of-00001.parquet wnli.parquet" \
  "mrpc/validation-00000-of-00001.parquet mrpc.parquet" \
  "stsb/validation-00000-of-00001.parquet stsb.parquet" ; do
  set -- $spec
  echo "fetch $1"
  curl -4 -sL --retry 5 -o "$2" "$BASE/$1"
done
ls -la
echo GLUE_DONE
