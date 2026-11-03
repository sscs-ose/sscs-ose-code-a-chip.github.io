#!/usr/bin/env sh
# Run the documented TT 20 mV (FFT bin 3) public diagnostic.
set -eu

cd "$(dirname "$0")"
exec python3 analyze_fct.py --deck tb_dynamic_tt_20mv.spi --input-peak-v 0.02 --tone-bin 3
