# ============================================================================
#  power_vcd.tcl -- post-P&R power with gate-level VCD activity (OpenROAD)
#  env: LIB TECH_LEF CELL_LEF NETLIST TOP SDC SPEF VCD SCOPE
# ============================================================================
read_lef $::env(TECH_LEF)
read_lef $::env(CELL_LEF)
read_liberty $::env(LIB)
read_verilog $::env(NETLIST)
link_design $::env(TOP)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
read_vcd -scope $::env(SCOPE) $::env(VCD)
report_power
