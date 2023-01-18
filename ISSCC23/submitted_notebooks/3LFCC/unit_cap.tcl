
# #########################	#
#   AC3E - UTFSM      		#
#   Project: 3LFCC    		#
#   Unit capacitor layout	#
#   01-09-2022        		#
# #########################	#

drc style drc(full)

box 0um 0um 30.3um 30.3um
paint {metal3 metal4 metal5}
box 10um 30.3um 20um 31.9um
paint {metal3 metal4 metal5}
box 30.3um 10um 31.9um 20um
paint {metal3 metal4 metal5}
box 0.15um 0.15um 30.15um 30.15um
paint {mimcap mimcap2}
box 0.23um 0.23um 30.07um 30.07um
paint {mimcapcontact mimcap2contact}

save unit_cap.mag