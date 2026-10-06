#!/usr/bin/env bash
# Power of the routed chip's logic over one ML-KEM decapsulation (typical corner, 25 MHz).
#   1. scripts/make_packed_system.py builds the chip's RTL (the streamed system, Section 8) from hskem_rtl/;
#   2. scripts/shadow_netlist.py turns the routed netlist into a 'shadow' whose flip-flop outputs and SRAM
#      read data follow the RTL simulation; the few registers the RTL cannot name ("self" mode) are
#      simulated in the shadow itself from their own D inputs;
#   3. the full-system RTL testbench runs in the chip's configuration (SRAM store, one-round Keccak, the
#      streamed-system defines) with the shadow next to it, and tb/decaps_vcd_window.sv (DUMP_SHADOW)
#      records a VCD of the shadow over the first profiled decapsulation, so every combinational net switches
#      exactly as the routed logic would without glitches (zero delay);
#   4. OpenROAD annotates that activity on the routed database with its extracted parasitics. The shadow's
#      clock is held constant; the clock network and the registers' clock pins are taken from OpenSTA's
#      clock analysis, which needs no activity;
#   5. scripts/shadow_toggles.py counts the register toggles in the VCD, and scripts/clock_gating_whatif.py
#      projects what gating the clock of the idle blocks would save.
# The SRAM macros are not part of this figure: their Liberty power views are not physical (notebook, Section 8);
# see scripts/sram_energy_spice.sh and scripts/sram_energy_model.py. The layout database is not published,
# so this needs the private run directory (like sta_corners_fullchip.sh); only the summaries in
# results/fullchip/ (power.json, register_toggles.json, clock_gating_whatif.json) are published.
# The Icarus Verilog of the OSS CAD Suite is needed (older distribution builds cannot elaborate kyber_pkg
# functions inside the retimed multiply-accumulate).
# usage: FULLCHIP_DIR=<ORFS results dir> MACRO_LIB_DIR=<seven *.physical.lib> scripts/fullchip_power.sh
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
B="${FULLCHIP_DIR:?FULLCHIP_DIR}"; M="${MACRO_LIB_DIR:?MACRO_LIB_DIR}"
W="${FULLCHIP_POWER_WORK:-$HOME/fullchip_power}"; mkdir -p "$W"         # netlist-derived files stay private
OUT="${FULLCHIP_OUT:-$ROOT/results/fullchip}"
SRC="$W/hskem_rtl"
[[ -d "$SRC" ]] || python3 "$ROOT/scripts/make_packed_system.py" "$ROOT/hskem_rtl" "$SRC" "$ROOT/rtl" "$W/packed_system.diff"
H="-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP -DTRUSTEDGE_STREAM_IO"
H="$H -DTRUSTEDGE_FAST_BASEMUL -DTRUSTEDGE_FAST_FEED -DTRUSTEDGE_STREAM_OUT -DTRUSTEDGE_FOLD_READBACK"
H="$H -DTRUSTEDGE_PREFETCH -DTRUSTEDGE_TIGHT_LOOPS -DTRUSTEDGE_FAST_CHECK -DTRUSTEDGE_FAST_Y"
H="$H -DTRUSTEDGE_PACKED2 -DTRUSTEDGE_FAST_PRF -DTRUSTEDGE_FUSED_CMP -DTRUSTEDGE_FAST_READ"
H="$H -DTRUSTEDGE_PIPE_CHECK -DTRUSTEDGE_PAIR_PORT -DTRUSTEDGE_DEFER_J -DTRUSTEDGE_PIPE_MAC -DTRUSTEDGE_FAST_HASH"
H="$H -DTRUSTEDGE_DEC_STREAM -DTRUSTEDGE_SEG_CHECK -DTRUSTEDGE_BG_PRF -DTRUSTEDGE_STREAM_INV -DTRUSTEDGE_STREAM_FWD"
H="$H -DTRUSTEDGE_PRF_TO_NTT -DTRUSTEDGE_STREAM_DEC_INV -DTRUSTEDGE_PRF_FINE_HOLD -DTRUSTEDGE_POLY_GUARD"
DEFS="-DFUNCTIONAL -DUNIT_DELAY=#0 -DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS"
DEFS="$DEFS $H -DTRUSTEDGE_PMAC_RETIME -DTRUSTEDGE_SO_PIPE"
F=$(sed -n '/^F=(/,/)$/p' "$ROOT/scripts/run_system_sim.sh" | tr -d '()"' | sed 's/^F=//; s#\${CAC_TB:-sim/tb/tb_trustedge_spi.sv}#sim/tb/tb_trustedge_spi.sv#')
F="$F rtl/kyber/barrett_reduce_1c.v rtl/kyber/kyber_ntt_engine_packed.sv rtl/kyber/kyber_ntt_engine_packed2.sv"
gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/primitives.v.gz" > "$W/primitives.v"
# the testbench models two library cells itself: the shadow uses renamed copies of the library's
gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/sky130_fd_sc_hd.v.gz" | \
  sed -E 's/\bmodule sky130_fd_sc_hd__(and2_1|inv_1)\b/module shadow_sky130_\1/' > "$W/sky130_shadow_lib.v"
