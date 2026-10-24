# Generic post-detailed-route repair, validated against pinned OpenROAD in DAC
# round 1.  It deliberately uses detailed routes, not a replacement global route.
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
set_thread_count $::env(DRT_THREADS)
source $::env(SCRIPTS_DIR)/openroad/common/dpl_cell_pad.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_routing_layers.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_layer_adjustments.tcl
set_macro_extension $::env(GRT_MACRO_EXTENSION)

if {![grt::have_detailed_routes]} {
    error "DAC27 repair requires a detailed-routed input database"
}
set summary [open "$::env(STEP_DIR)/repair_summary.tsv" w]
set before [check_antennas -verbose -report_file "$::env(STEP_DIR)/before.antenna.rpt"]
puts $summary "baseline\t$before"
flush $summary
set remaining $before
set passes 0
set route_drvs $::env(DAC27_INPUT_ROUTE_DRVS)
set diode_master [lindex [split $::env(DIODE_CELL) "/"] 0]

set min_layer $::env(RT_MIN_LAYER)
if {[info exists ::env(DRT_MIN_LAYER)]} { set min_layer $::env(DRT_MIN_LAYER) }
set max_layer $::env(RT_MAX_LAYER)
if {[info exists ::env(DRT_MAX_LAYER)]} { set max_layer $::env(DRT_MAX_LAYER) }

while {$remaining > 0 && $passes < 2} {
    incr passes
    puts "DAC27_POST_DRT_REPAIR_BEGIN pass=$passes iterations=1 ratio_margin=15 diode=$diode_master"
    repair_antennas $diode_master -iterations 1 -ratio_margin 15
    # Pinned OpenROAD edf00dff: RepairAntennas.cpp protects existing instances
    # and legalizes new diodes internally, inside GlobalRouter's incremental
    # routing update. An extra common/dpl.tcl here would re-place/mirror routed
    # cells after that update. Keep the independent placement check below.
    check_placement -verbose
    write_db "$::env(STEP_DIR)/pass_${passes}_after_repair.odb"
    detailed_route \
        -bottom_routing_layer $min_layer \
        -top_routing_layer $max_layer \
        -output_drc "$::env(STEP_DIR)/pass_${passes}.drc" \
        -droute_end_iter $::env(DRT_OPT_ITERS) \
        -or_seed 42 -verbose 1
    check_placement -verbose
    set route_drvs [drt::detailed_route_num_drvs]
    set remaining [check_antennas -verbose -report_file "$::env(STEP_DIR)/pass_${passes}.antenna.rpt"]
    write_db "$::env(STEP_DIR)/pass_${passes}_after_route.odb"
    puts $summary "pass\t$passes\t$remaining\t$route_drvs"
    flush $summary
    if {$route_drvs != 0} {
        close $summary
        error "DAC27 post-DRT reroute has $route_drvs routing violations"
    }
}
puts $summary "final\t$passes\t$remaining\t$route_drvs"
close $summary
if {$remaining != 0} {
    error "DAC27 antenna repair exhausted two passes with $remaining violations"
}
if {$route_drvs != 0} {
    error "DAC27 input has $route_drvs routing violations"
}
# Magic.StreamOut needs the native die rectangle as well as scalar areas.
# Recompute both rectangles from this database, including for zero-pass resumed
# runs. This follows the pinned floorplan.tcl DBU-to-micron conversion; it does
# not inherit geometry metadata from the pre-repair historical state.
set die_rect [$::block getDieArea]
set core_rect [$::block getCoreArea]
set die_bbox [list]
set core_bbox [list]
foreach coord [list [$die_rect xMin] [$die_rect yMin] [$die_rect xMax] [$die_rect yMax]] {
    lappend die_bbox [expr {1.0 * $coord / $::dbu}]
}
foreach coord [list [$core_rect xMin] [$core_rect yMin] [$core_rect xMax] [$core_rect yMax]] {
    lappend core_bbox [expr {1.0 * $coord / $::dbu}]
}
write_metric_str "design__die__bbox" $die_bbox
write_metric_str "design__core__bbox" $core_bbox
write_views
puts "DAC27_POST_DRT_COMPLETE passes=$passes antenna=$remaining route_drvs=$route_drvs"
