#!/usr/bin/env bash
# Power of the routed chip's logic over one ML-KEM decapsulation (typical corner, 25 MHz).
#   1. scripts/shadow_netlist.py turns the routed netlist into a 'shadow' whose flip-flop outputs and SRAM
#      read data follow the RTL simulation; references to registers the testbench configuration lacks are
#      found by compiling and tied to a constant (a handful);
#   2. the full-system RTL testbench runs in its ASIC configuration with the shadow next to it, and
#      tb/decaps_vcd_window.sv (DUMP_SHADOW) records a VCD of the shadow over the first profiled
#      decapsulation, so every combinational net switches exactly as the routed logic would without
#      glitches (zero delay);
#   3. OpenROAD annotates that activity on the routed database with its extracted parasitics. The
#      shadow's clock is held constant; the clock network and the registers' clock pins are taken from
#      OpenSTA's clock analysis, which needs no activity.
# The SRAM macros are not part of this figure: their Liberty power views are not physical (notebook, Section 8);
# see scripts/sram_energy_spice.sh and scripts/sram_energy_model.py. The layout database is not published,
# so this needs the private run directory (like sta_corners_fullchip.sh); only the summary,
# results/fullchip/power.json, is published.
# usage: FULLCHIP_DIR=<ORFS results dir> MACRO_LIB_DIR=<eight *.physical.lib> scripts/fullchip_power.sh
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
W="${FULLCHIP_POWER_WORK:-$HOME/fullchip_power}"; mkdir -p "$W"         # netlist-derived files stay private
SRC="$ROOT/hskem_rtl"
F=$(sed -n '/^F=(/,/)$/p' "$ROOT/scripts/run_system_sim.sh" | tr -d '()"' | sed 's/^F=//; s#\${CAC_TB:-sim/tb/tb_trustedge_spi.sv}#sim/tb/tb_trustedge_spi.sv#')
DEFS="-DFUNCTIONAL -DUNIT_DELAY=#0 -DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_KECCAK_SERIAL_ROUND -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS"
gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/primitives.v.gz" > "$W/primitives.v"
# the testbench models two library cells itself: the shadow uses renamed copies of the library's
gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/sky130_fd_sc_hd.v.gz" | \
  sed -E 's/\bmodule sky130_fd_sc_hd__(and2_1|inv_1)\b/module shadow_sky130_\1/' > "$W/sky130_shadow_lib.v"
: > "$W/shadow_skip.txt"
for round in 1 2 3; do
  python3 "$ROOT/scripts/shadow_netlist.py" "$B/6_final.v" "$W/shadow.v" "$W/shadow_skip.txt"
  (cd "$SRC" && iverilog -g2012 -I rtl/kyber $DEFS -DDUMP_SHADOW -s tb_trustedge_spi -s shadow_chip -s decaps_vcd_window \
     -o "$W/shadow.vvp" $F "$W/primitives.v" "$W/sky130_shadow_lib.v" "$W/shadow.v" "$ROOT/tb/decaps_vcd_window.sv") \
     > "$W/compile.log" 2>&1 && break
  python3 - "$W/compile.log" "$W/shadow_skip.txt" <<'PY'
import re, sys
log, skip = sys.argv[1], sys.argv[2]
new = {"u_common." + re.sub(r"\['sd(\d+)\]", r"[\1]", m) for m in
       re.findall(r"Unable to bind wire/reg/memory `tb_trustedge_spi\.dut\.([^`]+)'", open(log).read())}
old = set(open(skip).read().split())
open(skip, "w").write("\n".join(sorted(old | new)) + "\n"); print("unresolved references tied off:", len(new))
PY
done
(cd "$ROOT/results/system_sim" && vvp -n "$W/shadow.vvp" +skip=1 +vcd="$W/shadow.vcd" > "$W/sim.log" 2>&1)
grep "DECAPS_VCD" "$W/sim.log"
python3 "$ROOT/scripts/vcd_shift.py" "$W/shadow.vcd" "$W/shadow0.vcd" && rm -f "$W/shadow.vcd"
cat > "$W/power.tcl" <<TCL
read_liberty $ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
foreach lib [glob $M/*.physical.lib] { read_liberty \$lib }
read_db $B/6_final.odb
read_sdc $B/6_final.sdc
read_spef $B/6_final.spef
set_propagated_clock [all_clocks]
read_vcd -scope shadow_chip $W/shadow0.vcd
report_activity_annotation
report_power -digits 6
TCL
"$ORFS/tools/install/OpenROAD/bin/openroad" -no_splash -exit "$W/power.tcl" > "$W/power.log" 2>&1
python3 - "$W" "$ROOT/results/fullchip/power.json" "$B/6_final.sdc" <<'PY'
import json, re, sys, pathlib
w, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
log, sim = (w / "power.log").read_text(), (w / "sim.log").read_text()
skip = (w / "shadow_skip.txt").read_text().split()
clk = float(re.search(r"-period ([0-9.]+)", pathlib.Path(sys.argv[3]).read_text())[1])
cycles = int(re.search(r"cycles_in_window=(\d+)", sim)[1])
grp = {m[0].lower(): [float(x) for x in m[1:5]] for m in
       re.findall(r"^(Sequential|Combinational|Clock|Macro)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)", log, re.M)}
vcd_pins = int(re.search(r"^vcd\s+(\d+)", log, re.M)[1]); unann = int(re.search(r"^unannotated\s+(\d+)", log, re.M)[1])
logic = {g: grp[g][3] for g in ("sequential", "combinational", "clock")}
res = {"window": "the first of the three profiled decapsulations (Section 8), ASIC configuration, from its second busy cycle",
       "window_cycles": cycles, "clock_ns": clk, "corner": "tt_025C_1v80",
       "pins_annotated_from_vcd": vcd_pins, "pins_unannotated": unann, "register_references_tied_off": len(skip),
       "power_mw": {g: v * 1e3 for g, v in logic.items()}, "logic_power_mw": sum(logic.values()) * 1e3,
       "logic_energy_per_decaps_uj": sum(logic.values()) * cycles * clk * 1e-9 * 1e6,
       "method": "zero-delay activity of the routed logic from a shadow of the netlist driven by the RTL simulation "
                 "(scripts/shadow_netlist.py); clock network and register clock pins from OpenSTA's clock analysis; "
                 "SRAM macros excluded (their Liberty power views are not physical)"}
out.write_text(json.dumps(res, indent=2) + "\n"); print(json.dumps(res, indent=2))
PY
