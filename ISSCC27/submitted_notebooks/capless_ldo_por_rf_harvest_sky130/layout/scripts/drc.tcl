cd /w/mag
load ldo_top
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
set n [drc listall count total]
puts "DRCTOTAL $n"
set fh [open drc_report.txt w]
foreach {why boxes} [drc listall why] {
  puts $fh "[llength $boxes]\t$why\t$boxes"
}
close $fh
quit -noprompt
