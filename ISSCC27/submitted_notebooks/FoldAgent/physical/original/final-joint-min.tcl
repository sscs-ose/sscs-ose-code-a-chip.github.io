read_liberty "/home/asic03/project/user37-zzc/.tools/chipnebula-sky130/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
read_verilog "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/frozen/L0/6_final.sta.v"
read_verilog "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/continuation-20261029/round3-resume-0116/local.sta.v"
read_verilog "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/joint/system.v"
link_design lb_feedback
create_clock -name clk -period 100 [get_ports clk]
set_input_delay 20 -clock clk [all_inputs -no_clocks]
set_output_delay 20 -clock clk [all_outputs]
set_input_transition 1.0 [all_inputs -no_clocks]
set_load 0.005 [all_outputs]
set_clock_uncertainty -setup 1 [get_clocks clk]
set_clock_uncertainty -hold 1 [get_clocks clk]
read_spef "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/joint/min.spef"
read_spef -path L0 "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/frozen/L0/6_final.spef"
read_spef -path L1 "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/continuation-20261029/round3-resume-0116/local.spef"
set_propagated_clock [all_clocks]
puts {CLOSURE_CONSTRAINT_BEGIN}
check_setup -verbose
puts {CLOSURE_CONSTRAINT_END}

report_units
if {[llength [get_clocks *]] != 1 || abs([get_property [get_clocks clk] period]-100) > .000001} {
  error "constraints differ from the frozen 100 ns clock"
}
report_worst_slack -max -digits 12
report_worst_slack -min -digits 12
report_parasitic_annotation -report_unannotated
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 12
puts "STACKLINK_STA setup_ns=[format %.17g [sta::worst_slack -max]] hold_ns=[format %.17g [sta::worst_slack -min]] instances=[llength [get_cells -hierarchical *]]"
puts "STACKLINK_ERC slew=[sta::max_slew_violation_count] capacitance=[sta::max_capacitance_violation_count] fanout=[sta::max_fanout_violation_count] setup=[sta::endpoint_violation_count max] hold=[sta::endpoint_violation_count min]"

set closure_pins {}
foreach pin [get_pins -hierarchical *] {if {[$pin is_leaf]} {lappend closure_pins $pin}}
foreach port [get_ports *] {lappend closure_pins [sta::get_port_pin $port]}
foreach pin $closure_pins {
  if {![$pin is_driver] || [$pin is_pwr_gnd]} {continue}
  set loads {}
  set iterator [$pin connected_pin_iterator]
  while {[$iterator has_next]} {
    set load [$iterator next]
    if {[$load is_load] && ![$load is_pwr_gnd]} {lappend loads [get_full_name $load]}
  }
  $iterator finish
  if {[llength $loads]==0} {puts "CLOSURE_UNLOADED [get_full_name $pin]"}
}
report_check_types -max_slew -max_capacitance -max_fanout -max_count 1000000 -no_line_splits -digits 17 > "/home/asic03/project/user37-zzc/work/chipnebula-p0-electrical-closure/continuation-20261029/round3-resume-0116/local-joint-min-full-erc.rpt"

set qs [dict create L0 {} L1 {}]
set ds [dict create L0 {} L1 {}]
foreach pin [all_registers -output_pins] {
  set name [get_full_name $pin]
  foreach die {L0 L1} {if {[string match "$die/*" $name]} {dict lappend qs $die $pin}}
}
foreach pin [all_registers -data_pins] {
  set name [get_full_name $pin]
  foreach die {L0 L1} {if {[string match "$die/*" $name]} {dict lappend ds $die $pin}}
}
foreach from {L0 L1} {
  foreach to {L0 L1} {
    puts "CLOSURE_PATH_CLASS $from->$to"
    report_checks -from [dict get $qs $from] -to [dict get $ds $to] -path_delay min_max -group_path_count 5 -format full_clock_expanded -digits 9
  }
}
foreach die {L0 L1} {
  set other [expr {$die eq "L0" ? "L1" : "L0"}]
  puts "CLOSURE_PATH_CLASS $die->$other->$die"
  report_checks -from [dict get $qs $die] -to [dict get $ds $die] -through [get_pins -hierarchical $other/*] -path_delay min_max -group_path_count 5 -format full_clock_expanded -digits 9
}
exit
