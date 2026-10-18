# Sign-off STA of the final database with its extracted parasitics at one corner.
# env: RUN (results dir with 6_final.odb/.sdc/.spef), CORNER (liberty corner), MACRO_LIB_DIR (macro views),
#      IO_MODE sdc|soc (default sdc), DERATE (optional, e.g. 0.05: cell delays late x(1+d), early x(1-d))
# IO_MODE soc: the service ports (every port with an input or output delay in the SDC; the SPI pins are synchronized
# and false-pathed there) are timed against a virtual clock io_clk whose latency equals the core clock's measured
# insertion delay at this corner (report_clock_latency, min and max over all clock pins): the neighbour block that
# drives or samples them is assumed to sit on the same clock tree. Data delays: input max 2.0 ns / min 0.3 ns (a
# flop's clock-to-output), output max 2.0 ns / min 0.0 ns. The hold slack then is the latency mismatch the ports
# tolerate.
# SPDX-License-Identifier: Apache-2.0
set R $::env(RUN)
set mode [expr {[info exists ::env(IO_MODE)] ? $::env(IO_MODE) : "sdc"}]
# SC_LIB: the sky130_fd_sc_hd Liberty of the corner (default: the build machine's PDK)
set L [expr {[info exists ::env(SC_LIB)] ? $::env(SC_LIB) : [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__$::env(CORNER).lib] 0]}]
read_liberty $L
foreach f [glob $::env(MACRO_LIB_DIR)/*.physical.lib] { read_liberty $f }
puts "RESULT macro_views $::env(MACRO_LIB_DIR)"
puts "RESULT corner $::env(CORNER) io_mode $mode"
read_db $R/6_final.odb
read_sdc $R/6_final.sdc
set_propagated_clock [all_clocks]
read_spef $R/6_final.spef
if {[info exists ::env(DERATE)] && $::env(DERATE) > 0} {
  set_timing_derate -cell_delay -late [expr {1.0 + $::env(DERATE)}]
  set_timing_derate -cell_delay -early [expr {1.0 - $::env(DERATE)}]
  puts "RESULT derate $::env(DERATE)"
}
sta::with_output_to_variable lat { report_clock_latency -clock core_clk }
if {![regexp {\n\s*([-\d.]+)\s+([-\d.]+) latency} $lat -> lmin lmax]} { error "no clock latency parsed" }
puts "RESULT clock_latency_min $lmin"
puts "RESULT clock_latency_max $lmax"
if {$mode eq "soc"} {
  set ins [list]; set outs [list]
  foreach p [all_inputs] {
    set n [get_full_name $p]
    if {[string match "spi_*" $n] || $n eq "clk_i" || $n eq "rst_ni"} { continue }
    lappend ins $p
  }
  foreach p [all_outputs] { if {![string match "spi_*" [get_full_name $p]]} { lappend outs $p } }
  create_clock -name io_clk -period [get_property [get_clocks core_clk] period]
  set_clock_latency -min $lmin [get_clocks io_clk]
  set_clock_latency -max $lmax [get_clocks io_clk]
  set_clock_uncertainty 0.200 [get_clocks io_clk]
  set_input_delay -clock io_clk -max 2.0 $ins
  set_input_delay -clock io_clk -min 0.3 $ins
  set_output_delay -clock io_clk -max 2.0 $outs
  set_output_delay -clock io_clk -min 0.0 $outs
  puts "RESULT io_clk_ports in [llength $ins] out [llength $outs]"
}
puts "RESULT setup_wns [sta::format_time [sta::worst_slack_cmd max] 3]"
puts "RESULT setup_tns [sta::format_time [sta::total_negative_slack_cmd max] 3]"
puts "RESULT hold_wns [sta::format_time [sta::worst_slack_cmd min] 3]"
puts "RESULT hold_tns [sta::format_time [sta::total_negative_slack_cmd min] 3]"
puts "RESULT setup_violating_endpoints [sta::endpoint_violation_count max]"
puts "RESULT hold_violating_endpoints [sta::endpoint_violation_count min]"
sta::with_output_to_variable mp { report_clock_min_period }
if {[regexp {period_min = ([\d.]+) fmax = ([\d.]+)} $mp -> pmin fmax]} { puts "RESULT period_min $pmin fmax_mhz $fmax" }
puts "SECTION WORST_SETUP"
report_checks -path_delay max -group_path_count 20 -endpoint_path_count 1 -format end
puts "SECTION WORST_HOLD"
report_checks -path_delay min -group_path_count 20 -endpoint_path_count 1 -format end
# FMAX_SEARCH=1 (18/10): the shortest clock period with non-negative setup slack, by bisection on the real paths
# (report_clock_min_period does not treat the macros' falling-edge launches as half-cycle paths). The core clock keeps its
# 50 % duty cycle and uncertainty; in the SoC I/O model the virtual io_clk follows the period. Result: RESULT fmax_search.
if {[info exists ::env(FMAX_SEARCH)]} {
  set lo 5.0; set hi 60.0
  proc set_period {p} {
    create_clock -name core_clk -period $p -waveform [list 0 [expr {$p / 2.0}]] [get_ports clk_i]
    set_propagated_clock [get_clocks core_clk]
    set_clock_uncertainty 0.200 [get_clocks core_clk]
    if {[llength [get_clocks -quiet io_clk]]} {
      create_clock -name io_clk -period $p -waveform [list 0 [expr {$p / 2.0}]]
      set_clock_latency -min $::lmin [get_clocks io_clk]; set_clock_latency -max $::lmax [get_clocks io_clk]
      set_clock_uncertainty 0.200 [get_clocks io_clk]
    }
  }
  while {$hi - $lo > 0.02} {
    set mid [expr {($lo + $hi) / 2.0}]
    set_period $mid
    if {[sta::worst_slack_cmd max] >= 0} { set hi $mid } else { set lo $mid }
  }
  set_period $hi
  puts "RESULT fmax_search period_ns [format %.3f $hi] fmax_mhz [format %.2f [expr {1000.0 / $hi}]] setup_wns_at_period [sta::format_time [sta::worst_slack_cmd max] 3]"
  report_checks -path_delay max -fields {fanout cap slew} -digits 3
  exit
}
# MACRO_HOLD=1 (18/10): the hold paths into the SRAM macro inputs (addr/din/web/csb/wmask), whose view hold times are
# OpenRAM's analytical values; compared with the SPICE hold points of the D2 grid
if {[info exists ::env(MACRO_HOLD)]} {
  set mpins [list]
  foreach inst [get_cells *u_macro] {
    foreach p [get_pins -of_objects $inst -filter "direction == input"] {
      if {![string match "*clk0" [get_full_name $p]]} { lappend mpins $p }
    }
  }
  puts "RESULT macro_input_pins [llength $mpins]"
  puts "SECTION MACRO_HOLD"
  report_checks -path_delay min -to $mpins -group_path_count 40 -endpoint_path_count 1 -format end
  puts "SECTION MACRO_HOLD_PATH"
  report_checks -path_delay min -to $mpins -fields {slew} -digits 3
}
puts "SECTION WORST_SETUP_PATH"
report_checks -path_delay max -fields {fanout cap slew} -digits 3
puts "SECTION END"
exit
