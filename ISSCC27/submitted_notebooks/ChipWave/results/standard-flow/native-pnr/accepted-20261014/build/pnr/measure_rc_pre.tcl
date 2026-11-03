if {[catch {
read_liberty /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-4b0dbf51bbf44ff8b36202bda62a7d89/build/pnr/results/5_1_grt.odb
read_sdc /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-4b0dbf51bbf44ff8b36202bda62a7d89/physical/chip-nebula/constraints.sdc
set_propagated_clock [all_clocks]
source /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/setRC.tcl
estimate_parasitics -global_routing
report_check_types -max_slew -net [get_nets _01792_] -max_count 100 -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-4b0dbf51bbf44ff8b36202bda62a7d89/reports/pnr/rc_pre_slew.rpt
report_check_types -max_capacitance -net [get_nets _01792_] -max_count 100 -digits 12 > /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-4b0dbf51bbf44ff8b36202bda62a7d89/reports/pnr/rc_pre_cap.rpt
set f [open /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-4b0dbf51bbf44ff8b36202bda62a7d89/reports/pnr/rc_pre_instances.tsv w]
puts $f "instance\tmaster"
foreach name {_23163_ _23182_ _25818_} {
set i [[ord::get_db_block] findInst $name]
puts $f "$name\t[[$i getMaster] getName]"
}
close $f
} message options]} {puts stderr $message;puts stderr [dict get $options -errorinfo];exit 1}
exit
