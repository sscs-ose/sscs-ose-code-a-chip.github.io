cd /w/mag/gdsrt
gds flatglob *
gds read ../ldo_top.gds
load ldo_top
select top cell
flatten ldo_top_gdsflat
load ldo_top_gdsflat
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
puts "GDSFLATDRC [drc listall count total]"
foreach {why boxes} [drc listall why] { puts "  [llength $boxes] $why" }
quit -noprompt
