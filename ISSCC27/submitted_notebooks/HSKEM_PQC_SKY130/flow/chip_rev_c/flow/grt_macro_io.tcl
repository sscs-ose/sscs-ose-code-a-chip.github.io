# Per SRAM macro of a global-route database at one corner: worst setup slack of the paths into its inputs (launched by
# a flip-flop / by another macro) and out of its dout, and the worst hold slack out of its dout. Decides which macros can
# take an inverted clock (inputs get half a cycle, outputs a full one). env: RUN (results dir) CORNER
# SPDX-License-Identifier: Apache-2.0
set R $::env(RUN)
set P /opt/eda/orfs-6101364b/flow/platforms/sky130hd
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__$::env(CORNER).lib] 0]
read_liberty $L
set MLD [expr {[info exists ::env(MACRO_LIB_DIR)] ? $::env(MACRO_LIB_DIR) : "/mnt/d/TKVM_ATTT_2026_test/report/a2_macro_link_smoke/run.rjfysF/derived_liberty"}]
foreach f [glob $MLD/*.physical.lib] { read_liberty $f }
puts "RESULT macro_views $MLD"
read_db $R/5_1_grt.odb
read_sdc $R/5_1_grt.sdc
source $P/setRC.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
set macros {}; set flops {}
foreach c [all_registers -cells] {
  if {[string match "sky130_sram*" [get_property $c ref_name]]} { lappend macros $c } else { lappend flops $c }
}
proc worst {args} {
  set p [eval find_timing_paths $args -group_path_count 1]
  if {[llength $p] == 0} { return NA }
  return [sta::format_time [get_property [lindex $p 0] slack] 3]
}
foreach m $macros {
  set n [get_full_name $m]
  set ins {}
  foreach p [get_pins -of_objects $m] {
    if {[get_property $p direction] == "input" && ![string match "*clk*" [get_full_name $p]]} { lappend ins $p }
  }
  set others [lsearch -all -inline -not -exact $macros $m]
  puts "MACRO $n [get_property $m ref_name] in_flop [worst -path_delay max -from $flops -to $ins] in_macro [worst -path_delay max -from $others -to $ins] out_setup [worst -path_delay max -from $m] out_hold [worst -path_delay min -from $m]"
}
exit
