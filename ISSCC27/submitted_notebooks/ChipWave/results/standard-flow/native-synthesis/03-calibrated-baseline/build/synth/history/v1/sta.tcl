read_liberty /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog build/synth/nebula_cpu_npu_top.v
link_design nebula_cpu_npu_top
read_sdc physical/chip-nebula/constraints.sdc
set_wire_load_model -name Small
report_units
write_sdc -no_timestamp -digits 9 reports/synthesis/loaded_constraints.sdc
report_checks -path_delay max -group_path_count 10 -format full_clock_expanded -fields {slew capacitance fanout input_pin net} -digits 6 > reports/synthesis/setup_paths.rpt
report_checks -path_delay min -group_path_count 10 -format full_clock_expanded -fields {slew capacitance fanout input_pin net} -digits 6 > reports/synthesis/hold_paths.rpt
report_checks -unconstrained -path_delay min_max -group_path_count 10 -digits 6 > reports/synthesis/unconstrained_paths.rpt
check_setup -verbose > reports/synthesis/check_setup.rpt
report_check_types -max_delay -min_delay -recovery -removal -min_pulse_width -max_slew -max_capacitance -max_fanout -violators -digits 6 > reports/synthesis/timing_violations.rpt
puts "BEGIN_METRICS"
report_worst_slack -max -digits 9
report_worst_slack -min -digits 9
report_tns -max -digits 9
report_tns -min -digits 9
puts "END_METRICS"
exit