: > "$W/shadow_skip.txt"
ok=0
for round in 1 2 3 4; do
  python3 "$ROOT/scripts/shadow_netlist.py" "$B/6_final.v" "$W/shadow.v" "$W/shadow_skip.txt" self | tee "$W/shadow_gen.log"
  if (cd "$SRC" && iverilog -g2012 -I rtl/kyber $DEFS -DDUMP_SHADOW -s tb_trustedge_spi -s shadow_chip -s decaps_vcd_window \
        -o "$W/shadow.vvp" $F "$W/primitives.v" "$W/sky130_shadow_lib.v" "$W/shadow.v" "$ROOT/tb/decaps_vcd_window.sv") \
        > "$W/compile.log" 2>&1; then ok=1; break; fi
  python3 - "$W/compile.log" "$W/shadow_skip.txt" <<'PY'
import re, sys
log, skip = sys.argv[1], sys.argv[2]
text = open(log).read()
refs = re.findall(r"Unable to bind wire/reg/memory `tb_trustedge_spi\.dut\.([^`]+)'", text)
# registers of a two-dimensional RTL array that synthesis flattened to one index (u_shared_ntt.valid[k])
refs += re.findall(r"Unable to elaborate r-value: tb_trustedge_spi\.dut\.(\S+)", text)
new = {"u_common." + re.sub(r"\['sd(\d+)\]", r"[\1]", m) for m in refs}
old = set(open(skip).read().split())
open(skip, "w").write("\n".join(sorted(old | new)) + "\n"); print("references simulated in the shadow:", len(new))
PY
done
(( ok )) || { echo "shadow compile failed, see $W/compile.log"; exit 2; }
(cd "$ROOT/results/system_sim" && vvp -n "$W/shadow.vvp" +skip=1 +vcd="$W/shadow.vcd" > "$W/sim.log" 2>&1)
grep "DECAPS_VCD" "$W/sim.log"
python3 "$ROOT/scripts/vcd_shift.py" "$W/shadow.vcd" "$W/shadow0.vcd" && rm -f "$W/shadow.vcd"
python3 "$ROOT/scripts/shadow_toggles.py" "$B/6_final.v" "$W/shadow0.vcd" "$OUT/register_toggles.json" "$W/toggles_by_block.json"
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
# inputs of scripts/clock_gating_whatif.py: per-instance power of every flip-flop (without the SRAM macros)
# and clock buffer, and the instances each clock buffer drives
set insts {}
foreach c [all_registers -cells] { if {![string match "sky130_sram*" [get_property \$c ref_name]]} { lappend insts \$c } }
foreach c [get_cells *] { if {[string match "sky130_fd_sc_hd__clkbuf*" [get_property \$c ref_name]]} { lappend insts \$c } }
report_power -instances \$insts -digits 9 > $W/flop_clk_power.txt
set fh [open $W/clkbuf_loads.tsv w]
foreach inst [[ord::get_db_block] getInsts] {
  if {![string match "sky130_fd_sc_hd__clkbuf*" [[\$inst getMaster] getName]]} continue
  set loads {}
  foreach it [\$inst getITerms] {
    if {![\$it isOutputSignal] || [\$it getNet] eq "NULL"} continue
    foreach l [[\$it getNet] getITerms] { if {\$l ne \$it} { lappend loads [[\$l getInst] getName] } }
  }
  puts \$fh "[\$inst getName]\t[join \$loads { }]"
}
close \$fh
TCL
"$ORFS/tools/install/OpenROAD/bin/openroad" -no_splash -exit "$W/power.tcl" > "$W/power.log" 2>&1
python3 - "$W" "$OUT/power.json" "$B/6_final.sdc" <<'PY'
import json, re, sys, pathlib
w, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
log, sim = (w / "power.log").read_text(), (w / "sim.log").read_text()
skip = (w / "shadow_skip.txt").read_text().split()
n_self = int(re.search(r"simulated in the shadow (\d+)", (w / "shadow_gen.log").read_text())[1])
clk = float(re.search(r"-period ([0-9.]+)", pathlib.Path(sys.argv[3]).read_text())[1])
cycles = int(re.search(r"cycles_in_window=(\d+)", sim)[1])
grp = {m[0].lower(): [float(x) for x in m[1:5]] for m in
       re.findall(r"^(Sequential|Combinational|Clock|Macro)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)", log, re.M)}
