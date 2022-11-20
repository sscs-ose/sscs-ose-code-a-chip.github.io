
# #########################	#
#   AC3E - UTFSM      		#
#   Project: 3LFCC    		#
#   Flying capacitor layout	#
#   11-11-2022        		#
# #########################	#

load cap_matrix_43x52.tcl

# terminal 1
box 10um 1658.8um 689.9um 1670um
paint {metal3 metal5}
box 10um 1660um 689.9um 1680um
paint metal4
box 10.2um 1660.2um 689.7um 1669.8um
paint {via3 via4}

# terminal 2
box 711.8um 1658.8um 1359.8um 1670.5um
paint metal4
box 711.8um 1660.5um 1359.8um 1680um
paint {metal3 metal5}
box 712um 1660.7um 1359.6um 1670.3um
paint {via3 via4}

#
save flying_cap.mag