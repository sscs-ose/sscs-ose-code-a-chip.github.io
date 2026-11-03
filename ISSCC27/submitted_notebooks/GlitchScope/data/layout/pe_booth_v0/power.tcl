read_liberty <tools>/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog <repo>/build_layout/results/sky130hd/dot4_i8_pe_booth_v0/base/6_final.v
link_design dot4_i8
read_sdc <repo>/build_layout/results/sky130hd/dot4_i8_pe_booth_v0/base/6_final.sdc
read_spef <repo>/build_layout/results/sky130hd/dot4_i8_pe_booth_v0/base/6_final.spef
set_propagated_clock [all_clocks]
puts "===== vectorless (default activity)"
report_power
read_saif -scope dot4_i8 <repo>/data/layout/pe_booth_v0/glitchscope/glitch_activity.saif
puts "===== with GlitchScope SAIF"
report_power
report_checks -path_delay max -digits 3
report_design_area
