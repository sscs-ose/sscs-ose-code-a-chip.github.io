###############################################################################
# Created by write_sdc
###############################################################################
current_design fir_filter
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name clk -period 10.0000 [get_ports {clk}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {a[0]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {a[1]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {a[2]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {a[3]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {b[0]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {b[1]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {b[2]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {b[3]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {c[0]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {c[1]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {c[2]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {c[3]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {reset}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {x[0]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {x[1]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {x[2]}]
set_input_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {x[3]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {v1}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {v2}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {v3}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {v4}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {v5}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[0]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[1]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[2]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[3]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[4]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[5]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[6]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[7]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[8]}]
set_output_delay 2.0000 -clock [get_clocks {clk}] -add_delay [get_ports {y[9]}]
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
