v {xschem version=3.0.0 file_version=1.2 
}
G {}
K {}
V {}
S {}
E {}
N 190 -280 190 -230 {
lab=#net1}
N 120 -310 150 -310 {
lab=IN}
N 120 -310 120 -200 {
lab=IN}
N 120 -200 150 -200 {
lab=IN}
N 90 -250 120 -250 {
lab=IN}
N 190 -370 190 -340 {
lab=VDD}
N 190 -170 190 -140 {
lab=VSS}
N 190 -200 210 -200 {
lab=VSS}
N 210 -200 210 -140 {
lab=VSS}
N 190 -310 210 -310 {
lab=VDD}
N 210 -370 210 -310 {
lab=VDD}
N 420 -410 720 -410 {
lab=VH}
N 720 -410 720 -380 {
lab=VH}
N 420 -410 420 -380 {
lab=VH}
N 570 -410 570 -380 {
lab=VH}
N 420 -320 420 -220 {
lab=#net2}
N 570 -320 570 -220 {
lab=#net3}
N 720 -320 720 -220 {
lab=#net4}
N 400 -410 400 -350 {
lab=VH}
N 400 -410 420 -410 {
lab=VH}
N 570 -350 590 -350 {
lab=VH}
N 590 -410 590 -350 {
lab=VH}
N 720 -350 740 -350 {
lab=VH}
N 740 -410 740 -350 {
lab=VH}
N 720 -410 740 -410 {
lab=VH}
N 460 -350 470 -350 {
lab=#net3}
N 470 -350 470 -290 {
lab=#net3}
N 470 -290 570 -290 {
lab=#net3}
N 420 -160 420 -130 {
lab=VSS}
N 420 -130 720 -130 {
lab=VSS}
N 720 -160 720 -130 {
lab=VSS}
N 570 -160 570 -130 {
lab=VSS}
N 420 -190 440 -190 {
lab=VSS}
N 440 -190 440 -130 {
lab=VSS}
N 550 -190 570 -190 {
lab=VSS}
N 550 -190 550 -130 {
lab=VSS}
N 720 -190 740 -190 {
lab=VSS}
N 740 -190 740 -130 {
lab=VSS}
N 720 -130 740 -130 {
lab=VSS}
N 520 -350 530 -350 {
lab=#net2}
N 520 -350 520 -270 {
lab=#net2}
N 420 -270 520 -270 {
lab=#net2}
N 420 -250 660 -250 {
lab=#net2}
N 660 -350 660 -250 {
lab=#net2}
N 660 -350 680 -350 {
lab=#net2}
N 610 -190 680 -190 {
lab=IN}
N 400 -350 420 -350 {
lab=VH}
N 190 -250 240 -250 {
lab=#net1}
N 190 -370 210 -370 {
lab=VDD}
N 120 -60 240 -60 {
lab=IN}
N 120 -200 120 -70 {
lab=IN}
N 240 -250 320 -250 {
lab=#net1}
N 200 -380 200 -370 {
lab=VDD}
N 480 -420 480 -410 {
lab=VH}
N 890 -400 890 -370 {
lab=VH}
N 890 -310 890 -210 {
lab=OUT}
N 890 -340 910 -340 {
lab=VH}
N 910 -400 910 -340 {
lab=VH}
N 890 -400 910 -400 {
lab=VH}
N 890 -180 910 -180 {
lab=VSS}
N 830 -340 830 -240 {
lab=#net4}
N 830 -340 850 -340 {
lab=#net4}
N 890 -250 920 -250 {
lab=OUT}
N 830 -230 830 -180 {
lab=#net4}
N 830 -240 830 -230 {
lab=#net4}
N 830 -180 850 -180 {
lab=#net4}
N 740 -410 890 -410 {
lab=VH}
N 890 -410 890 -400 {
lab=VH}
N 320 -190 380 -190 {
lab=#net1}
N 320 -250 320 -190 {
lab=#net1}
N 240 -60 660 -60 {
lab=IN}
N 660 -190 660 -70 {
lab=IN}
N 740 -130 910 -130 {
lab=VSS}
N 890 -150 890 -130 {
lab=VSS}
N 910 -180 910 -130 {
lab=VSS}
N 210 -130 420 -130 {
lab=VSS}
N 190 -130 210 -130 {
lab=VSS}
N 190 -140 190 -130 {
lab=VSS}
N 210 -140 210 -130 {
lab=VSS}
N 480 -130 480 -110 {
lab=VSS}
N 660 -70 660 -60 {
lab=IN}
N 120 -70 120 -60 {
lab=IN}
N 720 -250 830 -250 {
lab=#net4}
C {sky130_fd_pr/pfet_01v8.sym} 170 -310 0 0 {name=M11
L=0.15
W=1
nf=1
mult=5
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8.sym} 170 -200 0 0 {name=M12
L=0.15
W=1
nf=1 
mult=5
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 440 -350 0 1 {name=M15
L=0.5
W=2
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 550 -350 0 0 {name=M14
L=0.5
W=2
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 700 -350 0 0 {name=M16
L=0.5
W=10
nf=1
mult=10
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 400 -190 0 0 {name=M18
L=0.5
W=4
nf=1
mult=3
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 590 -190 0 1 {name=M13
L=0.5
W=4
nf=1
mult=3
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 700 -190 0 0 {name=M17
L=0.5
W=10
nf=1
mult=10
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_g5v0d10v5
spiceprefix=X
}
C {devices/ipin.sym} 90 -250 0 0 {name=p3 lab=IN}
C {devices/iopin.sym} 200 -380 3 0 {name=p4 lab=VDD}
C {devices/iopin.sym} 480 -420 3 0 {name=p1 lab=VH}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 870 -340 0 0 {name=M7
L=0.5
W=20
nf=1
mult=20
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 870 -180 0 0 {name=M10
L=0.5
W=20
nf=1
mult=20
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_g5v0d10v5
spiceprefix=X
}
C {devices/opin.sym} 920 -250 0 0 {name=p2 lab=OUT}
C {devices/iopin.sym} 480 -110 1 0 {name=p6 lab=VSS}
