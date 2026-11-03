# GlitchScope -> OpenSTA hand-off check.
# Run from the folder containing mac.v and glitch_activity.saif:
#   setenv GS_LIB /path/to/sky130_fd_sc_hd__tt_025C_1v80.lib
#   sta -no_init -exit opensta_power.tcl          (or: openroad -no_init -exit opensta_power.tcl)
read_liberty $::env(GS_LIB)
read_verilog mac.v
link_design mac
create_clock -name clk -period 5.0 [get_ports clk]
puts "\n===== 1) OpenSTA default (propagated, glitch-free) activity ====="
report_power
puts "\n===== 2) GlitchScope glitch-accurate activity (SAIF) ====="
read_saif -scope mac glitch_activity.saif
report_power
puts "\nGlitchScope reference (Liberty energy, same activity): combinational dynamic = 208.9 uW, of which glitch = 89.4 uW"
