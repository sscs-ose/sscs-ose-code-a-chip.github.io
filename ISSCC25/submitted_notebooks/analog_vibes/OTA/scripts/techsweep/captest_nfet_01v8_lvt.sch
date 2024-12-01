v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 700 -380 700 -360 {
lab=d}
N 580 -210 580 -180 {
lab=GND}
N 890 -210 890 -180 {
lab=GND}
N 800 -210 800 -180 {
lab=GND}
N 700 -300 700 -270 {
lab=GND}
N 800 -330 800 -270 {
lab=b}
N 580 -330 580 -270 {
lab=g}
N 580 -330 660 -330 {
lab=g}
N 700 -330 800 -330 {
lab=b}
N 700 -380 890 -380 {
lab=d}
N 890 -380 890 -270 {
lab=d}
N 700 -270 700 -180 {
lab=GND}
C {devices/gnd.sym} 700 -180 0 0 {name=l1 lab=GND}
C {devices/vsource.sym} 580 -240 0 0 {name=vg value="dc 0.9 ac 1" savecurrent=false}
C {devices/gnd.sym} 580 -180 0 0 {name=l3 lab=GND}
C {devices/vsource.sym} 890 -240 0 0 {name=vd value="dc 0.9" savecurrent=false}
C {devices/gnd.sym} 890 -180 0 0 {name=l2 lab=GND}
C {devices/vsource.sym} 800 -240 2 1 {name=vsb value=\{vsbx\} savecurrent=false}
C {devices/gnd.sym} 800 -180 0 0 {name=l4 lab=GND}
C {devices/lab_wire.sym} 630 -330 0 0 {name=p1 sig_type=std_logic lab=g}
C {devices/lab_wire.sym} 800 -380 0 0 {name=p2 sig_type=std_logic lab=d}
C {devices/lab_wire.sym} 800 -330 0 0 {name=p3 sig_type=std_logic lab=b}
C {devices/code_shown.sym} 90 -620 0 0 {name=COMMANDS only_toplevel=false
value="
.param wx=5 lx=0.15 vsbx=0
.param freq = 1Meg
.csparam freq = \{freq\}
.ac lin 1 \{freq\} \{freq\}

.control
run
print -im(vg#branch)/(2*PI*freq)

op
show
*showmod m.XM1.msky130_fd_pr__nfet_01v8_lvt
.endc
"}
C {sky130_fd_pr/corner.sym} 560 -580 0 0 {name=CORNER only_toplevel=true corner=tt}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 680 -330 0 0 {name=M1
L=\{lx\}
W=\{wx\}
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {devices/title.sym} 160 -40 0 0 {name=l5 author="Boris Murmann"}
