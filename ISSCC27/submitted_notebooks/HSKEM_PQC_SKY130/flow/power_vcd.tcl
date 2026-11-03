# Activity-based power of a routed design from a gate-level VCD (OpenROAD/OpenSTA).
# env: LIB SDC SPEF VCD SCOPE (optional LIB_MACRO), and either ODB (routed database; run with `openroad`) or NETLIST + TOP
# (run with OpenSTA `sta`). Prefer ODB: 6_final.v lacks the antenna diodes that the SPEF refers to
# (see flow/sta_corner.tcl).
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
if { [info exists ::env(LIB_MACRO)] } { read_liberty $::env(LIB_MACRO) }   ; # a macro-store block's SRAM
if { [info exists ::env(ODB)] } {
  read_db $::env(ODB)
} else {
  read_verilog $::env(NETLIST)
  link_design $::env(TOP)
}
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
report_parasitic_annotation
read_vcd -scope $::env(SCOPE) $::env(VCD)
report_power -digits 5   ; # five digits: input-to-input differences are below 0.5 %
exit
