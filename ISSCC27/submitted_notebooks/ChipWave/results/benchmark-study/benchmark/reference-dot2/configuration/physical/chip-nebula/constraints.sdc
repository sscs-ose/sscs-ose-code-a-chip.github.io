current_design benchmark_dot
create_clock -name benchmark_clock -period 100 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks benchmark_clock]
set_input_delay 0.5 -clock benchmark_clock [get_ports {rst_n req_valid req_a[*] req_b[*] rsp_ready kill}]
set_output_delay 0.5 -clock benchmark_clock [all_outputs]
