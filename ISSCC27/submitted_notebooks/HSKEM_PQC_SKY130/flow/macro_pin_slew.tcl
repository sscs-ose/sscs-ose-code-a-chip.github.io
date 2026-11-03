# Address-pin transitions of an NTT block's SRAM macro on the routed database with the extracted
# parasitics (Appendix B.4), at the typical corner. env: LIB LIB_MACRO ODB SDC SPEF
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
read_liberty $::env(LIB_MACRO)
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
foreach cac_pin [get_pins -hierarchical *u_macro/addr0*] {
  puts "PIN [get_property $cac_pin full_name] slew [get_property $cac_pin slew_max]"
}
