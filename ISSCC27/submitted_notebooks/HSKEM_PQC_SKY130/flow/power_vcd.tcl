# Activity-based power of a routed design from a gate-level VCD (OpenROAD/OpenSTA).
# env: LIB NETLIST SDC SPEF TOP VCD SCOPE
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
read_verilog $::env(NETLIST)
link_design $::env(TOP)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
read_vcd -scope $::env(SCOPE) $::env(VCD)
report_power
exit
