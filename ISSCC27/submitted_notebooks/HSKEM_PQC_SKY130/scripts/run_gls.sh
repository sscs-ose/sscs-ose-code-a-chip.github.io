#!/usr/bin/env bash
# Gate-level simulation of a committed routed NTT netlist (results/asic/<run>/6_final.v)
# against the golden vectors, with the SKY130 functional cell models shipped in
# third_party/. Needs only Icarus Verilog and Python, so it also runs in Colab.
# (scripts/run_gls_power.sh is the full version: it also records activity for power.)
# usage: run_gls.sh <run, e.g. ntt_opt_pipe_w12_20ns>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
RUN=${1:?run}
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NET="$ROOT/results/asic/$RUN/6_final.v"; [ -f "$NET" ] || { echo "no netlist for $RUN"; exit 2; }
OUT="$ROOT/results/gls_notebook/$RUN"; TMP="$(mktemp -d)"; mkdir -p "$OUT"
TOP=$(grep -m1 -oE "^module [A-Za-z0-9_]+" "$NET" | cut -d' ' -f2)
# the testbench instantiates kyber_ntt_engine; netlists of the parameterized top keep its port list
sed "s/^module $TOP /module kyber_ntt_engine /" "$NET" > "$TMP/netlist.v"
for f in primitives.v sky130_fd_sc_hd.v; do gunzip -c "$ROOT/third_party/sky130_fd_sc_hd/$f.gz" > "$TMP/$f"; done
# a macro-store netlist instantiates the OpenRAM macro: add its behavioural model (OpenRAM output), quiet
MODELS=""
if grep -q "sky130_sram_1rw_16x256_wpr8 " "$TMP/netlist.v"; then
  sed "s/parameter VERBOSE = 1/parameter VERBOSE = 0/" "$ROOT/flow/macros/sky130_sram_1rw_16x256_wpr8.v" > "$TMP/sram_model.v"
  MODELS="sram_model.v -DRD_SAMPLE_DELAY=10"    # its dout0 is valid only 3 ns after the falling edge
fi
if grep -q "sky130_sram_1rw_24x128 " "$TMP/netlist.v"; then
  sed "s/parameter VERBOSE = 1/parameter VERBOSE = 0/" "$ROOT/flow/macros/sky130_sram_1rw_24x128.v" > "$TMP/sram_model.v"
  MODELS="sram_model.v -DRD_SAMPLE_DELAY=10"
fi
[ "$TOP" = kyber_ntt_engine_packed2 ] && MODELS="$MODELS -DGLS_PAIR_PORTS"   # its pair and stream ports, tied off
(cd "$ROOT/golden" && python3 gen_vectors.py --out "$TMP" --ntt 1 --keccak 1 > /dev/null)
cd "$TMP"
# a functional check: unit cell delays and a relaxed 100 ns clock, so that no timing effect can mask a logic error
iverilog -g2012 -I . -DFUNCTIONAL -DUNIT_DELAY=#1 -DCLK_HALF=50 -o gls.vvp primitives.v sky130_fd_sc_hd.v $MODELS netlist.v \
    "$ROOT/tb/tb_ntt.sv" > "$OUT/compile.log" 2>&1 || { grep -v -i warning "$OUT/compile.log" | head -20; exit 1; }
start=$(date +%s)
vvp -n gls.vvp > "$OUT/gls.log"
echo "simulation time: $(( $(date +%s) - start )) s" >> "$OUT/gls.log"
rm -rf "$TMP"
grep -E "NTT_RESULT|PASS|FAIL|MISMATCH|simulation time" "$OUT/gls.log" | head -6
