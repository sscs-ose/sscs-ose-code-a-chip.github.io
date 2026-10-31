#!/bin/bash
# usage: tryseq.sh <flowdir> try1 try2 ... ; stops at first config with 0 setup violations
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
d=$1; shift
for t in "$@"; do
  bash flow/try.sh $d $t
  grep -q '"timing__setup_vio__count": 0' flow/logs/${d}_$t.res && break
done
echo done > flow/logs/tryseq.done
