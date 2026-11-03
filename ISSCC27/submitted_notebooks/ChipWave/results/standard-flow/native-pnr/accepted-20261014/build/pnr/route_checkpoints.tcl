# Preserve the same WIP after each native route and legalized diode ECO.
proc nebula_route_checkpoint {stage} {
  set database $::env(RESULTS_DIR)/5_2_route-progress.odb
  write_db $database
  set instances [llength [[ord::get_db_block] getInsts]]
  set antennas [check_antennas]
  puts [exec python3 -B $::env(WORK_HOME)/checkpoint.py $stage $database $instances $antennas]
}
rename detailed_route nebula_native_detailed_route
proc detailed_route {args} {
  set result [uplevel 1 [list nebula_native_detailed_route {*}$args]]
  nebula_route_checkpoint detailed_route
  return $result
}
rename repair_antennas nebula_native_repair_antennas
proc repair_antennas {args} {
  set before [llength [[ord::get_db_block] getInsts]]
  set result [uplevel 1 [list nebula_native_repair_antennas {*}$args]]
  if {[llength [[ord::get_db_block] getInsts]]>$before} {
    check_placement -verbose
    nebula_route_checkpoint antenna_legalized
  }
  return $result
}
