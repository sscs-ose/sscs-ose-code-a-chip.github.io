	
# #####################	#
#   AC3E - UTFSM      	#
#   Project: 3LFCC    	#
#   25-11-2022        	#
# #####################	#

save core.mag
save converter.mag
save power_stage.mag
source power_stage.tcl
load converter.mag
box  0 0 0 0
source converter.tcl
load core.mag
box 0 0 0 0

set LS1 1292
set LS2 640
set LS3 550
set LS4 33
set yoff 403.5
set ypos [expr {$yoff - 29.49}]

# Converter
box 0um 0 10um 10um
getcell converter.mag

# VH
box 10um [expr {$yoff}]um 1372um [expr {$yoff + 3}]um
paint metal1
box 1370um [expr {$yoff}]um 1372um [expr {$yoff + 3}]um
label VLS east metal1

# VDD
box 10um [expr {$yoff + 3.5}]um 1372um [expr {$yoff + 6}]um
paint metal1
box 1370um [expr {$yoff + 3.5}]um 1372um [expr {$yoff + 6}]um
label VDD west metal1

# GND
box 10um [expr {$yoff + 12.5}]um 1372um [expr {$yoff + 15.5}]um
paint {metal1 metal2}
box 10.05um [expr {$yoff + 12.55}]um 1371.95um [expr {$yoff + 15.45}]um
paint m2contact
box 25um 375um 30um [expr {$yoff + 15.5}]um
paint metal2
box 25.05um 375.05um 29.95um 379.95um
paint m3contact
box 25um 310um 30um 380um
paint metal3


# LS1
box [expr {$LS1}]um [expr {$ypos}]um [expr {$LS1}]um [expr {$ypos}]um
getcell level_shifter.mag
rotate 90
box [expr {$LS1 + 20.47}]um 335um [expr {$LS1 + 23.47}]um [expr {$ypos + 0.5}]um
paint {metal2 metal3 metal4 metal5}
box [expr {$LS1 + 20.62}]um 335.15um [expr {$LS1 + 23.32}]um 341.85um
paint {m3contact via3 via4}
box [expr {$LS1 + 20.3}]um [expr {$ypos + 24}]um [expr {$LS1 + 21.3}]um [expr {$yoff + 15.5}]um
paint metal2
box [expr {$LS1 + 20.35}]um [expr {$ypos + 24.05}]um [expr {$LS1 + 21.25}]um [expr {$ypos + 26.95}]um
paint m2contact
box [expr {$LS1 + 15.92}]um [expr {$ypos + 25}]um [expr {$LS1 + 16.35}]um [expr {$yoff + 6}]um
paint metal2
box [expr {$LS1 + 15.97}]um [expr {$ypos + 25.05}]um [expr {$LS1 + 16.3}]um [expr {$ypos + 27.35}]um
paint m2contact
box [expr {$LS1 + 15.97}]um [expr {$yoff + 3.55}]um [expr {$LS1 + 16.3}]um [expr {$yoff + 5.95}]um
paint m2contact
box [expr {$LS1 + 17.5}]um [expr {$ypos + 28.65}]um [expr {$LS1 + 18.5}]um [expr {$yoff + 7.5}]um
paint metal2
box [expr {$LS1 + 17.5}]um [expr {$yoff + 6.5}]um 1372um [expr {$yoff + 7.5}]um
paint metal1
box [expr {$LS1 + 17.55}]um [expr {$yoff + 6.55}]um [expr {$LS1 + 18.45}]um [expr {$yoff + 7.45}]um
paint m2contact
box 1371um [expr {$yoff + 6.5}]um 1372um [expr {$yoff + 7.5}]um
label D1 west metal1

# LS2
box [expr {$LS2}]um [expr {$ypos}]um [expr {$LS2}]um [expr {$ypos}]um
getcell level_shifter.mag
rotate 90
box [expr {$LS2 + 20.47}]um 335um [expr {$LS2 + 23.47}]um [expr {$ypos + 0.5}]um
paint {metal2 metal3 metal4 metal5}
box [expr {$LS2 + 20.62}]um 335.15um [expr {$LS2 + 23.32}]um 341.85um
paint {m3contact via3 via4}
box [expr {$LS2 + 20.3}]um [expr {$ypos + 24}]um [expr {$LS2 + 21.3}]um [expr {$yoff + 15.5}]um
paint metal2
box [expr {$LS2 + 20.35}]um [expr {$ypos + 24.05}]um [expr {$LS2 + 21.25}]um [expr {$ypos + 26.95}]um
paint m2contact
box [expr {$LS2 + 15.92}]um [expr {$ypos + 25}]um [expr {$LS2 + 16.35}]um [expr {$yoff + 6}]um
paint metal2
box [expr {$LS2 + 15.97}]um [expr {$ypos + 25.05}]um [expr {$LS2 + 16.3}]um [expr {$ypos + 27.35}]um
paint m2contact
box [expr {$LS2 + 15.97}]um [expr {$yoff + 3.55}]um [expr {$LS2 + 16.3}]um [expr {$yoff + 5.95}]um
paint m2contact
box [expr {$LS2 + 17.5}]um [expr {$ypos + 28.65}]um [expr {$LS2 + 18.5}]um [expr {$yoff + 9}]um
paint metal2
box [expr {$LS2 + 17.5}]um [expr {$yoff + 8}]um 1372um [expr {$yoff + 9}]um
paint metal1
box [expr {$LS2 + 17.55}]um [expr {$yoff + 8.05}]um [expr {$LS2 + 18.45}]um [expr {$yoff + 8.95}]um
paint m2contact
box 1371um [expr {$yoff + 8}]um 1372um [expr {$yoff + 9}]um
label D2 west metal1

