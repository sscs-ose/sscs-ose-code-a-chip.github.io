set fd [open {/usr/local/share/pdk/sky130A/libs.tech/magic/sky130A.tcl} r]
set text [read $fd]
close $fd
uplevel #0 [string map [list {$sky130::ruleset} {$::sky130::ruleset}] $text]
random seed 1729
load clock_cells
box values 120um 10um 120um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X1_Xps w 1.0 l 8.0 viagb 100
box values 137.0um 10um 137.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X1_Xpi w 1.0 l 0.5 viagb 100
box values 146.5um 10um 146.5um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X1_Xni w 0.5 l 0.5 viagb 100
box values 156.0um 10um 156.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X1_Xns w 0.5 l 8.0 viagb 100
box values 173.0um 10um 173.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X2_Xps w 1.0 l 8.0 viagb 100
box values 190.0um 10um 190.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X2_Xpi w 1.0 l 0.5 viagb 100
box values 199.5um 10um 199.5um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X2_Xni w 0.5 l 0.5 viagb 100
box values 209.0um 10um 209.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X2_Xns w 0.5 l 8.0 viagb 100
box values 226.0um 10um 226.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X3_Xps w 1.0 l 8.0 viagb 100
box values 243.0um 10um 243.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X3_Xpi w 1.0 l 0.5 viagb 100
box values 252.5um 10um 252.5um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X3_Xni w 0.5 l 0.5 viagb 100
box values 262.0um 10um 262.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X3_Xns w 0.5 l 8.0 viagb 100
box values 279.0um 10um 279.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X4_Xps w 1.0 l 8.0 viagb 100
box values 296.0um 10um 296.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X4_Xpi w 1.0 l 0.5 viagb 100
box values 305.5um 10um 305.5um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X4_Xni w 0.5 l 0.5 viagb 100
box values 315.0um 10um 315.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X4_Xns w 0.5 l 8.0 viagb 100
box values 332.0um 10um 332.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X5_Xps w 1.0 l 8.0 viagb 100
box values 349.0um 10um 349.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 X5_Xpi w 1.0 l 0.5 viagb 100
box values 358.5um 10um 358.5um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X5_Xni w 0.5 l 0.5 viagb 100
box values 368.0um 10um 368.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 X5_Xns w 0.5 l 8.0 viagb 100
box values 145.75um 35um 145.75um 35um
magic::gencell sky130::sky130_fd_pr__cap_mim_m3_1 Xc1 w 2.0 l 2.0
box values 198.75um 35um 198.75um 35um
magic::gencell sky130::sky130_fd_pr__cap_mim_m3_1 Xc2 w 2.0 l 2.0
box values 251.75um 35um 251.75um 35um
magic::gencell sky130::sky130_fd_pr__cap_mim_m3_1 Xc3 w 2.0 l 2.0
box values 304.75um 35um 304.75um 35um
magic::gencell sky130::sky130_fd_pr__cap_mim_m3_1 Xc4 w 2.0 l 2.0
box values 357.75um 35um 357.75um 35um
magic::gencell sky130::sky130_fd_pr__cap_mim_m3_1 Xc5 w 2.0 l 2.5
box values 385.0um 10um 385.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 Xbp1 w 1.0 l 8.0 viagb 100
box values 402.0um 10um 402.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 Xbn1 w 0.5 l 8.0 viagb 100
box values 419.0um 10um 419.0um 10um
magic::gencell sky130::sky130_fd_pr__pfet_01v8 Xbp2 w 1.0 l 1.0 viagb 100
box values 429.0um 10um 429.0um 10um
magic::gencell sky130::sky130_fd_pr__nfet_01v8 Xbn2 w 0.5 l 1.0 viagb 100
select top cell
expand
save clock_cells
foreach cell [cellname list children clock_cells] { if {$cell ne "microrobot_bias"} { load $cell; save $cell } }
load clock_cells
select top cell
box values -40um 0um 650um 120um
drc check
drc catchup
set f [open placement_drc.txt w]
puts $f "DRC_ERRORS [drc list count total]"
puts $f [drc listall why]
close $f
puts "OPENTCAD_FLOW_DONE"
quit -noprompt
