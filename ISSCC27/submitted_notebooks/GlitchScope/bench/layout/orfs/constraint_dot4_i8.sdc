# AI-accelerator PE (4-lane int8 dot product): 133 MHz for all variants
create_clock -name clk -period 7.5 [get_ports clk]
set_input_delay  0.5 -clock clk [delete_from_list [all_inputs] [get_ports clk]]
set_output_delay 0.5 -clock clk [all_outputs]
set_load 0.005 [all_outputs]
