# Magic 추출 (LVS 용) + antenna — 칩. ext_magic.tcl 사본 + antennacheck + 단계 시각. 환경 GDS·TOP·OUT (netlist 경로).
set gds $::env(GDS); set top $::env(TOP); set out $::env(OUT)
puts "STAGE start [exec date +%s%3N]"
# 환경 FLATGLOB (빈칸으로 나눈 셀 이름 틀): 읽을 때 평탄화. 소자 층이 계층에 나뉜 셀 (diff 는 자식, nsdm·psdm·hvi·nwell 은 부모) 은 Magic 이 셀마다 type 을 정해 소자를 잘못 읽는다 (10/28)
if {[info exists ::env(FLATGLOB)]} { foreach p $::env(FLATGLOB) { gds flatglob $p } }
gds read $gds
puts "STAGE gds_read [exec date +%s%3N]"
load $top
select top cell
port makeall
extract path [file dirname $out]
extract do local
extract no capacitance
extract no coupling
extract no resistance
extract no adjust
extract unique
extract all
puts "STAGE extract [exec date +%s%3N]"
ext2spice lvs
ext2spice -o $out $top
puts "STAGE ext2spice [exec date +%s%3N]"
if {[info exists ::env(ANT)] && $::env(ANT) == 1} {
  feedback clear
  antennacheck
  puts "ANTENNA_FEEDBACK_COUNT [feedback count]"
  feedback save [file dirname $out]/antenna.fb
  puts "STAGE antenna [exec date +%s%3N]"
}
quit -noprompt
