# Worst setup and hold slack of the paths that start at an SRAM macro and of those that end at one (used by
# scripts/sta_macro_bound.sh's follow-up, to see the macro paths themselves rather than the chip's worst path).
# env: LIB SDC SPEF ODB EXTRA_LIBS
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
foreach lib $::env(EXTRA_LIBS) { read_liberty $lib }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
set macros {}
foreach c [all_registers -cells] { if {[string match "sky130_sram*" [get_property $c ref_name]]} { lappend macros $c } }
puts "RESULT macros [llength $macros]"
foreach {tag args} [list from_macro_setup "-path_delay max -from \$macros" to_macro_setup "-path_delay max -to \$macros" \
                         from_macro_hold "-path_delay min -from \$macros" to_macro_hold "-path_delay min -to \$macros"] {
  puts "SECTION $tag"
  eval report_checks $args -format end -group_path_count 1
}
puts "SECTION END"
exit
