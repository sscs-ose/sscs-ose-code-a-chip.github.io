# Worst setup slack at the input pins (addr0/din0/web0/csb0) of selected macros, ss, SPEF + SPICE views.
# env: RUN, MACRO_LIB_DIR, MACROS (instance name patterns)
set L [lindex [glob /opt/eda/pdks-openram/ciel/sky130/versions/*/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib] 0]
read_liberty $L
foreach f [glob $::env(MACRO_LIB_DIR)/*.physical.lib] { read_liberty $f }
read_db $::env(RUN)/6_final.odb
read_sdc $::env(RUN)/6_final.sdc
set_propagated_clock [all_clocks]
read_spef $::env(RUN)/6_final.spef
foreach pat $::env(MACROS) {
  foreach inst [get_cells -hierarchical $pat] {
    set worst 1e9; set wp ""
    foreach pin [get_pins -of_objects $inst -filter "direction == input"] {
      set n [get_full_name $pin]
      if {[string match "*clk0" $n]} { continue }
      set s [get_property $pin slack_max]
      regsub {[[0-9]+]$} [lindex [split $n /] end] "" grp
      if {$s ne "" && (![info exists g($grp)] || $s < $g($grp))} { set g($grp) $s }
      if {$s ne "" && $s < $worst} { set worst $s; set wp $n }
    }
    puts "PINSLACK [get_full_name $inst] worst=$worst at $wp groups: [lsort [array get g]]"; array unset g
  }
}
exit
