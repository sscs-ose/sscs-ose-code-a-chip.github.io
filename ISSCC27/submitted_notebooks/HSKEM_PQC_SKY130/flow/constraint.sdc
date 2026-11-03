# SPDX-License-Identifier: Apache-2.0
set period $::env(CAC_CLK_NS)
create_clock -name clk -period $period [get_ports clk]
set_clock_uncertainty 0.25 [get_clocks clk]
set_false_path -from [get_ports rst_n]
set non_clk [delete_from_list [all_inputs] [get_ports {clk rst_n}]]
set_input_delay  [expr {0.2 * $period}] -clock clk $non_clk
set_output_delay [expr {0.2 * $period}] -clock clk [all_outputs]
set_load 0.02 [all_outputs]
