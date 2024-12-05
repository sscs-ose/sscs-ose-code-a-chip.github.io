v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 280 -360 280 -270 {
lab=ds1_3}
N 520 -360 520 -270 {
lab=ds2_4}
N 280 -440 280 -420 {
lab=vdd}
N 520 -440 520 -420 {
lab=vdd}
N 510 -390 520 -390 {
lab=vdd}
N 280 -390 290 -390 {
lab=vdd}
N 390 -460 390 -440 {
lab=vdd}
N 520 -350 570 -350 {
lab=ds2_4}
N 560 -390 570 -390 {
lab=ds2_4}
N 280 -210 280 -190 {
lab=source}
N 520 -210 520 -190 {
lab=source}
N 230 -390 240 -390 {
lab=ds1_3}
N 230 -350 280 -350 {
lab=ds1_3}
N 140 -440 140 -420 {
lab=vdd}
N 140 -360 140 -160 {
lab=ds5_7}
N 180 -130 190 -130 {
lab=ds5_7}
N 190 -130 610 -130 {
lab=ds5_7}
N 650 -440 650 -420 {
lab=vdd}
N 130 -390 140 -390 {
lab=vdd}
N 130 -420 130 -390 {
lab=vdd}
N 130 -420 140 -420 {
lab=vdd}
N 650 -360 650 -160 {
lab=out}
N 650 -390 660 -390 {
lab=vdd}
N 660 -420 660 -390 {
lab=vdd}
N 650 -420 660 -420 {
lab=vdd}
N 140 -100 140 -80 {
lab=vss}
N 650 -100 650 -80 {
lab=vss}
N 130 -130 140 -130 {
lab=vss}
N 130 -130 130 -100 {
lab=vss}
N 660 -130 660 -100 {
lab=vss}
N 650 -130 660 -130 {
lab=vss}
N 280 -420 290 -420 {
lab=vdd}
N 290 -420 290 -390 {
lab=vdd}
N 510 -420 510 -390 {
lab=vdd}
N 510 -420 520 -420 {
lab=vdd}
N 230 -390 230 -350 {
lab=ds1_3}
N 570 -390 570 -350 {
lab=ds2_4}
N 140 -180 200 -180 {
lab=ds5_7}
N 200 -180 200 -130 {
lab=ds5_7}
N 290 -240 290 -210 {
lab=source}
N 280 -240 290 -240 {
lab=source}
N 510 -240 520 -240 {
lab=source}
N 510 -240 510 -210 {
lab=source}
N 510 -210 520 -210 {
lab=source}
N 400 -30 420 -30 {
lab=vss}
N 420 -30 420 0 {
lab=vss}
N 60 -30 70 -30 {
lab=vss}
N 60 -30 60 -0 {
lab=vss}
N 70 -80 120 -80 {
lab=itail}
N 120 -80 120 -30 {
lab=itail}
N 140 -80 330 -80 {
lab=vss}
N 470 -80 650 -80 {
lab=vss}
N 330 -80 470 -80 {
lab=vss}
N 280 -210 290 -210 {
lab=source}
N -10 0 420 0 {
lab=vss}
N 180 -390 230 -390 {
lab=ds1_3}
N 570 -390 610 -390 {
lab=ds2_4}
N 280 -190 520 -190 {
lab=source}
N 140 -440 650 -440 {
lab=vdd}
N 420 -0 660 -0 {
lab=vss}
N 110 -30 120 -30 {
lab=itail}
N 650 -80 660 -80 {
lab=vss}
N 660 -100 660 -80 {
lab=vss}
N 130 -100 130 -80 {
lab=vss}
N 130 -80 140 -80 {
lab=vss}
N 280 -80 280 0 {
lab=vss}
N 70 -80 70 -60 {
lab=itail}
N 70 -100 70 -80 {
lab=itail}
N 120 -30 360 -30 {
lab=itail}
N 400 -190 400 -60 {
lab=source}
C {sky130_fd_pr/nfet_01v8.sym} 260 -240 0 0 {name=M1
L=0.15
W=w1_2
nf=nf1_2
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
C {sky130_fd_pr/pfet_01v8.sym} 260 -390 0 0 {name=M3
L=0.15
W=w3_4
nf=nf3_4
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
C {sky130_fd_pr/nfet_01v8.sym} 540 -240 0 1 {name=M2
L=0.15
W=w1_2
nf=nf1_2
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
C {sky130_fd_pr/pfet_01v8.sym} 540 -390 0 1 {name=M4
L=0.15
W=w3_4
nf=nf3_4
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
C {devices/iopin.sym} 240 -240 0 1 {name=p4 lab=inn}
C {devices/iopin.sym} 560 -240 0 0 {name=p5 lab=inp}
C {sky130_fd_pr/pfet_01v8.sym} 160 -390 0 1 {name=M7
L=0.15
W=w7_8
nf=nf7_8
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
nf=nf5_6
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
nf=nf5_6
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
nf=nf7_8
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
C {devices/iopin.sym} -10 0 2 0 {name=p8 lab=vss}
C {devices/iopin.sym} 390 -460 0 0 {name=p7 lab=vdd}
C {devices/lab_wire.sym} 280 -310 0 1 {name=p10 sig_type=std_logic lab=ds1_3
}
C {devices/lab_wire.sym} 520 -310 0 1 {name=p11 sig_type=std_logic lab=ds2_4
}
C {sky130_fd_pr/nfet_01v8.sym} 380 -30 0 0 {name=M9
L=0.15
W=w9_10
nf=nf9_10
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
C {devices/lab_wire.sym} 140 -300 0 1 {name=p6 sig_type=std_logic lab=ds5_7
}
C {sky130_fd_pr/nfet_01v8.sym} 90 -30 0 1 {name=M10
L=0.15
W=w9_10
nf=nf1_2
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
C {devices/iopin.sym} 70 -100 2 0 {name=p12 lab=itail}
C {devices/lab_wire.sym} 400 -150 0 1 {name=p1 sig_type=std_logic lab=source
}
