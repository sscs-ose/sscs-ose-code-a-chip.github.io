# Magic GDS 읽기만 (시간 재기). 환경 GDS·TOP·OUT·FLATGLOB
if {[info exists ::env(FLATGLOB)]} { foreach p $::env(FLATGLOB) { gds flatglob $p } }
gds read $::env(GDS)
load $::env(TOP)
set f [open $::env(OUT) w]; puts $f "read ok [box values]"; close $f
quit -noprompt
