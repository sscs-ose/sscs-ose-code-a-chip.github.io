#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/lint.sh
# Type: Script: Verilator lint of the whole design, all warnings on
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/.."
RTL=$(grep -v '^//' src/files.f | tr '\n' ' ')
verilator --lint-only -Wall --top-module tt_um_vertrex_star_proem lint/waivers.vlt $RTL
echo "lint clean: verilator -Wall, $(grep -c lint_off lint/waivers.vlt) reviewed waivers"
