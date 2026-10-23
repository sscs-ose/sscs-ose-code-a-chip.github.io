# Post-global-route ECO for the OpenRAM-macro NTT points (ORFS hook POST_GLOBAL_ROUTE_TCL).
# The repair after global routing splits the long wires to the macro's address pins with
# minimum-size buffers, whose output transitions (0.26-0.35 ns) far exceed the macro's
# 0.04 ns limit; excluding that cell with DONT_USE_CELLS does not change the choice in this
# OpenROAD build. Upsizing alone is not enough: with the driver 25-70 um away, the wire still
# leaves 0.05-0.07 ns at the pin, while drivers within about 10 um meet the limit. This hook
# therefore makes every address-pin driver a buf_12 (a buf_16 loads its own input too much),
# moves it to the edge of the macro's placement halo next to its pin (flow/macro_place_ntt.tcl leaves
# room on both pin rows), strengthens the cell that drives it, legalizes, and re-routes the affected
# nets incrementally, as the flow itself does after its own repairs.
# SPDX-License-Identifier: Apache-2.0
# the buffers the repair may leave on these nets (plain, clock and delay buffers up to buf_16)
set cac_bufs {sky130_fd_sc_hd__clkbuf_1 sky130_fd_sc_hd__buf_1 sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__buf_2
              sky130_fd_sc_hd__clkdlybuf4s25_1 sky130_fd_sc_hd__clkdlybuf4s50_1 sky130_fd_sc_hd__buf_4
              sky130_fd_sc_hd__buf_6 sky130_fd_sc_hd__buf_8 sky130_fd_sc_hd__buf_12 sky130_fd_sc_hd__buf_16}
set cac_strong sky130_fd_sc_hd__buf_12
set cac_block [ord::get_db_block]
set cac_dbu [$cac_block getDbUnitsPerMicron]
# the halo keeps standard cells this far from the macro; the driver goes 1 um outside it
# (MACRO_PLACE_HALO, 10 um in config.mk, is not passed to this stage and the database keeps no halo)
proc cac_halo_dbu {inst} {
  set um 10.0
  if { [info exists ::env(MACRO_PLACE_HALO)] } { set um [lindex $::env(MACRO_PLACE_HALO) 0] }
  set h [$inst getHalo]
  if { $h != "NULL" } { return [$h xMin] }
  return [expr {round($um * [[ord::get_db_block] getDbUnitsPerMicron])}]
}
set cac_count 0
set cac_upsized 0
global_route -start_incremental
foreach cac_pin [get_pins -hierarchical *u_macro/addr0*] {
  foreach cac_drv [get_pins -of_objects [get_nets -of_objects $cac_pin] -filter "direction == output"] {
    set cac_inst [get_cells -of_objects $cac_drv]
    if { [lsearch -exact $cac_bufs [get_property $cac_inst ref_name]] < 0 } { continue }
    replace_cell $cac_inst $cac_strong
    # pin centre and macro outline, in database units
    set cac_mi [$cac_block findInst [get_full_name [get_cells -of_objects $cac_pin]]]
    set cac_pb [[$cac_mi findITerm [get_property $cac_pin lib_pin_name]] getBBox]
    set px [expr {([$cac_pb xMin] + [$cac_pb xMax]) / 2}]; set py [expr {([$cac_pb yMin] + [$cac_pb yMax]) / 2}]
    set mb [$cac_mi getBBox]
    set cac_gap [expr {[cac_halo_dbu $cac_mi] + $cac_dbu}]
    # the macro edge nearest to the pin decides where the driver goes
    set d [list [expr {$px - [$mb xMin]}] [expr {[$mb xMax] - $px}] [expr {$py - [$mb yMin]}] [expr {[$mb yMax] - $py}]]
    set side [lsearch -exact $d [tcl::mathfunc::min {*}$d]]
    switch $side {
      0 { set x [expr {[$mb xMin] - $cac_gap - 4000}]; set y $py }
      1 { set x [expr {[$mb xMax] + $cac_gap}];        set y $py }
      2 { set x $px; set y [expr {[$mb yMin] - $cac_gap - 3000}] }
      3 { set x $px; set y [expr {[$mb yMax] + $cac_gap}] }
    }
    set cac_di [$cac_block findInst [get_full_name $cac_inst]]
    $cac_di setLocation $x $y
    $cac_di setPlacementStatus PLACED
    incr cac_count
    # the moved buffer's input net is now longer: give its driver (a weak buffer or gate) drive
    # strength 4 of the same function, so that the buffer's own input transition stays short
    set cac_in [get_pins -of_objects $cac_inst -filter "direction == input"]
    foreach cac_up [get_pins -of_objects [get_nets -of_objects $cac_in] -filter "direction == output"] {
      # a top-level input port has no cell to resize
      if { [catch {get_cells -of_objects $cac_up} cac_uc] || $cac_uc eq "" } { continue }
      set cac_ref [get_property $cac_uc ref_name]
      if { [lsearch -exact $cac_bufs $cac_ref] >= 0 } {
        set cac_new sky130_fd_sc_hd__buf_8
      } else {
        regsub {_[0-2]$} $cac_ref _4 cac_new
      }
      if { $cac_new ne $cac_ref && [get_lib_cells -quiet */$cac_new] ne "" } {
        replace_cell $cac_uc $cac_new
        incr cac_upsized
      }
    }
  }
}
puts "CAC_MACRO_PIN_ECO: placed $cac_count address-pin drivers ($cac_strong) at the macro halo, upsized $cac_upsized of their drivers"
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
