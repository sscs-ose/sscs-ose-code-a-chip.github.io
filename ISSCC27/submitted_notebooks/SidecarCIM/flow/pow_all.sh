#!/bin/bash
# usage: pow_all.sh <flowdir> <top> <kind> <real.npz> <random.npz>   (latest run; real = first 100 real-layer cases)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
fd=$1; top=$2; kind=$3
GL_UD=${GL_UD:-0} bash flow/gl_npz.sh $fd $top $kind python/vectors/$4.npz real
GL_UD=${GL_UD:-0} bash flow/gl_npz.sh $fd $top $kind python/vectors/$5.npz random
