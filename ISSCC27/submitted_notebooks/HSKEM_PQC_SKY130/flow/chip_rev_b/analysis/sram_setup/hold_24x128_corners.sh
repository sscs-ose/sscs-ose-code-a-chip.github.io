#!/usr/bin/env bash
# (18/10) Hold of sky130_sram_1rw_24x128 by ngspice at the earliest input change that STA finds on the final w1
# database (macro_hold_t3e.sh: worst hold path ends at din0 of this macro, arriving 1.116 / 0.601 / 0.399 ns after the
# macro clock at ss / tt / ff, SoC I/O model, SPICE views). Every input of the deck changes that long after the rising
# edge (SRAM_ENERGY_IN_AT = -(40 - t)); a point passes when every write and read is correct.
# Results: /root/sram_hold128/<corner>/sky130_sram_1rw_24x128/energy.json
set -u
H=/mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/sram_setup
SP=/mnt/d/TKVM_ATTT_2026_test/codeachip/flow/macros/spice/sky130_sram_1rw_24x128.sp.gz
export PDK_LIB=/opt/eda/pdks-openram/sky130A/libs.tech/ngspice/sky130.lib.spice NGSPICE=/opt/eda/ngspice-cf/bin/ngspice
export SRAM_ENERGY_DELAY=1 SRAM_ENERGY_T_NS=40 SRAM_ENERGY_SETTLE=3 SRAM_ENERGY_ACCESSES=3 H SP
one() {   # corner vdd temp in_at
  SRAM_ENERGY_CORNER=$1 SRAM_ENERGY_VDD=$2 SRAM_ENERGY_TEMP=$3 SRAM_ENERGY_IN_AT=$4 \
    bash $H/run_openram_energy.sh /root/sram_hold128/$1 $SP > /root/sram_hold128/$1.log 2>&1
}
export -f one; mkdir -p /root/sram_hold128
printf '%s\n' "ss 1.6 100 -38.884" "tt 1.8 25 -39.399" "ff 1.95 -40 -39.601" | xargs -P 3 -L 1 bash -c 'one $0 $1 $2 $3'
for c in ss tt ff; do
  python3 -c "import json; d=json.load(open('/root/sram_hold128/$c/sky130_sram_1rw_24x128/energy.json')); print('$c', 'in_at', d['in_at_ns'], 'reads_correct', d['reads_correct'], 'clk_to_dout', d.get('clk_to_dout_ns'))" 2>/dev/null || echo "$c no result"
done
