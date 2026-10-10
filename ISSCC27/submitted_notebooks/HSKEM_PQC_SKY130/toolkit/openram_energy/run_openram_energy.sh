#!/usr/bin/env bash
# Simulate the transistor netlist of one or more OpenRAM SKY130 macros in ngspice (KLU) and report the energy
# of every clock cycle (openram_energy.py). One process per macro, in parallel.
#   usage: run_openram_energy.sh <work dir> <netlist.sp[.gz]> [<netlist> ...]
# The subcircuit name is taken from the file name (<macro>.sp, <macro>.sp.gz or <macro>.lvs.sp); a flat layout
# extraction of a macro is given as MACRO=<name> run_openram_energy.sh <work dir> <flat.spice>.
# Environment: PDK_LIB (sky130.lib.spice), NGSPICE (ngspice 41 or later with KLU), and the SRAM_ENERGY_* variables
# of openram_energy.py (clock period, idle cycles, accesses, read mode, tolerance).
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PDK_LIB="${PDK_LIB:-${PDK_ROOT:-/opt/eda/pdks-openram}/sky130A/libs.tech/ngspice/sky130.lib.spice}"
NGSPICE="${NGSPICE:-ngspice}"
W="${1:?work dir}"; shift
# the SKY130 models set scale=1u: device sizes become unitless microns (OpenRAM writes junction areas with a
# 'u' or 'p' suffix, both meaning square microns)
UNITS='/^[Xx]/ s/\b(ad|as|AD|AS)=([0-9.]+)[pu]/\1=\2/g; /^[Xx]/ s/\b(pd|ps|w|l|PD|PS|W|L)=([0-9.]+)u/\1=\2/g'
for SRC in "$@"; do
  M="${MACRO:-$(basename "$SRC" | sed -E 's/(\.lvs)?\.sp(\.gz)?$//')}"
  (
    mkdir -p "$W/$M" && cd "$W/$M" || exit 1
    echo "set ngbehavior=hsa" > .spiceinit
    { case "$SRC" in *.gz) gzip -dc "$SRC";; *) cat "$SRC";; esac; } | sed -E "$UNITS" > netlist_units.sp
    python3 "$HERE/openram_energy.py" netlist_units.sp "$M" energy.sp "$PDK_LIB"
    "$NGSPICE" -b energy.sp > energy.log 2>&1
    python3 "$HERE/openram_energy.py" --parse energy.log "$M" energy.json
  ) &
done
wait
