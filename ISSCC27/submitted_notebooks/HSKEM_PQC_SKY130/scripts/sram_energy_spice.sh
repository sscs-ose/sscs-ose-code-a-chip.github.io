#!/usr/bin/env bash
# Transistor-level energy per access of the chip's OpenRAM macros (scripts/sram_energy_deck.py).
# Each macro's OpenRAM SPICE netlist is simulated whole in ngspice (KLU solver), one process per macro in
# parallel; a run takes 20 minutes to two hours on a desktop machine. Two details make the SKY130 models
# load: their files set scale=1u, so the netlist's device sizes are rewritten as unitless microns (OpenRAM
# writes junction areas with a 'u' or 'p' suffix, both meaning square microns), and ngspice needs
# "set ngbehavior=hsa" in a .spiceinit in its working directory.
# Optional: SRAM_FLAT_NETLIST=<file> simulates a flat layout extraction of one macro instead (all wiring
# capacitance included; several hours), to calibrate the wiring the schematic netlist leaves out.
# The OpenRAM netlists of the chip's eight macros are in flow/macros/spice/ (MACRO_SP_DIR overrides).
# usage: scripts/sram_energy_spice.sh <work dir> <macro> [<macro> ...]
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PDK_LIB="${PDK_LIB:-${PDK_ROOT:-/opt/eda/pdks-openram}/sky130A/libs.tech/ngspice/sky130.lib.spice}"
NGSPICE="${NGSPICE:-ngspice}"
W="${1:?work dir}"; shift
UNITS='/^[Xx]/ s/\b(ad|as|AD|AS)=([0-9.]+)[pu]/\1=\2/g; /^[Xx]/ s/\b(pd|ps|w|l|PD|PS|W|L)=([0-9.]+)u/\1=\2/g'
for M in "$@"; do
  (
    mkdir -p "$W/$M" && cd "$W/$M" || exit 1
    echo "set ngbehavior=hsa" > .spiceinit
    src="${SRAM_FLAT_NETLIST:-${MACRO_SP_DIR:-$ROOT/flow/macros/spice}/$M.sp}"
    { if [ -f "$src" ]; then cat "$src"; else gzip -dc "$src.gz"; fi; } | sed -E "$UNITS" > netlist_units.sp
    python3 "$ROOT/scripts/sram_energy_deck.py" netlist_units.sp "$M" energy.sp "$PDK_LIB"
    "$NGSPICE" -b energy.sp > energy.log 2>&1
    python3 "$ROOT/scripts/sram_energy_deck.py" --parse energy.log "$M" energy.json
  ) &
done
wait
