
# ============================
# Clock definition
# ============================
create_clock -name clk -period 10 [get_ports clk]

# ============================
# Input delays (basic)
# ============================
set_input_delay 1 -clock clk [all_inputs]

# ============================
# Output delays (basic)
# ============================
set_output_delay 1 -clock clk [all_outputs]
