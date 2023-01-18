
# #########################	#
#   AC3E - UTFSM      		#
#   Project: 3LFCC    		#
#   Flying capacitor layout	#
#   23-11-2022        		#
# #########################	#

set m 43
set n $env(VAR)
box 0 0 0 0
getcell unit_cap.mag
set boxS [box size]
set sizex [expr {[lindex $boxS 0] /2}]
set sizey [expr {[lindex $boxS 1] /2}]
undo
for {set i 0} {$i < $m} {incr i} {
	for {set j 0} {$j < $n} {incr j} {
		box [expr {$sizex*$i}] [expr {$sizey*$j}] [expr {$sizex*$i}] [expr {$sizey*$j}] 
		getcell unit_cap.mag
	}
}

set yoff [expr {$n * $sizey}]

# terminal 1
box 10um [expr {$yoff}] 689.9um [expr {$yoff + 1120}]  
paint {metal3 metal5}
box 10um [expr {$yoff + 120}] 689.9um [expr {$yoff + 2120}]  
paint metal4
box 10.2um [expr {$yoff + 140}] 689.7um [expr {$yoff + 1100}] 
paint {via3 via4}

# terminal 2
box 711.8um [expr {$yoff}] 1359.8um [expr {$yoff + 1170}] 
paint metal4
box 711.8um [expr {$yoff + 170}] 1359.8um [expr {$yoff + 2120}] 
paint {metal3 metal5}
box 712um [expr {$yoff + 190}] 1359.6um [expr {$yoff + 1150}] 
paint {via3 via4}

#
save flying_cap.mag

exit