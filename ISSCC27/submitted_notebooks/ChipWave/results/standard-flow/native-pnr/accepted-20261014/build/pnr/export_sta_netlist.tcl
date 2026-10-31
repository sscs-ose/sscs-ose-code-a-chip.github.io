if {[catch {

read_liberty /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.odb
read_sdc /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/physical/chip-nebula/constraints.sdc
set_propagated_clock [all_clocks]
read_spef /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.spef
set block [ord::get_db_block]
set remove {}
set f [open /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_instances.tsv w]
puts $f "instance	master	signal_pin_count	liberty_model	sta_preserved	antenna"
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set name [$master getName]
  set signals 0
  foreach mt [$master getMTerms] {
    if {[$mt getSigType] ni {POWER GROUND}} {incr signals}
  }
  set modeled [expr {[llength [get_lib_cells -quiet $name]] > 0}]
  if {$signals > 0 && !$modeled} {error "Error-Class: invalid_physical_view: missing Liberty model for actual signal master $name"}
  set keep [expr {$signals > 0 || $modeled}]
  if {!$keep} {lappend remove $name}
  set antenna [expr {[$master getType] eq "CORE_ANTENNACELL"}]
  puts $f "[$inst getName]	$name	$signals	$modeled	$keep	$antenna"
}
close $f
write_verilog -sort -remove_cells [lsort -unique $remove] /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.sta.v
write_sdc -no_timestamp -digits 12 /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.sdc
write_sdf -no_timestamp -digits 12 /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.sdf
write_cdl -masters /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/cdl/sky130hd.cdl /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.cdl
set nebula_geometry_report /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr
source /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/geometry_measure.tcl
check_placement -verbose
set routed [design_is_routed -verbose]
set antenna [check_antennas -verbose -report_file /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/final_antenna.rpt]
set f [open /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/physical_checks.json w]
puts $f [format {{"routed": %s, "antenna_violations": %d}} [expr {$routed ? "true" : "false"}] $antenna]
close $f
check_power_grid -net VDD -error_file /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/final_power_vdd.rpt
check_power_grid -net VSS -error_file /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/final_power_vss.rpt

set f [open /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_signal_connectivity.tsv w]
puts $f "net	terminal"
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] in {POWER GROUND}} {continue}
  foreach it [$net getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] ni {POWER GROUND}} {puts $f "[$net getName]	I:[[$it getInst] getName]/[$mt getName]"}
  }
  foreach bt [$net getBTerms] {puts $f "[$net getName]	P:[$bt getName]"}
}
close $f
set f [open /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_all_signal_pins.tsv w]
puts $f "terminal	net"
foreach inst [[ord::get_db_block] getInsts] {
  foreach it [$inst getITerms] {
    if {[[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
    set net [$it getNet]
    set netname ""
    if {$net ne "NULL"} {set netname [$net getName]}
    puts $f "I:[$inst getName]/[[$it getMTerm] getName]	$netname"
  }
}
foreach bt [[ord::get_db_block] getBTerms] {
  if {[$bt getSigType] ni {POWER GROUND}} {puts $f "P:[$bt getName]	[[$bt getNet] getName]"}
}
close $f
report_units
report_parasitic_annotation -report_unannotated > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_parasitic_annotation.rpt
report_checks -path_delay max -group_path_count 10000 -format full_clock_expanded -fields {slew capacitance fanout input_pin net} -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_setup_paths.rpt
report_checks -path_delay min -group_path_count 10000 -format full_clock_expanded -fields {slew capacitance fanout input_pin net} -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_hold_paths.rpt
check_setup -verbose > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_check_setup.rpt
report_checks -unconstrained -path_delay min_max -group_path_count 10000 -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_unconstrained_paths.rpt
foreach kind {max_slew max_capacitance max_fanout recovery removal min_pulse_width} {
  puts "REPORT_CHECK_TYPES database $kind -violators"
  report_check_types -$kind -violators -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_$kind.rpt
}
report_clock_skew -setup -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_clock_skew_setup.rpt
report_clock_skew -hold -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_clock_skew_hold.rpt
set f [open /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr/database_timing.json w]
puts $f [format {{"setup_slack_ns": %.17g, "hold_slack_ns": %.17g, "instance_count": %d}} [sta::worst_slack -max] [sta::worst_slack -min] [llength [get_cells -hier *]]]
close $f
report_worst_slack -max -digits 12
report_worst_slack -min -digits 12
report_tns -max -digits 12
report_tns -min -digits 12


} message options]} {
puts stderr $message
puts stderr [dict get $options -errorinfo]
exit 1
}
exit
