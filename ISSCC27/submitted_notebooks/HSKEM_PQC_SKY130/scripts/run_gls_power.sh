#!/usr/bin/env bash
# Gate-level simulation of a routed NTT netlist and activity-based power.
#   1. simulate results of ORFS (6_final.v) with the SKY130 functional cell
#      models against the golden vectors (bit-exact check);
#   2. record a VCD over exactly one forward NTT of a random polynomial;
#   3. annotate that activity with the extracted parasitics in OpenROAD and
#      report power; energy per transform = power x cycles x clock period.
# A macro-store point instantiates the OpenRAM macro, whose Liberty power is not physical: its group is
# left out of the power, and the macro's cycles in the window, counted from the VCD, are priced with the
# transistor-level energies of results/fullchip/sram_energy.json instead.
# usage: run_gls_power.sh <run, e.g. ntt_sp_20ns>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
RUN=${1:?run}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
PDK="${SKY130_HD:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd | head -1)}"
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
B="${CAC_WORK:-$HOME/cac_runs}/$RUN/results/sky130hd/cac_$RUN/base"
# CAC_VEC_SEED / CAC_POWER_TAG: another random input, recorded in a separate folder (defaults reproduce the committed run)
OUT="$ROOT/results/gls_power/$RUN${CAC_POWER_TAG:-}"; mkdir -p "$OUT"
TOP=$(grep -m1 -oE "^module [A-Za-z0-9_]+" "$B/6_final.v" | cut -d' ' -f2)
CLK_NS=$(grep -m1 -oE "create_clock.*-period [0-9.]+" "$B/6_final.sdc" | grep -oE "[0-9.]+$")
HALF=$(python3 -c "print($CLK_NS/2)")
MACRO=""; grep -q "sky130_sram_1rw_16x256_wpr8 " "$B/6_final.v" && MACRO=sky130_sram_1rw_16x256_wpr8
grep -q "sky130_sram_1rw_24x128 " "$B/6_final.v" && MACRO=sky130_sram_1rw_24x128

if [ "${SKIP_GLS:-0}" = 1 ] && [ -f "$OUT/ntt_fwd.vcd.gz" ]; then
  gunzip -kf "$OUT/ntt_fwd.vcd.gz"          # reuse the recorded activity; only redo the power step
