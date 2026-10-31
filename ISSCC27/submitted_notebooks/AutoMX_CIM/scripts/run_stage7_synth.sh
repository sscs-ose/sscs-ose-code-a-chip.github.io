#!/usr/bin/env bash
# Structural-only controller synthesis: this is not SKY130 PPA.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
out="$root/build/yosys_stage7"
if ! command -v yosys >/dev/null 2>&1; then
    echo "yosys is not on PATH" >&2
    exit 127
fi
mkdir -p "$out"
yosys -p "read_verilog -sv $root/rtl/automx_ternary_cim_4x4_blackbox.sv $root/rtl/automx_cim_tile_controller.sv; hierarchy -check -top automx_cim_tile_controller; synth -top automx_cim_tile_controller -noabc; stat; write_json $out/automx_cim_tile_controller.json" \
    | tee "$out/automx_cim_tile_controller.rpt"
echo "Structural controller report: $out/automx_cim_tile_controller.rpt"
echo "This excludes physical wrapper area, timing, energy, ADC and macro-bound routing."
