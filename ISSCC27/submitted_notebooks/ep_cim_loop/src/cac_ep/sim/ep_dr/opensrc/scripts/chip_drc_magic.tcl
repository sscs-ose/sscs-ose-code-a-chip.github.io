# Magic DRC — 칩 (core·die). drc_magic.tcl 사본 + 단계 시각 (STAGE <이름> <ms>). 환경 GDS·TOP·OUT.
set gds $::env(GDS); set top $::env(TOP); set out $::env(OUT)
puts "STAGE start [exec date +%s%3N]"
# 환경 FLATGLOB (빈칸으로 나눈 셀 이름 틀): 읽을 때 평탄화. 소자 층이 계층에 나뉜 셀 (diff 는 자식, nsdm·psdm·hvi·nwell 은 부모) 은 Magic 이 셀마다 type 을 정해 소자를 잘못 읽는다 (10/28)
if {[info exists ::env(FLATGLOB)]} { foreach p $::env(FLATGLOB) { gds flatglob $p } }
gds read $gds
puts "STAGE gds_read [exec date +%s%3N]"
load $top
select top cell
expand
set bb [box values]; set g 400
box [expr {[lindex $bb 0]-$g}] [expr {[lindex $bb 1]-$g}] [expr {[lindex $bb 2]+$g}] [expr {[lindex $bb 3]+$g}]
drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "STAGE drc [exec date +%s%3N]"
set res [drc listall why]
set n 0
foreach {why boxes} $res { incr n [llength $boxes] }
set f [open $out w]
puts $f "total $n   (위반 상자 수, drc count total = [drc list count total])"
foreach {why boxes} $res { puts $f [format "%6d  %s" [llength $boxes] $why] }
close $f
set f [open $out.boxes w]
foreach {why boxes} $res { foreach b $boxes { puts $f "$b\t$why" } }
close $f
puts "STAGE drc_list [exec date +%s%3N]"
quit -noprompt
