v {xschem version=3.0.0 file_version=1.2 }
G {}
K {}
V {}
S {}
E {}
N -6240 -440 -6140 -440 {
lab=out}
N -6240 -570 -6240 -530 {
lab=fc1}
N -6240 -500 -6220 -500 {
lab=fc1}
N -6220 -550 -6220 -500 {
lab=fc1}
N -6240 -550 -6220 -550 {
lab=fc1}
N -6240 -600 -6220 -600 {
lab=VP}
N -6220 -650 -6220 -600 {
lab=VP}
N -6240 -650 -6220 -650 {
lab=VP}
N -6310 -550 -6240 -550 {
lab=fc1}
N -6310 -600 -6280 -600 {
lab=s1}
N -6310 -500 -6280 -500 {
lab=s2}
N -6240 -670 -6240 -650 {
lab=VP}
N -6240 -360 -6240 -320 {
lab=fc2}
N -6240 -390 -6220 -390 {
lab=fc2}
N -6220 -390 -6220 -340 {
lab=fc2}
N -6240 -340 -6220 -340 {
lab=fc2}
N -6240 -290 -6220 -290 {
lab=VN}
N -6220 -290 -6220 -240 {
lab=VN}
N -6240 -240 -6220 -240 {
lab=VN}
N -6320 -390 -6280 -390 {
lab=s3}
N -6320 -340 -6240 -340 {
lab=fc2}
N -6320 -290 -6280 -290 {
lab=s4}
N -6240 -260 -6240 -200 {
lab=VN}
N -6240 -470 -6240 -420 {
lab=out}
N -6240 -650 -6240 -630 {
lab=VP}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} -6260 -500 0 0 {name=M3
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
C {sky130_fd_pr/pfet_g5v0d10v5.sym} -6260 -600 0 0 {name=M4
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
C {devices/iopin.sym} -6240 -670 3 0 {name=p10 lab=VP
}
C {devices/ipin.sym} -6310 -600 0 0 {name=p11 lab=s1}
C {devices/ipin.sym} -6310 -500 0 0 {name=p12 lab=s2
}
C {devices/iopin.sym} -6140 -440 0 0 {name=p14 lab=out}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} -6260 -390 0 0 {name=M1
L=0.5
W=4.38
nf=1
mult=2520
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_g5v0d10v5
spiceprefix=X
}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} -6260 -290 0 0 {name=M2
L=0.5
W=4.38
nf=1
mult=2520
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_g5v0d10v5
spiceprefix=X
}
C {devices/ipin.sym} -6320 -390 0 0 {name=p2 lab=s3}
C {devices/ipin.sym} -6320 -290 0 0 {name=p5 lab=s4}
C {devices/iopin.sym} -6240 -200 1 0 {name=p8 lab=VN}
C {devices/iopin.sym} -6310 -550 2 0 {name=p1 lab=fc1}
C {devices/iopin.sym} -6320 -340 2 0 {name=p4 lab=fc2}
