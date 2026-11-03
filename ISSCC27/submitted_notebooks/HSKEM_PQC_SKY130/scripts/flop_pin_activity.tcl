# Apply the flip-flop pin activity of scripts/flop_pin_activity.py (source after read_vcd). env: FLOP_ACT (the .tsv)
# Matches each D/Q/Q_N/RESET_B/SET_B/DE pin of a flip-flop to its net's measured density and duty; clock pins are left to
# the clock analysis. SPDX-License-Identifier: Apache-2.0
set act [dict create]
set fh [open $::env(FLOP_ACT)]
while {[gets $fh l] >= 0} {
  if {[string index $l 0] eq "#"} continue
  lassign [split $l "\t"] nm d u
  dict set act $nm [list $d $u]
}
close $fh
set n_set 0; set n_miss 0
foreach c [all_registers -cells] {
  if {[string match "sky130_sram*" [get_property $c ref_name]]} continue
  foreach p [get_pins -of_objects $c] {
    if {[lsearch -exact {D Q Q_N RESET_B SET_B DE} [get_property $p lib_pin_name]] < 0} continue
    set net [get_nets -quiet -of_objects $p]
    if {$net eq ""} { incr n_miss; continue }
    set key [string map {"\\" ""} [get_full_name $net]]
    if {[dict exists $act $key]} {
      lassign [dict get $act $key] d u
      set_power_activity -pins $p -density $d -duty $u
      incr n_set
    } else { incr n_miss }
  }
}
puts "RESULT flop_pins_annotated $n_set flop_pins_missing $n_miss"
