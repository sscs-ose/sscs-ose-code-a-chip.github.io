#!/usr/bin/env bash
# Gate-level TVLA of HSKEM-2's NTT engine: the routed netlist of the two-lane packed engine (ntt_packed2_20ns)
# simulated with the SKY130 cell models (zero delay) and OpenRAM's model of its 24 x 128 macro; each trace sample
# is the capacitance switched in one clock, from the extracted wire capacitance and the input-pin loads of every
# net (scripts/leak_cap_monitor.py). Same inputs, labels and Welch test as scripts/run_leakage.sh.
# usage: run_leakage_gls.sh [N traces] [noise sigma in toggles of the mean net] [plain|masked]
#   needs the routed database of the block (CAC_WORK, default ~/cac_runs) for its SPEF.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
N=${1:-2000}; SIGMA=${2:-4.0}; MODE=${3:-plain}
RUN=ntt_packed2_20ns; MACRO=sky130_sram_1rw_24x128
B="${CAC_WORK:-$HOME/cac_runs}/$RUN/results/sky130hd/cac_$RUN/base"
ORFS="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
PDK="${SKY130_HD:-$(ls -d /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd | head -1)}"
OUT="$ROOT/results/leakage_gls"; MFLAG=""
[ "$MODE" = masked ] && { OUT="$ROOT/results/leakage_gls_masked"; MFLAG="--masked"; }
mkdir -p "$OUT"; W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
cd "$ROOT/golden" && python3 leakage.py gen --out "$OUT" -n "$N" $MFLAG
python3 "$ROOT/scripts/leak_cap_monitor.py" "$B/6_final.v" "$B/6_final.spef" \
    "$ORFS/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib" "$ROOT/flow/macros/${MACRO}_TT_1p8V_25C.lib" \
    --scope tb_ntt_leak.dut --out "$W/leak_cap_mon.sv" > "$OUT/cap_monitor.json"
cp "$W/leak_cap_mon.json" "$OUT/cap_monitor.json"
# Icarus rejects text after `endif in the SKY130 cell models: compile cleaned copies
for f in primitives.v sky130_fd_sc_hd.v; do
  sed -E 's/^([[:space:]]*`endif)[[:space:]]+[^/[:space:]].*$/\1/' "$PDK/verilog/$f" > "$W/$f"
done
sed "s/parameter VERBOSE = 1/parameter VERBOSE = 0/" "$ROOT/flow/macros/$MACRO.v" > "$W/sram_model.v"
iverilog -g2012 -DGLS_CAP -DFUNCTIONAL "-DUNIT_DELAY=" -I "$OUT" -s tb_ntt_leak -s leak_cap_mon -o "$W/leak.vvp" \
    "$W/primitives.v" "$W/sky130_fd_sc_hd.v" "$W/sram_model.v" "$B/6_final.v" "$ROOT/tb/tb_ntt_leak.sv" \
    "$W/leak_cap_mon.sv" > "$W/compile.log" 2>&1 || { grep -v -i warning "$W/compile.log" | head -20; exit 1; }
(cd "$OUT" && vvp -n "$W/leak.vvp" | grep LEAK)
# noise: SIGMA toggles of the mean switched net (so that sigma is comparable with the register model's)
SIG_AF=$(python3 -c "import json; m=json.load(open('$OUT/cap_monitor.json')); print(round($SIGMA * (m['wire_cap_pf'] + m['pin_cap_pf']) / m['nets'] * 1e6))")
cd "$ROOT/golden" && python3 leakage.py analyze --out "$OUT" --sigma "$SIG_AF"
python3 - "$OUT" "$SIGMA" "$SIG_AF" <<'PY'
import json, sys, pathlib
o = pathlib.Path(sys.argv[1]); s = json.loads((o / "tvla_summary.json").read_text())
s.update({"model": "gate level: routed netlist of ntt_packed2_20ns, zero delay, switched capacitance per cycle "
                    "(SPEF wire + input-pin loads) in aF", "noise_sigma_mean_net_toggles": float(sys.argv[2]),
          "noise_sigma_af": int(sys.argv[3])})
(o / "tvla_summary.json").write_text(json.dumps(s, indent=2) + "\n"); print(json.dumps(s))
PY
