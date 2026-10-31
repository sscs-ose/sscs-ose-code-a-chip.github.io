#!/bin/bash
# usage: pow128c.sh <clock> ; real-activity compute power + reload power for the three 128-row redo layouts at that clock
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
clk=$1; V=python/vectors
go() { # name top kind npz winsig cyc-extra env...
  n=$1; top=$2; kind=$3; npz=$4; sig=$5; extra=$6; shift 6
  RUN=flow/p128/c${clk}_$n/runs/layout
  env "$@" GL_PERIOD=$clk NCASES=50 PERIOD_PS=$((clk*1000)) WINDOW_EXTRA_PS=$extra RUN=$RUN bash flow/gl_npz.sh p128/c${clk}_$n $top $kind $V/$npz real 2>&1 | grep -E "compared|Total"
  env "$@" GL_PERIOD=$clk NCASES=50 PERIOD_PS=$((clk*1000)) WIN_SIG=$sig WINDOW_EXTRA_PS=0 RUN=$RUN bash flow/gl_npz.sh p128/c${clk}_$n $top $kind $V/$npz load 2>&1 | grep -E "compared|Total"
}
go s3k4 sidecarcim_top top r128_sidecar_k4_real_layer.npz w_load_en $((clk*1000)) SBITS=3 PIPE=1
go w6a4 dcim_core w6a4 r128_w6a4_real_layer.npz load_en 0 X=1
go w4a4 dcim_core dense r128_w4a4_real_layer.npz load_en 0 X=1
python3 flow/extract_ppa128.py > /dev/null
python3 flow/extract_load.py > /dev/null
