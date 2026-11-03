#!/bin/bash
# gate-level power during weight reload (window = load_en high: N_IN row loads + slot/S column loads), tag "load"
# usage: loadpow.sh <flowdir> <top> <kind> <npz> <win_signal> [env assignments...]
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
fd=$1; top=$2; kind=$3; npz=$4; sig=$5; shift 5
env "$@" WIN_SIG=$sig NCASES=${NCASES:-50} bash flow/gl_npz.sh $fd $top $kind $npz load 2>&1 | grep -E "compared|Total"
