#!/usr/bin/env bash
# D2: input setup / hold of sky130_sram_1rw_24x256 at ss (1.60 V, 100 C) by ngspice: a grid of input-change times s
# relative to the rising clock edge (openram_energy.py SRAM_ENERGY_IN_AT); a point passes when every write and read of
# the run is correct. setup = -s for s near 0, hold = 40 + s for s near -40. Results: /root/sram_setup/<s>/<macro>/energy.json
set -u
H=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/sram_setup
SP=/mnt/d/TKVM_ATTT_2026_test/codeachip/flow/macros/spice/sky130_sram_1rw_24x256.sp.gz
export PDK_LIB=/opt/eda/pdks-openram/sky130A/libs.tech/ngspice/sky130.lib.spice NGSPICE=/opt/eda/ngspice-cf/bin/ngspice
export SRAM_ENERGY_CORNER=ss SRAM_ENERGY_VDD=1.6 SRAM_ENERGY_TEMP=100 SRAM_ENERGY_DELAY=1 SRAM_ENERGY_T_NS=40 \
       SRAM_ENERGY_SETTLE=3 SRAM_ENERGY_ACCESSES=3
one() { SRAM_ENERGY_IN_AT=$1 bash $H/run_openram_energy.sh /root/sram_setup/s$1 $SP; }
export -f one; export H SP
printf '%s\n' ${POINTS:--0.1 -0.2 -0.35 -0.5 -0.75 -1.0 -1.5 -2.5 -39.95 -39.85 -39.7 -39.4} | xargs -P ${J:-4} -I{} bash -c 'one {}'
for d in /root/sram_setup/s*/sky130_sram_1rw_24x256; do
  python3 -c "import json,sys; d=json.load(open('$d/energy.json')); print('$d'.split('/')[3], 'reads_correct', d['reads_correct'], 'clk_to_dout', d.get('clk_to_dout_ns'))" 2>/dev/null || echo "$d no result"
done | sort -t s -k2 -g
