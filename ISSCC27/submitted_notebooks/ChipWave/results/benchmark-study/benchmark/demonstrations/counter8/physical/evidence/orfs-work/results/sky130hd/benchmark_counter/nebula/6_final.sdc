###############################################################################
# Created by write_sdc
###############################################################################
current_design benchmark_counter
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name benchmark_clock -period 100.0000 [get_ports {clk}]
set_clock_uncertainty 0.1000 benchmark_clock
set_propagated_clock [get_clocks {benchmark_clock}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {en}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[0]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[1]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[2]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[3]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[4]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[5]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[6]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {load_value[7]}]
set_input_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {rst_n}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[0]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[1]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[2]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[3]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[4]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[5]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[6]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {count[7]}]
set_output_delay 0.5000 -clock [get_clocks {benchmark_clock}] -add_delay [get_ports {overflow}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
