# ===== Units =====
set_units -time ns -resistance Ohm -capacitance pF -voltage V -current mA

# ===== Timing knobs (virtual clock + IO budgets) =====
set CLK_PERIOD         10.0
set CLK_UNCERTAINTY     0.10
set MAX_INPUT_DELAY     0.05
set MIN_INPUT_DELAY     0.01
set MAX_OUTPUT_DELAY    0.05
set MIN_OUTPUT_DELAY    0.01
set OUT_LOAD_PF         0.01
set MAX_TRANSITION      0.01
set MAX_FANOUT          16

# ===== Virtual clock for combinational block =====
set VCLK_NAME VCLK
create_clock -name $VCLK_NAME -period $CLK_PERIOD
set_clock_uncertainty $CLK_UNCERTAINTY [get_clocks $VCLK_NAME]

# ===== IO constraints (match RTL port names) =====
# inputs A[7:0], B[7:0]
set_input_delay  -max $MAX_INPUT_DELAY -clock [get_clocks $VCLK_NAME] [get_ports {A[*] B[*]}]
set_input_delay  -min $MIN_INPUT_DELAY -clock [get_clocks $VCLK_NAME] [get_ports {A[*] B[*]}]

# outputs OUT[15:0]
set_output_delay -max $MAX_OUTPUT_DELAY -clock [get_clocks $VCLK_NAME] [get_ports {OUT[*]}]
set_output_delay -min $MIN_OUTPUT_DELAY -clock [get_clocks $VCLK_NAME] [get_ports {OUT[*]}]

# Output loading & global limits
set_load $OUT_LOAD_PF [get_ports {OUT[*]}]
set_max_transition $MAX_TRANSITION  [current_design]
set_max_fanout     $MAX_FANOUT      [current_design]

# Optional: specify input slew if upstream not modeled
# set_input_transition 0.05 [get_ports {A[*] B[*]}]