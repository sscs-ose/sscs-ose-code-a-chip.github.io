current_design nebula_cpu_npu_top
create_clock -name nebula_clock -period 10.5263 [get_ports {clk}]
set_clock_uncertainty 0.1 [get_clocks nebula_clock]
set_input_delay 0.5 -clock nebula_clock [get_ports {rst_n imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]
set_output_delay 0.5 -clock nebula_clock [all_outputs]
