#!/usr/bin/env bash
# Post-route clock sweep split into short chunks (two runs in parallel each),
# so the sweep never has to run overnight. Results accumulate in results/asic/.
# usage: run_chunk.sh A|B|C|D|I|J
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
case ${1:?chunk} in
  A) PTS=("ntt_sp 15" "ntt_sp 30");;
  B) PTS=("keccak_r1 10" "keccak_s7 10");;
  C) PTS=("ntt_dp 15" "ntt_dp 30");;
  D) PTS=("keccak_r1 7" "keccak_s7 7");;
  I) PTS=("ntt_opt_b1_w12 20" "ntt_opt_pipe_w12 20");;       # design iteration, same 20 ns target
  J) PTS=("ntt_opt_pipe_w12 12" "ntt_sp 12");;               # pipelined NTT at a tighter clock
  *) echo "unknown chunk $1"; exit 2;;
esac
printf '%s\n' "${PTS[@]}" | xargs -P 2 -L 1 nice -n 10 bash "$HERE/run_orfs.sh"
