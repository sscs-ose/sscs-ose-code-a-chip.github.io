if {[catch {
read_db build/pnr/results/6_final.odb
set b [ord::get_db_block]
set f [open reports/pnr/structural_fanout.tsv w]
puts $f "net	driver_count	sink_count	inout_count"
foreach n [$b getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 set drivers 0; set sinks 0; set inouts 0
 foreach t [$n getITerms] {
  switch [[$t getMTerm] getIoType] {INPUT {incr sinks} OUTPUT {incr drivers} INOUT {incr inouts}}
 }
 foreach t [$n getBTerms] {
  switch [$t getIoType] {INPUT {incr drivers} OUTPUT {incr sinks} INOUT {incr inouts}}
 }
 puts $f "[$n getName]	$drivers	$sinks	$inouts"
}
close $f
set f [open reports/pnr/placed_area.tsv w]
puts $f "instance	master	type	footprint_dbu2"
foreach i [$b getInsts] {
 set m [$i getMaster]
 puts $f "[$i getName]	[$m getName]	[$m getType]	[expr {wide([$m getWidth])*[$m getHeight]}]"
}
close $f
} e]} {puts stderr $e;exit 1}
exit
