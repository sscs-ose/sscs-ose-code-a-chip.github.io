gds read ../microrobot_clock.gds
load microrobot_clock
select top cell
expand
box values -40um 0um 650um 120um
drc check
drc catchup
set f [open drc.txt w]
puts $f "DRC_ERRORS [drc list count total]"
puts $f [drc listall why]
close $f
extract all
ext2spice lvs
ext2spice -o clock_lvs.spice
puts "OPENTCAD_FLOW_DONE"
quit -noprompt
