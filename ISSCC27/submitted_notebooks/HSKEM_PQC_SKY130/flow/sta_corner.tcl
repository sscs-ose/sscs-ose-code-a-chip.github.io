# Multi-corner STA of a routed ORFS design with OpenSTA.
# env: LIB NETLIST SDC SPEF TOP
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
read_verilog $::env(NETLIST)
link_design $::env(TOP)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
set regs [all_registers]
puts "RESULT setup_wns [sta::format_time [sta::worst_slack_cmd max] 3]"
puts "RESULT hold_wns [sta::format_time [sta::worst_slack_cmd min] 3]"
report_checks -path_delay max -from $regs -to $regs -format end -group_path_count 1
report_checks -path_delay min -from $regs -to $regs -format end -group_path_count 1
exit