else
VEC="$OUT/vectors"; mkdir -p "$VEC"
(cd "$ROOT/golden" && python3 gen_vectors.py --seed "${CAC_VEC_SEED:-2027}" --out "$VEC" --ntt 1 --keccak 1 > /dev/null)
DEFS=(-DFUNCTIONAL -DUNIT_DELAY=#1 -DCLK_HALF=$HALF -DVCD_VEC=4 "-DVCD_OUT=\"$OUT/ntt_fwd.vcd\"")
[ "$TOP" = kyber_ntt_engine_packed2 ] && DEFS+=(-DGLS_PAIR_PORTS)   # its pair and stream ports, tied off
if [ "$TOP" != kyber_ntt_engine ]; then     # netlists of other tops keep the port list; alias the module name
  sed "s/^module $TOP /module kyber_ntt_engine /" "$B/6_final.v" > "$OUT/netlist.v"
else
  cp "$B/6_final.v" "$OUT/netlist.v"
fi
# Icarus rejects text after `endif, which the SKY130 cell models use as a comment;
# a cleaned temporary copy is compiled instead (the PDK itself is left untouched).
MODELS="$(mktemp -d)"
for f in primitives.v sky130_fd_sc_hd.v; do
  sed -E 's/^([[:space:]]*`endif)[[:space:]]+[^/[:space:]].*$/\1/' "$PDK/verilog/$f" > "$MODELS/$f"
done
SRAM_MODEL=()
if [ -n "$MACRO" ]; then      # OpenRAM's behavioural model; its dout0 is valid 3 ns after the falling edge
  sed "s/parameter VERBOSE = 1/parameter VERBOSE = 0/" "$ROOT/flow/macros/$MACRO.v" > "$MODELS/sram_model.v"
  SRAM_MODEL=("$MODELS/sram_model.v"); DEFS+=(-DRD_SAMPLE_DELAY=5)
fi
cd "$VEC"
iverilog -g2012 -I . "${DEFS[@]}" -o "$OUT/gls.vvp" \
    "$MODELS/primitives.v" "$MODELS/sky130_fd_sc_hd.v" "${SRAM_MODEL[@]}" "$OUT/netlist.v" "$ROOT/tb/tb_ntt.sv" > "$OUT/compile.log" 2>&1 \
  || { grep -v -i warning "$OUT/compile.log" | head -20; exit 1; }
vvp -n "$OUT/gls.vvp" > "$OUT/gls.log"
rm -rf "$OUT/gls.vvp" "$OUT/netlist.v" "$MODELS" "$VEC"
grep -E "NTT_RESULT|PASS|FAIL|MISMATCH" "$OUT/gls.log" | head -5
fi

# OpenSTA reads no $dumpon/$dumpoff blocks: cut the file to the recorded window first. The power step
# works in a local temporary directory (OpenROAD can stall on files of a mounted Windows drive under WSL).
PW="$(mktemp -d)"; cd "$PW"     # a local working directory: the simulation directory has been removed
python3 "$ROOT/scripts/vcd_window.py" "$OUT/ntt_fwd.vcd" "$PW/window.vcd"
cp "$ROOT/flow/power_vcd.tcl" "$PW/"
[ -n "$MACRO" ] && cp "$ROOT/flow/macros/${MACRO}_TT_1p8V_25C.lib" "$PW/macro.lib" && export LIB_MACRO="$PW/macro.lib"
# the routed database carries the antenna diodes that the SPEF refers to (flow/power_vcd.tcl)
LIB="$ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib" ODB="$B/6_final.odb" \
SDC="$B/6_final.sdc" SPEF="$B/6_final.spef" VCD="$PW/window.vcd" SCOPE="tb_ntt/dut" \
  "$ORFS/tools/install/OpenROAD/bin/openroad" -no_splash -exit "$PW/power_vcd.tcl" > "$PW/power.log" 2>&1 || true
cp "$PW/power.log" "$OUT/power.log"
[ -n "$MACRO" ] && python3 "$ROOT/scripts/vcd_macro_accesses.py" "$PW/window.vcd" u_macro "$OUT/macro_accesses.json"
rm -rf "$PW"; gzip -f "$OUT/ntt_fwd.vcd"
python3 - "$OUT" "$CLK_NS" "$ROOT" "$MACRO" <<'PY'
import json, re, sys, pathlib
out, clk, root, macro = pathlib.Path(sys.argv[1]), float(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4]
g = (out / "gls.log").read_text(); p = (out / "power.log").read_text()
m = re.search(r"cycles_fwd=(\d+)", g)
# report_power: "Total  <internal> <switching> <leakage> <total>  100.0%" in watts
w = re.search(r"^Total\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", p, re.M)
res = {"gls_pass": "PASS" in g and "FAIL" not in g, "cycles_fwd": int(m[1]) if m else None,
       "clock_ns": clk, "total_power_w": float(w[4]) if w else None,
       "internal_w": float(w[1]) if w else None, "switching_w": float(w[2]) if w else None,
       "leakage_w": float(w[3]) if w else None,
       "activity_source": "gate-level VCD of one forward NTT of a random polynomial"}
if res["total_power_w"] and res["cycles_fwd"]:
    res["energy_per_forward_ntt_nj"] = res["total_power_w"] * res["cycles_fwd"] * clk * 1e-9 * 1e9
if macro and res["total_power_w"]:
    # the standard cells' power is the sum of the other groups: OpenRAM's analytical power view of the
    # macro reports megawatts, so subtracting it from the total would lose the logic to rounding
    grp = {k: [float(x) for x in v] for k, *v in re.findall(
        r"^(Sequential|Combinational|Clock|Macro|Pad)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", p, re.M)}
    acc = json.loads((out / "macro_accesses.json").read_text())
    e = json.loads((root / "results/fullchip/sram_energy.json").read_text())["masters"][macro]
    res["macro_liberty_power_w"] = grp["Macro"][3]        # OpenRAM's analytical power view: not used
    cells = [v for k, v in grp.items() if k != "Macro"]
    res["internal_w"], res["switching_w"], res["leakage_w"], res["total_power_w"] = (sum(c[i] for c in cells) for i in range(4))
    res["logic_power_w"] = res["total_power_w"]
    res["logic_energy_per_forward_ntt_nj"] = res["logic_power_w"] * res["cycles_fwd"] * clk
    res["macro_accesses"] = acc
    res["macro_energy_nj"] = 1e-3 * (acc["writes"] * e["write_pj"] + acc["reads_new_address"] * e["read_pj"]
                                     + acc["reads_same_address"] * e["read_repeat_pj"] + acc["idle"] * e["idle_pj"])
    res["energy_per_forward_ntt_nj"] = res["logic_energy_per_forward_ntt_nj"] + res["macro_energy_nj"]
    res["macro_energy_source"] = "transistor-level energies of results/fullchip/sram_energy.json"
(out / "summary.json").write_text(json.dumps(res, indent=2)); print(res)
PY
