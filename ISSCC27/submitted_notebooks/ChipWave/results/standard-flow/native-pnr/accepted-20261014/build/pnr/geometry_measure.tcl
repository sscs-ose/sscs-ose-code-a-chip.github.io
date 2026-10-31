set block [ord::get_db_block]
set d [$block getDieArea]
set core [$block getCoreArea]
set f [open $nebula_geometry_report/database_geometry.json w]
puts $f [format {{"dbu_per_micron": %d, "die_dbu": [%d,%d,%d,%d], "core_dbu": [%d,%d,%d,%d]}} [$block getDbUnitsPerMicron] [$d xMin] [$d yMin] [$d xMax] [$d yMax] [$core xMin] [$core yMin] [$core xMax] [$core yMax]]
close $f
set f [open $nebula_geometry_report/database_rows.tsv w]
puts $f "row\tsite\txmin\tymin\txmax\tymax\tsite_width\tsite_height\tcount\tspacing\torientation"
foreach row [$block getRows] {
  set box [$row getBBox]
  set site [$row getSite]
  puts $f "[$row getName]\t[$site getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]\t[$site getWidth]\t[$site getHeight]\t[$row getSiteCount]\t[$row getSpacing]\t[$row getOrient]"
}
close $f
set f [open $nebula_geometry_report/database_pin_locations.tsv w]
puts $f "port\tsignal_type\tstatus\tlayer\txmin\tymin\txmax\tymax"
foreach bt [$block getBTerms] {
  foreach pin [$bt getBPins] {
    foreach box [$pin getBoxes] {
      puts $f "[$bt getName]\t[$bt getSigType]\t[$pin getPlacementStatus]\t[[$box getTechLayer] getName]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]"
    }
  }
}
close $f
set f [open $nebula_geometry_report/database_ports.tsv w]
puts $f "port\tdirection\tsignal_type\tpin_count"
foreach bt [$block getBTerms] {puts $f "[$bt getName]\t[$bt getIoType]\t[$bt getSigType]\t[llength [$bt getBPins]]"}
close $f

set f [open $nebula_geometry_report/database_placed_instances.tsv w]
puts $f "instance\tmaster\ttype\tstatus\txmin\tymin\txmax\tymax\tfootprint_dbu2"
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set box [$inst getBBox]
  puts $f "[$inst getName]\t[$master getName]\t[$master getType]\t[$inst getPlacementStatus]\t[$box xMin]\t[$box yMin]\t[$box xMax]\t[$box yMax]\t[expr {wide([$master getWidth])*[$master getHeight]}]"
}
close $f
set f [open $nebula_geometry_report/database_pin_rules.tsv w]
puts $f "layer\tspacing"
foreach name {met2 met3} {
  set layer [[ord::get_db_tech] findLayer $name]
  puts $f "$name\t[$layer getSpacing]"
}
close $f
check_placement -verbose

set f [open $nebula_geometry_report/database_power_connections.tsv w]
puts $f "instance\tmaster\tpin\tsignal_type\tnet"
foreach inst [$block getInsts] {
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] ni {POWER GROUND}} {continue}
    set net [$it getNet]
    set netname ""
    if {$net ne "NULL"} {set netname [$net getName]}
    puts $f "[$inst getName]\t[[$inst getMaster] getName]\t[$mt getName]\t[$mt getSigType]\t$netname"
  }
}
close $f
