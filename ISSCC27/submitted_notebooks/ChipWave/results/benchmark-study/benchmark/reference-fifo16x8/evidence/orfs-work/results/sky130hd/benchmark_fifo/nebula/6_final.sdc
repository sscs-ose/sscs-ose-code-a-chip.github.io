###############################################################################
# Created by write_sdc
###############################################################################
current_design benchmark_fifo
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name benchmark_clock -period 100.0000 [get_ports {clk}]
set_clock_uncertainty 0.1000 benchmark_clock
set_propagated_clock [get_clocks {benchmark_clock}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_en}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rst_n}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[0]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[10]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[11]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[12]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[13]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[14]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[15]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[1]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[2]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[3]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[4]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[5]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[6]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[7]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[8]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_data[9]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {wr_en}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {empty}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {full}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[0]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[10]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[11]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[12]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[13]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[14]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[15]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[1]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[2]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[3]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[4]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[5]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[6]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[7]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[8]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rd_data[9]}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
