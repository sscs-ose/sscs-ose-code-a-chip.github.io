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
(cd "$ROOT/golden" && python3 gen_vectors.py --out "$TMP" --ntt 1 --keccak 1 > /dev/null)
cd "$TMP"
# a functional check: unit cell delays and a relaxed 100 ns clock, so that no timing effect can mask a logic error
iverilog -g2012 -I . -DFUNCTIONAL -DUNIT_DELAY=#1 -DCLK_HALF=50 -o gls.vvp primitives.v sky130_fd_sc_hd.v netlist.v \
    "$ROOT/tb/tb_ntt.sv" > "$OUT/compile.log" 2>&1 || { grep -v -i warning "$OUT/compile.log" | head -20; exit 1; }
start=$(date +%s)
vvp -n gls.vvp > "$OUT/gls.log"
echo "simulation time: $(( $(date +%s) - start )) s" >> "$OUT/gls.log"
rm -rf "$TMP"
grep -E "NTT_RESULT|PASS|FAIL|MISMATCH|simulation time" "$OUT/gls.log" | head -6
