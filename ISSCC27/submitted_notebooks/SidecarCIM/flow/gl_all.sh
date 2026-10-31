#!/bin/bash
# usage: flow/gl_all.sh <flowdir> <run_dir> <rtl_vcd> <name>
# gate-level sim of the post-layout netlist with the RTL testbench's input stimulus -> busy-window VCD -> power
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
set -e
cd "$ROOT"
fd=$1; run=$2; rtlvcd=$3; name=$4; maxe=${5:-1000000000}
top=$(python3 -c "import json;print(json.load(open('flow/$fd/config.json'))['DESIGN_NAME'])")
mkdir -p flow/vcd_compute
python3 flow/gl_stim.py $rtlvcd flow/vcd_compute/$top.stim $maxe
python3 flow/gl_sim.py $top $run flow/vcd_compute/$top.stim flow/vcd_compute/$name.gl.vcd /tmp/gl_$name
python3 flow/vcd_window.py flow/vcd_compute/$name.gl.vcd flow/vcd_compute/$name.gl.busy.vcd
rm -f flow/vcd_compute/$name.gl.vcd
bash flow/power.sh $fd $run flow/vcd_compute/$name.gl.busy.vcd tb/dut
