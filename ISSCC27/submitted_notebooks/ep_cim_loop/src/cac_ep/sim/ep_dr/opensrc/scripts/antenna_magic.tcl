# Magic antenna 검사 (OpenLane magic antenna 절차와 같음). 환경 GDS·TOP·OUTD. 결과: 표준출력 "Cell: … " 줄 + antenna.fb
set gds $::env(GDS); set top $::env(TOP); set outd $::env(OUTD)
gds read $gds
load $top
select top cell
extract path $outd
extract do local
extract no capacitance
extract no coupling
extract no resistance
extract no adjust
extract unique
extract all
feedback clear
antennacheck
puts "ANTENNA_FEEDBACK_COUNT [feedback count]"
feedback save $outd/antenna.fb
quit -noprompt
