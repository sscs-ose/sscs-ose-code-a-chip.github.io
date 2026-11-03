# Magic DRC (sky130A.tech, drc(full) 스타일) — 블록 하나. drc_magic.sh 가 부른다 (환경 GDS·TOP·OUT).
set gds $::env(GDS); set top $::env(TOP); set out $::env(OUT)
gds read $gds
load $top
select top cell
expand
# 셀 bbox 그대로면 bbox 가장자리 바깥에 찍히는 위반 (예: 끝 도형 폭 위반) 이 빠진다 → 2 µm 넓힌 상자로 검사
set bb [box values]; set g 400
box [expr {[lindex $bb 0]-$g}] [expr {[lindex $bb 1]-$g}] [expr {[lindex $bb 2]+$g}] [expr {[lindex $bb 3]+$g}]
drc euclidean on
drc style drc(full)
drc check
drc catchup
set res [drc listall why]
set n 0
foreach {why boxes} $res { incr n [llength $boxes] }
set f [open $out w]
puts $f "total $n   (위반 상자 수, drc count total = [drc list count total])"
foreach {why boxes} $res { puts $f [format "%6d  %s" [llength $boxes] $why] }
close $f
quit -noprompt
