# Macro-to-macro setup edges of a global-route database at one corner: for every ordered pair of SRAM macros with a
# timing path from the first one's dout to the second one's inputs, the worst slack (the phase rule of an inverted
# macro clock needs the list of such edges). env: RUN CORNER
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
set macros {}
foreach c [all_registers -cells] { if {[string match "sky130_sram*" [get_property $c ref_name]]} { lappend macros $c } }
foreach m $macros {
  set ins {}
  foreach p [get_pins -of_objects $m] {
    if {[get_property $p direction] == "input" && ![string match "*clk*" [get_full_name $p]]} { lappend ins $p }
  }
  foreach s $macros {
    if {$s == $m} continue
    set p [find_timing_paths -path_delay max -from $s -to $ins -group_path_count 1]
    if {[llength $p]} { puts "EDGE [get_full_name $s] -> [get_full_name $m] [get_property [lindex $p 0] slack]" }
  }
}
exit
