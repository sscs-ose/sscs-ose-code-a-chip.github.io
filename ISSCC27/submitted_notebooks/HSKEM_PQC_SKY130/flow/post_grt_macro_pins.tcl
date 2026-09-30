# Post-global-route ECO for the OpenRAM-macro NTT point (ORFS hook POST_GLOBAL_ROUTE_TCL).
# The repair after global routing splits the long wires to the macro's address pins with
# minimum-size buffers, whose output transitions (0.26-0.35 ns) far exceed the macro's
# 0.04 ns limit; excluding that cell with DONT_USE_CELLS does not change the choice in this
# OpenROAD build. This hook upsizes exactly those buffers and re-routes the affected nets
# incrementally, as the flow itself does after its own repairs.
# SPDX-License-Identifier: Apache-2.0
# the weak buffers the repair uses for long wires (plain, clock and delay buffers of the smallest sizes)
set cac_weak {sky130_fd_sc_hd__clkbuf_1 sky130_fd_sc_hd__buf_1 sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__buf_2
              sky130_fd_sc_hd__clkdlybuf4s25_1 sky130_fd_sc_hd__clkdlybuf4s50_1}
set cac_count 0
global_route -start_incremental
foreach cac_pin [get_pins -hierarchical *u_macro/addr0*] {
  foreach cac_drv [get_pins -of_objects [get_nets -of_objects $cac_pin] -filter "direction == output"] {
    set cac_inst [get_cells -of_objects $cac_drv]
    if { [lsearch -exact $cac_weak [get_property $cac_inst ref_name]] >= 0 } {
      replace_cell $cac_inst sky130_fd_sc_hd__buf_8
      incr cac_count
    }
  }
}
puts "CAC_MACRO_PIN_ECO: upsized $cac_count address-pin buffers to sky130_fd_sc_hd__buf_8"
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
