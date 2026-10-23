# Corner STA of the routed full chip (used by scripts/sta_corners_fullchip.sh). It loads the design like
# flow/sta_corner.tcl (routed database, extracted SPEF, the corner's standard-cell Liberty, the SRAM macros'
# views) and reports the clocked paths in a form that keeps three things apart:
#  * report_checks prints the asynchronous group (reset recovery/removal) before the core_clk group, so a
#    summary must read the core_clk group by name;
#  * all_registers includes the SRAM macros, whose views exist for the typical corner only, so the
#    flip-flop-to-flip-flop paths are reported separately, with the macros excluded at both ends;
#  * every hold-violating endpoint is listed.
# env: LIB SDC SPEF ODB EXTRA_LIBS
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
foreach lib $::env(EXTRA_LIBS) { read_liberty $lib }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
report_parasitic_annotation
puts "RESULT setup_wns [sta::format_time [sta::worst_slack_cmd max] 3]"
puts "RESULT hold_wns [sta::format_time [sta::worst_slack_cmd min] 3]"
puts "RESULT setup_violating_endpoints [sta::endpoint_violation_count max]"
puts "RESULT hold_violating_endpoints [sta::endpoint_violation_count min]"
set regs [all_registers]
set ffs {}
set macros {}
foreach c [all_registers -cells] {
  if {[string match "sky130_sram*" [get_property $c ref_name]]} { lappend macros $c } else { lappend ffs $c }
}
puts "RESULT flipflops [llength $ffs]"
puts "RESULT macros [llength $macros]"
puts "SECTION reg2reg_with_macros"
report_checks -path_delay max -from $regs -to $regs -format end -group_path_count 1
report_checks -path_delay min -from $regs -to $regs -format end -group_path_count 1
puts "SECTION ff2ff_setup"
report_checks -path_delay max -from $ffs -to $ffs -format end -group_path_count 1
puts "SECTION ff2ff_hold"
report_checks -path_delay min -from $ffs -to $ffs -format end -group_path_count 1
puts "SECTION ff2ff_worst_setup_path"
report_checks -path_delay max -from $ffs -to $ffs -group_path_count 1 -fields {fanout cap slew}
puts "SECTION hold_violators"
report_checks -path_delay min -group_path_count 20 -slack_max 0 -format summary
puts "SECTION worst_setup_paths_any"
report_checks -path_delay max -group_path_count 5 -format summary
puts "SECTION END"
exit
