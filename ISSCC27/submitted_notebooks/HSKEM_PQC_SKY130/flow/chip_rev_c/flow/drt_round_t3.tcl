# (tier-3 clone copy of chip_v2/drt_round.tcl, plus the optional diode padding CHIPV2_DIODE_PAD)
# One round of the split detailed route of chip v2, run as its own session in the ORFS environment
# (make run): read the latest routed checkpoint, repair the antennas with diodes (mode antenna) or not
# (mode drc), detailed-route again from the existing routes with the arguments of ORFS detail_route.tcl,
# and write the next checkpoint. The old chip's resumed route (5_2_route_r6) shows that the router keeps
# the existing routes and repairs only the violations.
# env: CHIPV2_IN, CHIPV2_OUT (odb names in RESULTS_DIR), CHIPV2_TAG, CHIPV2_MODE (antenna | drc),
#      DETAILED_ROUTE_END_ITERATION
source $::env(SCRIPTS_DIR)/load.tcl
load_design $::env(CHIPV2_IN) 5_1_grt.sdc
set_propagated_clock [all_clocks]
set tag $::env(CHIPV2_TAG)

set before [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_${tag}_before.log]
puts "CHIPV2_ROUND=$tag mode=$::env(CHIPV2_MODE) antenna_violations_before=$before"
if { $::env(CHIPV2_MODE) == "antenna" } {
  if {[info exists ::env(CHIPV2_RENAME_DIODES)] && $::env(CHIPV2_RENAME_DIODES) == 1} {
    # repair_antennas names a new diode ANTENNA_<number of diodes>; once diodes were removed (ECO e1) that
    # name can exist already, the instance creation fails and setDiodeLoc crashes on the null instance
    # (round a5). Renaming the existing diodes clears every such collision; names do not matter to LVS.
    # the new name carries the round tag: a plain ANTD_<n> can exist already from an earlier round, and
    # dbInst rename then fails silently (round a8 crashed so); every rename is checked
    set rn 0
    foreach inst [[ord::get_db_block] getInsts] {
      if {[string match "ANTENNA_*" [$inst getName]]} {
        set new "ANTD_${tag}_[string range [$inst getName] 8 end]"
        $inst rename $new
        if {[$inst getName] ne $new} { error "diode rename to $new failed" }
        incr rn
      }
    }
    set left 0
    foreach inst [[ord::get_db_block] getInsts] { if {[string match "ANTENNA_*" [$inst getName]]} { incr left } }
    if {$left} { error "$left ANTENNA_* instances left after renaming" }
    puts "CHIPV2_ROUND=$tag renamed_diodes=$rn"
  }
  if {[info exists ::env(CHIPV2_DIODE_PAD)] && $::env(CHIPV2_DIODE_PAD) > 0} {
    # (tier-3 clone) keep new diodes CHIPV2_DIODE_PAD sites away from their neighbours: a diode legalized flush
    # against a flip-flop took the access point of its RESET_B pin (DRT-1231, round t3e r1)
    set_placement_padding -masters sky130_fd_sc_hd__diode_2       -left $::env(CHIPV2_DIODE_PAD) -right $::env(CHIPV2_DIODE_PAD)
    puts "CHIPV2_ROUND=$tag diode_padding_sites=$::env(CHIPV2_DIODE_PAD)"
  }
  set inserted [repair_antennas]
  puts "CHIPV2_ROUND=$tag repair_antennas_inserted=$inserted"
}

# optional routing blockage, CHIPV2_ROUTE_BLOCKAGE = "<layer> x0 y0 x1 y1" (um): keeps the router off a spot it keeps
# shorting (t3e: the met3 short of net2421 with VDD at the top-right corner of the ekPKE macro)
if {[info exists ::env(CHIPV2_ROUTE_BLOCKAGE)]} {
  lassign $::env(CHIPV2_ROUTE_BLOCKAGE) lname bx0 by0 bx1 by1
  set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set layer [[ord::get_db_tech] findLayer $lname]
  odb::dbObstruction_create $blk $layer [expr {round($bx0*$dbu)}] [expr {round($by0*$dbu)}] [expr {round($bx1*$dbu)}] [expr {round($by1*$dbu)}]
  puts "CHIPV2_ROUND=$tag routing_blockage=$lname ($bx0,$by0)-($bx1,$by1)"
}
set additional_args ""
append_env_var additional_args dbProcessNode -db_process_node 1
append_env_var additional_args OR_SEED -or_seed 1
append_env_var additional_args OR_K -or_k 1
append_env_var additional_args VIA_IN_PIN_MIN_LAYER -via_in_pin_bottom_layer 1
append_env_var additional_args VIA_IN_PIN_MAX_LAYER -via_in_pin_top_layer 1
append_env_var additional_args DISABLE_VIA_GEN -disable_via_gen 0
append_env_var additional_args REPAIR_PDN_VIA_LAYER -repair_pdn_vias 1
append_env_var additional_args DETAILED_ROUTE_END_ITERATION -droute_end_iter 1
if {[info exists ::env(CHIPV2_DR_EXTRA)]} { append additional_args " $::env(CHIPV2_DR_EXTRA)" }
append additional_args " -verbose 1"
log_cmd detailed_route -output_drc $::env(REPORTS_DIR)/5_route_drc_${tag}.rpt \
  -output_maze $::env(RESULTS_DIR)/maze_${tag}.log {*}$additional_args -drc_report_iter_step 5

set after [check_antennas -report_file $::env(REPORTS_DIR)/drt_antennas_${tag}.log]
puts "CHIPV2_ROUND=$tag antenna_violations_after=$after"
if { ![design_is_routed] } {
  error "Design has unrouted nets."
}
report_design_area
orfs_write_db $::env(RESULTS_DIR)/$::env(CHIPV2_OUT)
puts "CHIPV2_ROUND=$tag written=$::env(CHIPV2_OUT)"
