v {xschem version=3.0.0 file_version=1.2 }
G {}
K {}
V {}
S {}
E {}
N 250 -290 250 -270 { lab=VDD}
N 250 -400 250 -350 { lab=G}
N 700 -280 700 -240 { lab=D}
N 620 -310 660 -310 { lab=G}
N 700 -310 730 -310 { lab=VDD}
N 80 -400 80 -370 { lab=#net1}
N 700 -370 700 -340 { lab=VDD}
N 80 -500 80 -460 { lab=D}
N 80 -310 80 -290 { lab=VDD}
N 730 -350 730 -310 { lab=VDD}
N 700 -350 730 -350 { lab=VDD}
N 390 -300 390 -280 { lab=GND}
N 390 -410 390 -360 { lab=VDD}
C {devices/vsource.sym} 250 -320 0 0 {name=VGS value=\{VGS\}}
C {devices/lab_wire.sym} 250 -400 0 0 {name=l8 sig_type=std_logic lab=G}
C {devices/lab_wire.sym} 80 -500 0 0 {name=l3 sig_type=std_logic lab=D}
C {devices/lab_wire.sym} 620 -310 0 0 {name=l4 sig_type=std_logic lab=G}
C {devices/lab_wire.sym} 700 -370 0 0 {name=l6 sig_type=std_logic lab=VDD}
C {devices/code_shown.sym} 40 -980 0 0 {name=s1 only_toplevel=false value="
.param VIN = 20
.param VGS = 1
.option temp=70
*.ic v(V_CFTOP) = VIN/2
.lib /foss/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.control
save all
compose voltage start=-5 stop=-2 step=0.5
foreach volt $&voltage
alterparam VGS=$volt
reset
dc IDS 0.25 0.35 0.001
run
wrdata /foss/designs/personal/3LFCC_AC3E/xschem/dev_switches/PMOS_R_on_calc.txt dc.v(D) dc.v(VDD)
set appendwrite
end


*print 1/@m.xm1.msky130_fd_pr__nfet_g5v0d10v5[gds]
*plot 1/@m.xm1.msky130_fd_pr__nfet_g5v0d10v5[gds]
.endc

"}
C {devices/isource.sym} 80 -340 0 0 {name=IDS value=300m}
C {devices/vsource.sym} 80 -430 0 0 {name=VIDSMEAS value=0}
C {devices/lab_wire.sym} 700 -240 0 0 {name=l2 sig_type=std_logic lab=D}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 680 -310 0 0 {name=M1
L=0.5
W=4.38
nf=1
mult=4506
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_g5v0d10v5
spiceprefix=X
}
C {devices/vsource.sym} 390 -330 0 0 {name=VDD value=5}
C {devices/gnd.sym} 390 -280 0 0 {name=l7 lab=GND}
C {devices/lab_wire.sym} 390 -410 0 0 {name=l11 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 250 -270 0 0 {name=l5 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 80 -290 0 0 {name=l1 sig_type=std_logic lab=VDD}
