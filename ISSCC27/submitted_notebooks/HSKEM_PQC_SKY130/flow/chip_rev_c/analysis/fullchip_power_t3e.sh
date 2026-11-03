#!/usr/bin/env bash
# Logic power of the HSKEM-2 rev B (t3e w1) final over one ML-KEM decapsulation (typical corner, 25 MHz), with the
# method of codeachip/scripts/fullchip_power.sh (shadow of the routed netlist driven by the RTL system
# simulation, zero-delay activity annotated on the routed database with its extracted parasitics). Changes
# for chip v2:
#   * RTL: the public sources (codeachip/hskem_rtl) through the generator that built chip v2
#     (codeachip/scripts/make_packed_system.py), never a private source tree (only the public placeholder credential);
#     register names are the same, only key constants differ, and the shadow follows the RTL registers;
#   * configuration: the chip's choices, i.e. the SRAM store with the one-round Keccak (the notebook's
#     sram_only configuration, 6,856 cycles per decapsulation) and the chip's further defines (streamed
#     system "H" set, PMAC_RETIME, SO_PIPE);
#   * outputs: work files on drive C, power.json into chip_v2/signoff/fullchip_stage.
# usage: fullchip_power_v2.sh [compile|sim|power|run]   compile: build only; sim: build and simulate (VCD);
#        power: OpenROAD power from an existing VCD; run (default): everything
set -uo pipefail
readonly MODE="${1:-run}"
readonly ROOT=/mnt/d/TKVM_ATTT_2026_test CAC=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3
readonly ORFS=/opt/eda/orfs-6101364b
readonly B=/root/t3/t3e_final_w1/results
readonly M="${ROOT}/report/a2_macro_link_smoke/run.rjfysF/derived_liberty"
readonly W=/mnt/c/chipv2_signoff/power_t3e STAGE="${ROOT}/chip_v2/signoff/fullchip_stage_t3e"
mkdir -p "${W}" "${STAGE}"
# the iverilog of the notebook's system simulations (oss-cad-suite): the distribution's older iverilog
# cannot resolve kyber_pkg functions inside the PMAC_RETIME code
# (rev B) system iverilog: the GLS source copy calls kyber_pkg::kyber_zeta explicitly (SOURCE_EDITS.txt)
iverilog -V 2>&1 | head -1
# the packed system exactly as run_system_sim.sh builds it (CAC_PACKED_SYSTEM=1)
SRC="${W}/hskem_rtl"
if [[ ! -d "${SRC}" ]]; then
  cp -r /root/real_gls_t3e/hskem_rtl "${SRC}"   # (rev B) the synthesized root build_t3e/root + kyber_zeta qualification
fi
H="-DTRUSTEDGE_PACKED_NTT -DTRUSTEDGE_HASH_OVERLAP -DTRUSTEDGE_STREAM_IO"
H="$H -DTRUSTEDGE_FAST_BASEMUL -DTRUSTEDGE_FAST_FEED -DTRUSTEDGE_STREAM_OUT -DTRUSTEDGE_FOLD_READBACK"
H="$H -DTRUSTEDGE_PREFETCH -DTRUSTEDGE_TIGHT_LOOPS -DTRUSTEDGE_FAST_CHECK -DTRUSTEDGE_FAST_Y"
H="$H -DTRUSTEDGE_PACKED2 -DTRUSTEDGE_FAST_PRF -DTRUSTEDGE_FUSED_CMP -DTRUSTEDGE_FAST_READ"
H="$H -DTRUSTEDGE_PIPE_CHECK -DTRUSTEDGE_PAIR_PORT -DTRUSTEDGE_DEFER_J -DTRUSTEDGE_PIPE_MAC -DTRUSTEDGE_FAST_HASH"
H="$H -DTRUSTEDGE_DEC_STREAM -DTRUSTEDGE_SEG_CHECK -DTRUSTEDGE_BG_PRF -DTRUSTEDGE_STREAM_INV -DTRUSTEDGE_STREAM_FWD"
H="$H -DTRUSTEDGE_PRF_TO_NTT -DTRUSTEDGE_STREAM_DEC_INV -DTRUSTEDGE_PRF_FINE_HOLD -DTRUSTEDGE_POLY_GUARD"
DEFS="-DFUNCTIONAL -DUNIT_DELAY=#0 -DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS"
DEFS="$DEFS $H -DTRUSTEDGE_PMAC_RETIME -DTRUSTEDGE_SO_PIPE"
for d in MAC_DEEP MM_PIPE CRC_SERIAL BARRETT_1C SA_PIPE PMAC_RAW CODEC_RETIME MSG_PIPE PP_EARLY LOAD_PIPE MARGIN MUL_SEL SEL_REP EK_PREF; do DEFS="$DEFS -DTRUSTEDGE_T3_$d"; done   # (rev B) the 14 tier-3 defines
F=$(sed -n '/^F=(/,/)$/p' "${CAC}/scripts/run_system_sim.sh" | tr -d '()"' | sed 's/^F=//; s#\${CAC_TB:-sim/tb/tb_trustedge_spi.sv}#sim/tb/tb_trustedge_spi.sv#')
F="$F rtl/kyber/barrett_reduce_1c.v rtl/kyber/kyber_ntt_engine_packed.sv rtl/kyber/kyber_ntt_engine_packed2.sv"
gunzip -c "${CAC}/third_party/sky130_fd_sc_hd/primitives.v.gz" > "${W}/primitives.v"
gunzip -c "${CAC}/third_party/sky130_fd_sc_hd/sky130_fd_sc_hd.v.gz" | \
  sed -E 's/\bmodule sky130_fd_sc_hd__(and2_1|inv_1)\b/module shadow_sky130_\1/' > "${W}/sky130_shadow_lib.v"
