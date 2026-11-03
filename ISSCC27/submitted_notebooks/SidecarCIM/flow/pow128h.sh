#!/bin/bash
# compute + reload power for the hold-repair 128-row layout of the final build (35 ns, c35h_s3k4)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
clk=35; V=python/vectors; RUN=flow/p128/c35h_s3k4/runs/layout
env SBITS=3 PIPE=1 GL_PERIOD=$clk NCASES=50 PERIOD_PS=35000 WINDOW_EXTRA_PS=35000 RUN=$RUN bash flow/gl_npz.sh p128/c35h_s3k4 sidecarcim_top top $V/r128_sidecar_k4_real_layer.npz real 2>&1 | grep -E "compared|Total"
env SBITS=3 PIPE=1 GL_PERIOD=$clk NCASES=50 PERIOD_PS=35000 WIN_SIG=w_load_en WINDOW_EXTRA_PS=0 RUN=$RUN bash flow/gl_npz.sh p128/c35h_s3k4 sidecarcim_top top $V/r128_sidecar_k4_real_layer.npz load 2>&1 | grep -E "compared|Total"
python3 flow/extract_ppa128.py > /dev/null
python3 flow/extract_load.py > /dev/null
