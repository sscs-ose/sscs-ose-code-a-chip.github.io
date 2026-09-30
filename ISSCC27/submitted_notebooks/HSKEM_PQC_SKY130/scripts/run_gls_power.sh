#!/usr/bin/env bash
# Gate-level simulation of a routed NTT netlist and activity-based power.
#   1. simulate results of ORFS (6_final.v) with the SKY130 functional cell
#      models against the golden vectors (bit-exact check);
#   2. record a VCD over exactly one forward NTT of a random polynomial;
#   3. annotate that activity with the extracted parasitics in OpenROAD and
#      report power; energy per transform = power x cycles x clock period.
# usage: run_gls_power.sh <run, e.g. ntt_sp_20ns>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
RUN=${1:?run}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
PDK="${SKY130_HD:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd | head -1)}"
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
B="${CAC_WORK:-$HOME/cac_runs}/$RUN/results/sky130hd/cac_$RUN/base"
OUT="$ROOT/results/gls_power/$RUN"; mkdir -p "$OUT"
TOP=$(grep -m1 -oE "^module [A-Za-z0-9_]+" "$B/6_final.v" | cut -d' ' -f2)
CLK_NS=$(grep -m1 -oE "create_clock.*-period [0-9.]+" "$B/6_final.sdc" | grep -oE "[0-9.]+$")
HALF=$(python3 -c "print($CLK_NS/2)")

if [ "${SKIP_GLS:-0}" = 1 ] && [ -f "$OUT/ntt_fwd.vcd.gz" ]; then
  gunzip -kf "$OUT/ntt_fwd.vcd.gz"          # reuse the recorded activity; only redo the power step
else
VEC="$OUT/vectors"; mkdir -p "$VEC"
(cd "$ROOT/golden" && python3 gen_vectors.py --out "$VEC" --ntt 1 --keccak 1 > /dev/null)
DEFS=(-DFUNCTIONAL -DUNIT_DELAY=#1 -DCLK_HALF=$HALF -DVCD_VEC=4 "-DVCD_OUT=\"$OUT/ntt_fwd.vcd\"")
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
cd "$VEC"
iverilog -g2012 -I . "${DEFS[@]}" -o "$OUT/gls.vvp" \
    "$MODELS/primitives.v" "$MODELS/sky130_fd_sc_hd.v" "$OUT/netlist.v" "$ROOT/tb/tb_ntt.sv" > "$OUT/compile.log" 2>&1 \
  || { grep -v -i warning "$OUT/compile.log" | head -20; exit 1; }
vvp -n "$OUT/gls.vvp" > "$OUT/gls.log"
rm -rf "$OUT/gls.vvp" "$OUT/netlist.v" "$MODELS" "$VEC"
grep -E "NTT_RESULT|PASS|FAIL|MISMATCH" "$OUT/gls.log" | head -5
fi

# OpenSTA reads no $dumpon/$dumpoff blocks: cut the file to the recorded window first
python3 "$ROOT/scripts/vcd_window.py" "$OUT/ntt_fwd.vcd" "$OUT/ntt_fwd_window.vcd"
# OpenSTA alone needs no LEF/technology data, unlike the openroad shell
LIB="$ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib" NETLIST="$B/6_final.v" \
SDC="$B/6_final.sdc" SPEF="$B/6_final.spef" TOP=$TOP VCD="$OUT/ntt_fwd_window.vcd" SCOPE="tb_ntt/dut" \
  "$ORFS/tools/install/OpenROAD/bin/sta" -no_splash -exit "$ROOT/flow/power_vcd.tcl" > "$OUT/power.log" 2>&1 || true
rm -f "$OUT/ntt_fwd_window.vcd"; gzip -f "$OUT/ntt_fwd.vcd"
python3 - "$OUT" "$CLK_NS" <<'PY'
import json, re, sys, pathlib
out, clk = pathlib.Path(sys.argv[1]), float(sys.argv[2])
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
(out / "summary.json").write_text(json.dumps(res, indent=2)); print(res)
PY
