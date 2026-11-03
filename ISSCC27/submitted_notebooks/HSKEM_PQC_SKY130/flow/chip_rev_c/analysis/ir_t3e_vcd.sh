#!/usr/bin/env bash
# (18/10) IR drop of HSKEM-2 rev B with the decapsulation activity of the corrected (x4-stretched) shadow VCD:
# edge sources at the met5 strap ends (vsrc_edge_*), SPICE macro power (macro_power.tcl), macro Liberty copies
# without internal power (views_nopower). Same setup as /root/t3/ir_w1_vcd (17/10), which read the unstretched VCD.
set -euo pipefail
O=/root/t3/ir_w1_vcd4; mkdir -p "$O"
RUN=/root/t3/t3e_final_w1/results MACRO_LIB_DIR=/root/t3/ir_w1_spice/views_nopower OUT="$O" \
CHIPV2_VCD=/mnt/c/chipv2_signoff/power_t3e/shadow0.vcd CHIPV2_MACRO_POWER=/root/t3/ir_w1_spice/macro_power.tcl \
CHIPV2_VSRC_DIR=/root/t3/ir_w1_edge \
  /opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad -no_splash -exit \
  /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/ir_drop.tcl > "$O/ir.log" 2>&1
grep -E "CHIPV2_IR|^Sequential|^Combinational|^Clock|^Total|IR drop|Percentage" "$O/ir.log"
