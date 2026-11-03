# 66.7 MHz for all variants: the un-pipelined baseline meets timing without heavy repair
create_clock -name clk -period 15.0 [get_ports clk]
set_input_delay  0.5 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0.5 -clock clk [all_outputs]
set_load 0.005 [all_outputs]
