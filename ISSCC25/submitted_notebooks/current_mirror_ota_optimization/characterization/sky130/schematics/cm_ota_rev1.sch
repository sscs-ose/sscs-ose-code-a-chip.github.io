v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 290 -360 290 -270 {
lab=ds3_4}
N 500 -360 500 -270 {
lab=ds2_4}
N 290 -440 290 -420 {
lab=avdd_1v8}
N 290 -440 500 -440 {
lab=avdd_1v8}
N 500 -440 500 -420 {
lab=avdd_1v8}
N 490 -390 500 -390 {
lab=avdd_1v8}
N 290 -390 300 -390 {
lab=avdd_1v8}
N 390 -460 390 -440 {
lab=avdd_1v8}
N 500 -350 550 -350 {
lab=ds2_4}
N 540 -390 550 -390 {
lab=ds2_4}
N 290 -210 290 -190 {
lab=itail}
N 290 -190 500 -190 {
lab=itail}
N 500 -210 500 -190 {
lab=itail}
N 390 -190 390 -160 {
lab=itail}
N 240 -390 250 -390 {
lab=ds3_4}
N 240 -350 290 -350 {
lab=ds3_4}
N 140 -440 140 -420 {
lab=avdd_1v8}
N 140 -360 140 -160 {
lab=#net1}
N 180 -130 190 -130 {
lab=#net1}
N 190 -130 610 -130 {
lab=#net1}
N 650 -440 650 -420 {
lab=avdd_1v8}
N 130 -390 140 -390 {
lab=avdd_1v8}
N 130 -420 130 -390 {
lab=avdd_1v8}
N 130 -420 140 -420 {
lab=avdd_1v8}
N 650 -360 650 -160 {
lab=out}
N 650 -390 660 -390 {
lab=avdd_1v8}
N 660 -420 660 -390 {
lab=avdd_1v8}
N 650 -420 660 -420 {
lab=avdd_1v8}
N 140 -100 140 -80 {
lab=avss}
N 140 -80 650 -80 {
lab=avss}
N 650 -100 650 -80 {
lab=avss}
N 130 -130 140 -130 {
lab=avss}
N 130 -130 130 -100 {
lab=avss}
N 130 -100 140 -100 {
lab=avss}
N 650 -100 660 -100 {
lab=avss}
N 660 -130 660 -100 {
lab=avss}
N 650 -130 660 -130 {
lab=avss}
N 290 -420 300 -420 {
lab=avdd_1v8}
N 300 -420 300 -390 {
lab=avdd_1v8}
N 490 -420 490 -390 {
lab=avdd_1v8}
N 490 -420 500 -420 {
lab=avdd_1v8}
N 0 -0 390 0 {
lab=avss}
N 390 -160 390 -60 {
lab=itail}
N -10 -30 0 -30 {
lab=avss}
N -10 -30 -10 -0 {
lab=avss}
N -10 -0 -0 -0 {
lab=avss}
N 390 0 410 0 {
lab=avss}
N 410 0 650 0 {
lab=avss}
N 650 -80 650 -0 {
lab=avss}
N 140 -80 140 -0 {
lab=avss}
N 140 -440 290 -440 {
lab=avdd_1v8}
N 500 -440 650 -440 {
lab=avdd_1v8}
N 240 -390 240 -350 {
lab=ds3_4}
N 550 -390 550 -350 {
lab=ds2_4}
N 140 -180 200 -180 {
lab=#net1}
N 200 -180 200 -130 {
lab=#net1}
N 180 -390 240 -390 {
lab=ds3_4}
N 550 -390 610 -390 {
lab=ds2_4}
N 300 -240 300 -210 {
lab=itail}
N 290 -210 300 -210 {
lab=itail}
N 290 -240 300 -240 {
lab=itail}
N 490 -240 500 -240 {
lab=itail}
N 490 -240 490 -210 {
lab=itail}
N 490 -210 500 -210 {
lab=itail}
C {sky130_fd_pr/nfet_01v8.sym} 270 -240 0 0 {name=M1
L=0.15
W=w1_2
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8.sym} 270 -390 0 0 {name=M3
L=0.15
W=w3_4
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=x
}
C {sky130_fd_pr/nfet_01v8.sym} 520 -240 0 1 {name=M2
L=0.15
W=w1_2
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8.sym} 520 -390 0 1 {name=M4
L=0.15
W=w3_4
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=x
}
C {devices/lab_wire.sym} 380 -240 0 1 {name=p2 sig_type=std_logic lab=avss}
C {devices/iopin.sym} 250 -240 0 1 {name=p4 lab=inn}
C {devices/iopin.sym} 540 -240 0 0 {name=p5 lab=inp}
C {sky130_fd_pr/pfet_01v8.sym} 160 -390 0 1 {name=M7
L=0.15
W=w7_8
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=x
}
C {sky130_fd_pr/nfet_01v8.sym} 160 -130 0 1 {name=M5
L=0.15
W=w5_6
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 630 -130 0 0 {name=M6
L=0.15
W=w5_6
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8.sym} 630 -390 0 0 {name=M8
L=0.15
W=w7_8
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=x
}
C {devices/iopin.sym} 650 -270 0 0 {name=p9 lab=out}
C {devices/iopin.sym} 390 -60 2 0 {name=p3 lab=itail}
C {devices/iopin.sym} -10 0 2 0 {name=p8 lab=avss}
C {devices/iopin.sym} 390 -460 0 0 {name=p7 lab=avdd_1v8}
C {devices/lab_wire.sym} 290 -310 0 1 {name=p10 sig_type=std_logic lab=ds3_4
}
C {devices/lab_wire.sym} 500 -310 0 1 {name=p11 sig_type=std_logic lab=ds2_4
}
