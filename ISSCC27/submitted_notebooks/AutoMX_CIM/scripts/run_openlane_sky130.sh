#!/usr/bin/env bash
# Baseline SKY130 PPA flow for the inferred-memory tile.
# Replace inferred banks with macro blackboxes + LEF/GDS/LIB/SPEF before using
# this result as a physical CiROM claim.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
design="$root/openlane/automx_cim_sram_tile"

if ! command -v flow.tcl >/dev/null 2>&1; then
    echo "error: flow.tcl is not on PATH; activate the OpenLane/conda-eda environment first" >&2
    exit 127
fi

(
    cd "$design"
    export PDK=sky130A
    flow.tcl -design . -tag automx_cim_sram_tile_baseline -overwrite
)