vcd_pins = int(re.search(r"^vcd\s+(\d+)", log, re.M)[1]); unann = int(re.search(r"^unannotated\s+(\d+)", log, re.M)[1])
logic = {g: grp[g][3] for g in ("sequential", "combinational", "clock")}
res = {"chip": "chip v2 sign-off final (report/orfs_chip_v2_r2_a3grt/final_from_h1r)",
       "window": "the first of the profiled decapsulations, chip configuration (SRAM store, one-round Keccak, "
                 "streamed system), from its second busy cycle",
       "window_cycles": cycles, "clock_ns": clk, "corner": "tt_025C_1v80",
       "pins_annotated_from_vcd": vcd_pins, "pins_unannotated": unann,
       "registers_simulated_in_shadow": n_self, "register_references_tied_off": len(skip) - n_self,
       "power_mw": {g: v * 1e3 for g, v in logic.items()}, "logic_power_mw": sum(logic.values()) * 1e3,
       "logic_energy_per_decaps_uj": sum(logic.values()) * cycles * clk * 1e-9 * 1e6,
       "method": "zero-delay activity of the routed logic from a shadow of the netlist driven by the RTL simulation "
                 "(scripts/shadow_netlist.py); clock network and register clock pins from OpenSTA's clock analysis; "
                 "SRAM macros excluded (their Liberty power views are not physical)"}
tog = json.loads((out.parent / "register_toggles.json").read_text())
res["registers_never_toggling"] = tog["never_toggling"]
res["registers_compared"] = tog["flip_flops_in_vcd"]
res["registers_note"] = ("flip-flops of the routed netlist whose output never changes in the window, counted on the "
                         "shadow VCD, which traces every flip-flop (scripts/shadow_toggles.py)")
out.write_text(json.dumps(res, indent=2) + "\n"); print(json.dumps(res, indent=2))
PY
python3 "$ROOT/scripts/clock_gating_whatif.py" "$W/flop_clk_power.txt" "$W/clkbuf_loads.tsv" \
  "$W/toggles_by_block.json" "$OUT/clock_gating_whatif.json"
