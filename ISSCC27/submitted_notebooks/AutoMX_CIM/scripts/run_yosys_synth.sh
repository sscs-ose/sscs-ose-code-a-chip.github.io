#!/usr/bin/env bash
# Technology-independent synthesis receipt for the clocked AutoMX-CIM tile.
set -euo pipefail

if ! command -v yosys >/dev/null 2>&1; then
    echo "error: yosys is not on PATH" >&2
    exit 127
fi

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
out=${1:-"$root/build/yosys"}
mkdir -p "$out"

yosys -p "\
read_verilog -sv $root/rtl/automx_cim_slice.sv $root/rtl/automx_cim_sram_tile.sv; \
hierarchy -check -top automx_cim_sram_tile; \
proc; opt; memory; opt; techmap; opt; \
stat; write_json $out/automx_cim_sram_tile.json" \
    | tee "$out/automx_cim_sram_tile.rpt"

echo "Wrote $out/automx_cim_sram_tile.rpt and .json"