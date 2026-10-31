current_design benchmark_dot
create_clock -name nebula_clock -period 100 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks nebula_clock]
set_input_delay 0.5 -clock nebula_clock [get_ports {req_a[*] rsp_ready kill}]
set_output_delay 0.5 -clock nebula_clock [all_outputs]
