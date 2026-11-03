read_liberty <tools>/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog <repo>/build_layout/results/sky130hd/mul16_r_td/base/6_final.v
link_design mul16
read_sdc <repo>/build_layout/results/sky130hd/mul16_r_td/base/6_final.sdc
read_spef <repo>/build_layout/results/sky130hd/mul16_r_td/base/6_final.spef
set_propagated_clock [all_clocks]
puts "===== vectorless (default activity)"
report_power
read_saif -scope mul16 <repo>/data/layout/r_td/glitchscope/glitch_activity.saif
puts "===== with GlitchScope SAIF"
report_power
report_checks -path_delay max -digits 3
report_design_area
