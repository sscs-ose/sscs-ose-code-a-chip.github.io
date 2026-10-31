current_design benchmark_fifo
create_clock -name benchmark_clock -period 100 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks benchmark_clock]
set_input_delay 0.5 -clock benchmark_clock [get_ports {rst_n wr_en rd_en wr_data[*]}]
set_output_delay 0.5 -clock benchmark_clock [all_outputs]