[[ -f "${W}/shadow_skip.txt" ]] || cp /root/real_gls_t3e/shadow_skip.txt "${W}/shadow_skip.txt"   # (rev B) FSM-recode skip list by instance name
ok=0
for round in 1 2 3 4; do
  python3 "${CAC}/scripts/shadow_netlist.py" "${B}/6_final.v" "${W}/shadow.v" "${W}/shadow_skip.txt" self | tee "${W}/shadow_gen.log"
  if (cd "${SRC}" && iverilog -g2012 -I rtl/kyber ${DEFS} -DDUMP_SHADOW -s tb_trustedge_spi -s shadow_chip \
        -s decaps_vcd_window -o "${W}/shadow.vvp" ${F} "${W}/primitives.v" "${W}/sky130_shadow_lib.v" \
        "${W}/shadow.v" "${CAC}/tb/decaps_vcd_window.sv") > "${W}/compile.log" 2>&1; then ok=1; break; fi
  python3 - "${W}/compile.log" "${W}/shadow_skip.txt" <<'PY'
import re, sys
log, skip = sys.argv[1], sys.argv[2]
text = open(log).read()
refs = re.findall(r"Unable to bind wire/reg/memory `tb_trustedge_spi\.dut\.([^`]+)'", text)
# registers of a two-dimensional RTL array that synthesis flattened to one index (u_shared_ntt.valid[k])
refs += re.findall(r"Unable to elaborate r-value: tb_trustedge_spi\.dut\.(\S+)", text)
new = {"u_common." + re.sub(r"\['sd(\d+)\]", r"[\1]", m) for m in refs}
old = set(open(skip).read().split())
open(skip, "w").write("\n".join(sorted(old | new)) + "\n"); print("round: unresolved references tied off:", len(new))
PY
done
[[ ${ok} == 1 ]] || { echo "POWER_COMPILE=FAIL (see ${W}/compile.log)"; tail -20 "${W}/compile.log"; exit 2; }
echo "POWER_COMPILE=PASS tied_off=$(wc -l < "${W}/shadow_skip.txt")"
[[ "${MODE}" == compile ]] && exit 0
if [[ "${MODE}" != power ]]; then
  echo "POWER_SIM_START $(date -Is)"
  (cd "${CAC}/results/system_sim" && vvp -n "${W}/shadow.vvp" +skip=1 +vcd="${W}/shadow.vcd" > "${W}/sim.log" 2>&1)
  grep "DECAPS_VCD" "${W}/sim.log"
  # (rev B, fixed 18/10) stretch the testbench's 10 ns clock to the chip's 40 ns clock as fullchip_power.sh does;
  # the first rev B run omitted the factor and priced the data-dependent power at four times the clock rate
  CLK_NS=$(grep -m1 -oE "create_clock.*-period [0-9.]+" "${B}/6_final.sdc" | grep -oE "[0-9.]+$")
  TB_NS=$(grep -m1 -oE "always #[0-9]+ clk" "${SRC}/sim/tb/tb_trustedge_spi.sv" | grep -oE "[0-9]+" | head -1)
  K=$(python3 -c "k = $CLK_NS / (2 * $TB_NS); assert k == int(k), k; print(int(k))")
  python3 "${CAC}/scripts/vcd_shift.py" "${W}/shadow.vcd" "${W}/shadow0.vcd" "${K}" && rm -f "${W}/shadow.vcd"
  echo "POWER_SIM_DONE $(date -Is) $(ls -la "${W}/shadow0.vcd")"
fi
python3 "${CAC}/scripts/shadow_toggles.py" "${B}/6_final.v" "${W}/shadow0.vcd" "${STAGE}/register_toggles.json" "${W}/toggles_by_block.json"
[[ "${MODE}" == sim ]] && exit 0
cat > "${W}/power.tcl" <<TCL
read_liberty ${ORFS}/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
foreach lib [glob ${M}/*.physical.lib] { read_liberty \$lib }
read_db ${B}/6_final.odb
read_sdc ${B}/6_final.sdc
read_spef ${B}/6_final.spef
set_propagated_clock [all_clocks]
read_vcd -scope shadow_chip ${W}/shadow0.vcd
report_activity_annotation
report_power -digits 6
# inputs of scripts/clock_gating_whatif.py: per-instance power of every flip-flop and clock buffer, and the
# instances each clock buffer drives
set insts {}
foreach c [all_registers -cells] { if {![string match "sky130_sram*" [get_property \$c ref_name]]} { lappend insts \$c } }
foreach c [get_cells *] { if {[string match "sky130_fd_sc_hd__clkbuf*" [get_property \$c ref_name]]} { lappend insts \$c } }
report_power -instances \$insts -digits 9 > ${W}/flop_clk_power.txt
set fh [open ${W}/clkbuf_loads.tsv w]
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
"${ORFS}/tools/install/OpenROAD/bin/openroad" -no_splash -exit "${W}/power.tcl" > "${W}/power.log" 2>&1
python3 - "${W}" "${STAGE}/power.json" "${B}/6_final.sdc" <<'PY'
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
res = {"chip": "HSKEM-2 rev B sign-off final (t3e w1)",
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
python3 "${CAC}/scripts/clock_gating_whatif.py" "${W}/flop_clk_power.txt" "${W}/clkbuf_loads.tsv" \
  "${W}/toggles_by_block.json" "${STAGE}/clock_gating_whatif.json" | head -20
