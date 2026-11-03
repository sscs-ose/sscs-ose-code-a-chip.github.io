# C6: static IR drop of the t3e final power grid (OpenROAD PSM) at tt 1.80 V. Power per instance from OpenSTA with
# the extracted parasitics and a uniform input activity (CHIPV2_ACT, default 0.1 toggles/cycle at 25 MHz) propagated
# through the logic; macro power from the macro Liberty views. Voltage sources: the top-layer straps (no pads in this
# core). env: RUN, MACRO_LIB_DIR, OUT, [CHIPV2_ACT]
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib] 0]
read_liberty $L
foreach f [glob $::env(MACRO_LIB_DIR)/*.physical.lib] { read_liberty $f }
read_db $::env(RUN)/6_final.odb
read_sdc $::env(RUN)/6_final.sdc
set_propagated_clock [all_clocks]
read_spef $::env(RUN)/6_final.spef
set act [expr {[info exists ::env(CHIPV2_ACT)] ? $::env(CHIPV2_ACT) : 0.1}]
# CHIPV2_VCD: activity of the routed netlist over a decapsulation (shadow VCD of the power run) instead of a uniform
# input activity
if {[info exists ::env(CHIPV2_VCD)]} { read_vcd -scope shadow_chip $::env(CHIPV2_VCD); puts "CHIPV2_IR activity from $::env(CHIPV2_VCD)" } else { set_power_activity -input -activity $act }
report_power
# CHIPV2_MACRO_POWER: set_pdnsim_inst_power lines for the macros (their Liberty power tables are not physical); the
# SPICE-measured energies replace them (macro_power.py: worst case, one access per cycle at 25 MHz)
if {[info exists ::env(CHIPV2_MACRO_POWER)]} { source $::env(CHIPV2_MACRO_POWER); puts "CHIPV2_IR macro power from $::env(CHIPV2_MACRO_POWER)" }
# CHIPV2_BUMP_PITCH: with CHIPV2_SRC=BUMPS, supply points on a square grid of that pitch (um) instead of ideal straps
if {[info exists ::env(CHIPV2_BUMP_PITCH)]} { set_pdnsim_source_settings -bump_dx $::env(CHIPV2_BUMP_PITCH) -bump_dy $::env(CHIPV2_BUMP_PITCH) }
foreach n {VDD VSS} {
  set_pdnsim_net_voltage -net $n -voltage [expr {$n eq "VDD" ? 1.8 : 0.0}]
  # CHIPV2_VSRC_DIR: voltage-source files vsrc_<tag>_<net>.loc (PSM takes the net BTerms as ideal sources otherwise:
  # here the pins are every full-width met5 strap, i.e. an ideal supply over the whole core)
  set vs [expr {[info exists ::env(CHIPV2_VSRC_DIR)] ? [list -vsrc [glob $::env(CHIPV2_VSRC_DIR)/vsrc_*_$n.loc]] : {}}]
  analyze_power_grid -net $n {*}$vs -source_type [expr {[info exists ::env(CHIPV2_SRC)] ? $::env(CHIPV2_SRC) : "STRAPS"}] -voltage_file $::env(OUT)/ir_$n.csv -error_file $::env(OUT)/ir_$n.err
}
exit
