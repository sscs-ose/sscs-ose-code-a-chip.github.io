#!/usr/bin/env bash
# Gate-level simulation of a routed Keccak block and activity-based energy per
# permutation (the Keccak counterpart of run_gls_power.sh):
#   1. simulate the routed netlist (6_final.v) with the SKY130 functional cell
#      models against the golden states (bit-exact check through the lane wrapper);
#   2. record a VCD over exactly one permutation of a random state;
#   3. annotate that activity with the extracted parasitics in OpenSTA and report
#      power; energy per permutation = power x cycles x clock period.
# usage: run_gls_power_keccak.sh <run, e.g. keccak_r1_20ns>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
RUN=${1:?run}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
B="${CAC_WORK:-$HOME/cac_runs}/$RUN/results/sky130hd/cac_$RUN/base"
# CAC_VEC_SEED / CAC_POWER_TAG: another random input, recorded in a separate folder (defaults reproduce the committed run)
# GLS_DELAY=unit (default, as committed), zero, or sdf (routed delays at tt as inertial delays per cell output,
# scripts/sdf_inertial_netlist.py): plan item 2.1; a non-default mode writes to results/gls_power/<run>_<mode>
GLS_DELAY="${GLS_DELAY:-unit}"; [ "$GLS_DELAY" = unit ] && DTAG="" || DTAG="_$GLS_DELAY"
OUT="$ROOT/results/gls_power/$RUN${CAC_POWER_TAG:-}$DTAG"; mkdir -p "$OUT"; TMP="$(mktemp -d)"
TOP=$(grep -m1 -oE "^module [A-Za-z0-9_]+" "$B/6_final.v" | cut -d' ' -f2)
CLK_NS=$(grep -m1 -oE "create_clock.*-period [0-9.]+" "$B/6_final.sdc" | grep -oE "[0-9.]+$")
HALF=$(python3 -c "print($CLK_NS/2)")
if [ "${SKIP_GLS:-0}" = 1 ] && [ -f "$OUT/keccak_perm.vcd.gz" ]; then
  gunzip -kf "$OUT/keccak_perm.vcd.gz"      # reuse the recorded activity; only redo the power step
  rm -rf "$TMP"
else
NETSRC="$B/6_final.v"; DLY="-DUNIT_DELAY=#1"
if [ "$GLS_DELAY" = zero ]; then DLY="-DUNIT_DELAY="; fi
if [ "$GLS_DELAY" = sdf ]; then
  cat > "$TMP/sdf.tcl" <<TCL
read_liberty $ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db $B/6_final.odb
read_sdc $B/6_final.sdc
read_spef $B/6_final.spef
set_propagated_clock [all_clocks]
write_sdf -divider . -digits 4 $TMP/netlist.sdf
TCL
  "$ORFS/tools/install/OpenROAD/bin/openroad" -no_splash -exit "$TMP/sdf.tcl" > "$OUT/sdf.log" 2>&1
  python3 "$ROOT/scripts/sdf_inertial_netlist.py" "$B/6_final.v" "$TMP/netlist.sdf"     "$ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib" "$TMP/netlist_dly.v" "$OUT/sdf_delays.json"
  NETSRC="$TMP/netlist_dly.v"; DLY="-DUNIT_DELAY="
fi
sed "s/^module $TOP /module keccak_lane_wrapper /" "$NETSRC" > "$TMP/netlist.v"
for f in primitives.v sky130_fd_sc_hd.v; do gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/$f.gz" > "$TMP/$f"; done
(cd "$ROOT/golden" && python3 gen_vectors.py --seed "${CAC_VEC_SEED:-2027}" --out "$TMP" --ntt 1 --keccak 3 > /dev/null)
N=$(grep -oE "N_KECCAK [0-9]+" "$TMP/counts.vh" | cut -d' ' -f2)
cd "$TMP"
iverilog -g2012 -I . -DFUNCTIONAL "$DLY" -DCLK_HALF=$HALF -DVCD_VEC=$((N - 1)) \
    "-DVCD_OUT=\"$OUT/keccak_perm.vcd\"" -o gls.vvp primitives.v sky130_fd_sc_hd.v netlist.v \
    "$ROOT/tb/tb_keccak_lanes.sv" > "$OUT/compile.log" 2>&1 || { grep -v -i warning "$OUT/compile.log" | head; exit 1; }
vvp -n gls.vvp > "$OUT/gls.log"
cd "$ROOT"; rm -rf "$TMP"
grep -E "KECCAK_RESULT|PASS|FAIL|MISMATCH" "$OUT/gls.log" | head -5
fi
python3 "$ROOT/scripts/vcd_window.py" "$OUT/keccak_perm.vcd" "$OUT/keccak_perm_window.vcd"
# the routed database carries the antenna diodes that the SPEF refers to (flow/power_vcd.tcl)
LIB="$ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib" ODB="$B/6_final.odb" \
SDC="$B/6_final.sdc" SPEF="$B/6_final.spef" VCD="$OUT/keccak_perm_window.vcd" SCOPE="tb_keccak_lanes/dut" \
  "$ORFS/tools/install/OpenROAD/bin/openroad" -no_splash -exit "$ROOT/flow/power_vcd.tcl" > "$OUT/power.log" 2>&1 || true
rm -f "$OUT/keccak_perm_window.vcd"; gzip -f "$OUT/keccak_perm.vcd"
python3 - "$OUT" "$CLK_NS" <<'PY'
import json, re, sys, pathlib
out, clk = pathlib.Path(sys.argv[1]), float(sys.argv[2])
g = (out / "gls.log").read_text(); p = (out / "power.log").read_text()
m = re.search(r"KECCAK_RESULT .*cycles=(\d+)", g)
w = re.search(r"^Total\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)", p, re.M)
res = {"gls_pass": "PASS" in g and "FAIL" not in g, "cycles_perm": int(m[1]) if m else None,
       "clock_ns": clk, "total_power_w": float(w[4]) if w else None,
       "internal_w": float(w[1]) if w else None, "switching_w": float(w[2]) if w else None,
       "leakage_w": float(w[3]) if w else None,
       "activity_source": "gate-level VCD of one Keccak-f[1600] permutation of a random state"}
if res["total_power_w"] and res["cycles_perm"]:
    res["energy_per_permutation_nj"] = res["total_power_w"] * res["cycles_perm"] * clk
(out / "summary.json").write_text(json.dumps(res, indent=2)); print(res)
PY