# LS3
box [expr {$LS3}]um [expr {$ypos}]um [expr {$LS3}]um [expr {$ypos}]um
getcell level_shifter.mag
rotate 90
box [expr {$LS3 + 20.47}]um 335um [expr {$LS3 + 23.47}]um [expr {$ypos + 0.5}]um
paint {metal2 metal3 metal4 metal5}
box [expr {$LS3 + 20.62}]um 335.15um [expr {$LS3 + 23.32}]um 341.85um
paint {m3contact via3 via4}
box [expr {$LS3 + 20.3}]um [expr {$ypos + 24}]um [expr {$LS3 + 21.3}]um [expr {$yoff + 15.5}]um
paint metal2
box [expr {$LS3 + 20.35}]um [expr {$ypos + 24.05}]um [expr {$LS3 + 21.25}]um [expr {$ypos + 26.95}]um
paint m2contact
box [expr {$LS3 + 15.92}]um [expr {$ypos + 25}]um [expr {$LS3 + 16.35}]um [expr {$yoff + 6}]um
paint metal2
box [expr {$LS3 + 15.97}]um [expr {$ypos + 25.05}]um [expr {$LS3 + 16.3}]um [expr {$ypos + 27.35}]um
paint m2contact
box [expr {$LS3 + 15.97}]um [expr {$yoff + 3.55}]um [expr {$LS3 + 16.3}]um [expr {$yoff + 5.95}]um
paint m2contact
box [expr {$LS3 + 17.5}]um [expr {$ypos + 28.65}]um [expr {$LS3 + 18.5}]um [expr {$yoff + 10.5}]um
paint metal2
box [expr {$LS3 + 17.5}]um [expr {$yoff + 9.5}]um 1372um [expr {$yoff + 10.5}]um
paint metal1
box [expr {$LS3 + 17.55}]um [expr {$yoff + 9.55}]um [expr {$LS3 + 18.45}]um [expr {$yoff + 10.45}]um
paint m2contact
box 1371um [expr {$yoff + 9.5}]um 1372um [expr {$yoff + 10.5}]um
label D3 west metal1

# LS4
box [expr {$LS4}]um [expr {$ypos}]um [expr {$LS4}]um [expr {$ypos}]um
getcell level_shifter.mag
rotate 90
box [expr {$LS4 + 20.47}]um 335um [expr {$LS4 + 23.47}]um [expr {$ypos + 0.5}]um
paint {metal2 metal3 metal4 metal5}
box [expr {$LS4 + 20.62}]um 335.15um [expr {$LS4 + 23.32}]um 341.85um
paint {m3contact via3 via4}
box [expr {$LS4 + 20.3}]um [expr {$ypos + 24}]um [expr {$LS4 + 21.3}]um [expr {$yoff + 15.5}]um
paint metal2
box [expr {$LS4 + 20.35}]um [expr {$ypos + 24.05}]um [expr {$LS4 + 21.25}]um [expr {$ypos + 26.95}]um
paint m2contact
box [expr {$LS4 + 15.92}]um [expr {$ypos + 25}]um [expr {$LS4 + 16.35}]um [expr {$yoff + 6}]um
paint metal2
box [expr {$LS4 + 15.97}]um [expr {$ypos + 25.05}]um [expr {$LS4 + 16.3}]um [expr {$ypos + 27.35}]um
paint m2contact
box [expr {$LS4 + 15.97}]um [expr {$yoff + 3.55}]um [expr {$LS4 + 16.3}]um [expr {$yoff + 5.95}]um
paint m2contact
box [expr {$LS4 + 17.5}]um [expr {$ypos + 28.65}]um [expr {$LS4 + 18.5}]um [expr {$yoff + 12}]um
paint metal2
box [expr {$LS4 + 17.5}]um [expr {$yoff + 11}]um 1372um [expr {$yoff + 12}]um
paint metal1
box [expr {$LS4 + 17.55}]um [expr {$yoff + 11.05}]um [expr {$LS4 + 18.45}]um [expr {$yoff + 11.95}]um
paint m2contact
box 1371um [expr {$yoff + 11}]um 1372um [expr {$yoff + 12}]um
label D4 west metal1

# Electromagnetic protections
box 80um [expr {$yoff - 3.5}]um 560um [expr {$yoff + 15.5}]um
paint {metal2}
box 80um [expr {$yoff - 3.5}]um 560um [expr {$yoff - 0.5}]um
paint {metal1}
box 80.05um [expr {$yoff - 3.45}]um 559.95um [expr {$yoff - 0.55}]um
paint m2contact
box 600um [expr {$yoff - 3.5}]um 650um [expr {$yoff + 15.5}]um
paint {metal2}
box 600um [expr {$yoff - 3.5}]um 650um [expr {$yoff - 0.5}]um
paint {metal1}
box 600.05um [expr {$yoff - 3.45}]um 649.95um [expr {$yoff - 0.55}]um
paint m2contact
box 690um [expr {$yoff - 3.5}]um 1300um [expr {$yoff + 15.5}]um
paint {metal2}
box 690um [expr {$yoff - 3.5}]um 1300um [expr {$yoff - 0.5}]um
paint {metal1}
box 690.05um [expr {$yoff - 3.45}]um 1299.95um [expr {$yoff - 0.55}]um
paint m2contact

save core.mag

gds write core.gds
extract
ext2spice lvs
ext2spice subcircuit top off
ext2spice -o core_layout.spice