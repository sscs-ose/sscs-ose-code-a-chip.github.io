# Multi-corner STA of a routed ORFS design.
# env: LIB SDC SPEF, and either ODB (routed OpenROAD database; run with `openroad`) or NETLIST + TOP
#      (run with OpenSTA `sta`) [EXTRA_LIBS: further Liberty files, e.g. the SRAM macros of the full chip]
# Prefer ODB: ORFS leaves the antenna diodes out of 6_final.v while 6_final.spef still refers to them,
# so with the netlist alone the nets that carry a diode keep no (or only part of their) parasitics.
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
if { [info exists ::env(EXTRA_LIBS)] } { foreach lib $::env(EXTRA_LIBS) { read_liberty $lib } }
if { [info exists ::env(ODB)] } {
  read_db $::env(ODB)
} else {
  read_verilog $::env(NETLIST)
  link_design $::env(TOP)
}
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
report_parasitic_annotation
set regs [all_registers]
puts "RESULT setup_wns [sta::format_time [sta::worst_slack_cmd max] 3]"
puts "RESULT hold_wns [sta::format_time [sta::worst_slack_cmd min] 3]"
puts "RESULT setup_violating_endpoints [sta::endpoint_violation_count max]"
puts "RESULT hold_violating_endpoints [sta::endpoint_violation_count min]"
report_checks -path_delay max -from $regs -to $regs -format end -group_path_count 1
report_checks -path_delay min -from $regs -to $regs -format end -group_path_count 1
# the worst hold paths of any kind (input ports included), for naming the violators
puts "WORST_HOLD_PATHS"
report_checks -path_delay min -group_path_count 3 -format summary
exit
