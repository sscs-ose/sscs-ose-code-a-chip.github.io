#!/usr/bin/env bash
# Gate-level run of the routed chip netlist over one ML-KEM decapsulation, next to the RTL testbench and the shadow.
#   1. builds the chip's RTL and the shadow exactly as fullchip_power.sh does;
#   2. scripts/real_netlist.py builds real_chip, the routed netlist with its own flip-flops (rtl/real_ff.v);
#   3. the full-system testbench runs to the start of the window; there tb/real_chip_window.sv loads real_chip's flip-flops
#      with the RTL state, releases its clock and compares it with the shadow at every cycle of the window;
#   4. with VCD=1 the activity of real_chip over the window is written, for OpenSTA (compare with the shadow's).
# The netlist holds the (old) device key logic, so every derived file stays in the private work directory.
# usage: FULLCHIP_DIR=<ORFS results dir> [REAL_GLS_WORK=<dir>] [VCD=1] scripts/real_gls_window.sh
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"
W="${REAL_GLS_WORK:-$HOME/real_gls}"; mkdir -p "$W"
SRC="$W/hskem_rtl"
[[ -d "$SRC" ]] || python3 "$ROOT/scripts/make_packed_system.py" "$ROOT/hskem_rtl" "$SRC" "$ROOT/rtl" "$W/packed_system.diff"
# the defines and the file list of fullchip_power.sh
eval "$(sed -n '/^H="-DTRUSTEDGE_PACKED_NTT/,/^F="\$F rtl\/kyber\/barrett/p' "$ROOT/scripts/fullchip_power.sh")"
gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/primitives.v.gz" > "$W/primitives.v"
gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/sky130_fd_sc_hd.v.gz" | \
  sed -E 's/\bmodule sky130_fd_sc_hd__(and2_1|inv_1)\b/module shadow_sky130_\1/' > "$W/sky130_shadow_lib.v"
[[ -f "$W/shadow_skip.txt" ]] || cp "${SHADOW_SKIP:?no shadow_skip.txt in the work directory: give SHADOW_SKIP=<file of an earlier shadow run>}" "$W/shadow_skip.txt"
DUMP=""; [[ "${VCD:-0}" == 1 ]] && DUMP="+vcd=$W/real.vcd"
for round in 1 2 3 4; do
  python3 "$ROOT/scripts/shadow_netlist.py" "$B/6_final.v" "$W/shadow.v" "$W/shadow_skip.txt" self | tee "$W/shadow_gen.log"
  (cd "$ROOT/scripts" && python3 real_netlist.py "$B/6_final.v" "$W/real.v" "$W/real_flops.txt") | tee "$W/real_gen.log"
  ( cd "$SRC" && iverilog -g2012 -Wselect-range -I rtl/kyber $DEFS -s tb_trustedge_spi -s shadow_chip -s real_chip -s real_chip_window       -o "$W/real.vvp" $F "$W/primitives.v" "$W/sky130_shadow_lib.v" "$W/shadow.v" "$W/real.v" "$ROOT/rtl/real_ff.v"       "$ROOT/tb/real_chip_window.sv" ) > "$W/compile.log" 2>&1 || { echo "compile failed, see $W/compile.log"; exit 2; }
  (( $(python3 "$ROOT/scripts/shadow_oob_skip.py" "$W/compile.log" "$W/shadow.v" "$W/shadow_skip.txt") )) || break
done
echo "compiled $(date +%H:%M)"
(cd "$ROOT/results/system_sim" && /usr/bin/time -v vvp -n "$W/real.vvp" +skip=1 $DUMP ${SIM_ARGS:-} > "$W/sim.log" 2> "$W/sim.time"; grep -E "REAL_CHIP|DECAPS" "$W/sim.log")
grep -E "Elapsed|Maximum resident" "$W/sim.time"
