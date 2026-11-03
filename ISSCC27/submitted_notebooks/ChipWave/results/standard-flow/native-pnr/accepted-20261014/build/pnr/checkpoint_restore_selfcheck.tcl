set ::env(NEBULA_ECO_SOURCE) build/pnr/history/electrical-baseline/6_final.odb
if {[catch {
set source_database build/pnr/results/6_final.odb
if {[info exists ::env(NEBULA_ECO_SOURCE)]} {set source_database $::env(NEBULA_ECO_SOURCE)}
read_db $source_database
set block [ord::get_db_block]
set count_before [llength [$block getInsts]]
set diode_before 0
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getType] eq "CORE_ANTENNACELL"} {incr diode_before}
}
remove_fillers
set diode_after 0
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getType] eq "CORE_ANTENNACELL"} {incr diode_after}
}
if {$diode_before != $diode_after} {error "ECO preparation removed antenna cells"}
set wires 0
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 $net clearGuides
 set wire [$net getWire]
 if {$wire ne "NULL"} {incr wires; odb::dbWire_destroy $wire}
}
if {$diode_after != 49 || $wires != 16690} {error "Frozen baseline restoration self-check failed"}
check_placement -verbose
write_db build/pnr/checkpoint_restore_selfcheck.odb
set f [open reports/pnr/checkpoint_restore_selfcheck.json w]
puts $f [format {{"schema_version":1,"status":"prepared","source_database":"%s","prepared_database":"build/pnr/checkpoint_restore_selfcheck.odb","instances_before":%d,"instances_after":%d,"antenna_instances_preserved":%d,"signal_detailed_wires_removed":%d,"global_guides_cleared":true,"scope":"Same final WIP, remove fillers and ordinary signal/clock wires; preserve cells, CTS, PDN and diodes, then regenerate global guides before native repair; final checks remain required."}} $source_database $count_before [llength [$block getInsts]] $diode_after $wires]
close $f
} message options]} {puts stderr $message;puts stderr [dict get $options -errorinfo];exit 1}
exit
