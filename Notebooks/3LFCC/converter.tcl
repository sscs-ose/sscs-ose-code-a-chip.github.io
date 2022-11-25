
# #####################	#
#   AC3E - UTFSM      	#
#   Project: 3LFCC    	#
#   Converter layout	#
#   24-11-2022        	#
# #####################	#

set gap 30

#
box 0um 0um 10um 10um
getcell power_stage.mag
rotate 90

box 0um [expr {380 + $gap}]um 10um [expr {390 + $gap}]um
getcell flying_cap.mag
rotate 180

# connections
box 690um 330um 1300um [expr {390 + $gap}]um
paint metal4
box 691um 330um 1299um 360um
paint {via3 via4}

box 70um 330um 560um [expr {390 + $gap}]um
paint {metal3 metal5}
box 71um 330um 559um 360um
paint {via3 via4}

save