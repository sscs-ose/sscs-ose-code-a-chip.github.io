v {xschem version=3.1.0 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
P 4 5 580 -240 680 -240 680 -80 580 -80 580 -240 {}
T {I/O Pins} 600 -230 0 0 0.3 0.3 {}
N 110 -310 170 -310 { lab=vg}
N 170 -340 170 -310 { lab=vg}
N 150 -340 170 -340 { lab=vg}
N 170 -340 280 -340 { lab=vg}
N 110 -390 110 -370 { lab=VDD}
N 320 -390 320 -370 { lab=VDD}
N 110 -310 110 -240 { lab=vg}
N 320 -300 320 -240 { lab=vout}
N 50 -210 70 -210 { lab=minus}
N 310 -180 320 -180 { lab=Vq}
N 320 -340 330 -340 { lab=VDD}
N 330 -370 330 -340 { lab=VDD}
N 320 -370 330 -370 { lab=VDD}
N 100 -340 110 -340 { lab=VDD}
N 100 -370 100 -340 { lab=VDD}
N 100 -370 110 -370 { lab=VDD}
N 110 -210 120 -210 { lab=GND}
N 310 -210 320 -210 { lab=GND}
N 200 -60 210 -60 { lab=GND}
N 200 -60 200 -30 { lab=GND}
N 250 -60 380 -60 { lab=Vx}
N 420 -60 430 -60 { lab=GND}
N 380 -90 380 -60 { lab=Vx}
N 380 -90 420 -90 { lab=Vx}
N 430 -60 430 -30 { lab=GND}
N 420 -290 430 -290 { lab=VDD}
N 430 -320 430 -290 { lab=VDD}
N 420 -320 430 -320 { lab=VDD}
N 380 -300 380 -290 { lab=vout}
N 420 -390 420 -320 { lab=VDD}
N 110 -390 320 -390 { lab=VDD}
N 110 -180 120 -180 { lab=Vq}
N 210 -180 310 -180 { lab=Vq}
N 200 -30 430 -30 { lab=GND}
N 120 -180 210 -180 { lab=Vq}
N 320 -310 320 -300 { lab=vout}
N 320 -300 380 -300 { lab=vout}
N 320 -390 420 -390 { lab=VDD}
N 120 -210 310 -210 { lab=GND}
N 420 -260 420 -140 {
lab=Vx}
N 420 -140 420 -90 {
lab=Vx}
N 210 -110 210 -90 {
lab=Vq}
N 210 -180 210 -110 {
lab=Vq}
N 360 -210 370 -210 {
lab=plus}
N 380 -300 520 -300 {
lab=vout}
N 260 -420 260 -390 {
lab=VDD}
N 320 -30 320 20 {
lab=GND}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 340 -210 0 1 {name=M5
L='2'
W='1'
nf=1
mult=26.95
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 230 -60 0 1 {name=M6
L=2
W=1
nf=1
mult=3.65
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 90 -210 0 0 {name=M9
L='2'
W='1'
nf=1
mult=26.95
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {devices/lab_pin.sym} 230 -340 1 0 {name=l2 lab=vg}
C {devices/lab_pin.sym} 420 -140 1 0 {name=l12 lab=Vx}
C {devices/lab_pin.sym} 210 -110 0 0 {name=l18 lab=Vq}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 400 -60 0 0 {name=M7
L=2
W=1
nf=1
mult=3.65
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 400 -290 0 0 {name=M13
L=2
W=1
nf=1
mult=77.32
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {devices/ngspice_probe.sym} 420 -110 0 0 {name=r3}
C {devices/ngspice_probe.sym} 210 -130 0 0 {name=r4}
C {devices/ngspice_probe.sym} 170 -340 0 0 {name=r6}
C {devices/ngspice_get_value.sym} 420 -230 0 0 {name=r16 node=i(@m.xm13.msky130_fd_pr__pfet_01v8_lvt[id])
descr="I="}
C {devices/ngspice_get_value.sym} 210 -150 0 0 {name=r17 node=i(@m.xm6.msky130_fd_pr__nfet_01v8_lvt[id])
descr="I="}
C {devices/ngspice_get_value.sym} 110 -240 0 0 {name=r18 node=i(@m.xm8.msky130_fd_pr__pfet_01v8_lvt[id])
descr="I="}
C {devices/ngspice_get_value.sym} 320 -240 0 1 {name=r19 node=i(@m.xm4.msky130_fd_pr__pfet_01v8_lvt[id])
descr="I="}
C {devices/ngspice_get_value.sym} 110 -280 0 0 {name=r10 node=@m.xm8.msky130_fd_pr__pfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 320 -280 0 1 {name=r11 node=@m.$\{path\}xm4.msky130_fd_pr__pfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 110 -150 0 0 {name=r12 node=@m.xm9.msky130_fd_pr__nfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 320 -150 0 1 {name=r13 node=@m.xm5.msky130_fd_pr__nfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 440 -220 0 0 {name=r14 node=@m.xm13.msky130_fd_pr__pfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 230 -90 0 0 {name=r15 node=@m.xm6.msky130_fd_pr__nfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 400 -90 0 1 {name=r23 node=@m.xm7.msky130_fd_pr__nfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_probe.sym} 320 -270 0 0 {name=r27}
C {devices/gnd.sym} 210 -210 0 0 {name=l14 lab=GND}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 130 -340 0 1 {name=M4
L=2
W=1
nf=1
mult=38.66
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 300 -340 0 0 {name=M8
L=2
W=1
nf=1
mult=38.66
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {devices/gnd.sym} 290 -30 0 0 {name=l17 lab=GND}
C {devices/ipin.sym} 570 -190 2 0 {name=p1 lab=plus}
C {devices/ipin.sym} 570 -170 2 0 {name=p2 lab=minus}
C {devices/opin.sym} 570 -150 0 0 {name=p3 lab=vout}
C {devices/lab_pin.sym} 50 -210 0 0 {name=l1 lab=minus
}
C {devices/lab_pin.sym} 370 -210 2 0 {name=l3 lab=plus
}
C {devices/lab_pin.sym} 520 -300 2 0 {name=l4 lab=vout}
C {devices/iopin.sym} 600 -130 0 0 {name=p4 lab=VDD}
C {devices/iopin.sym} 600 -110 0 0 {name=p5 lab=GND}
C {devices/lab_pin.sym} 260 -420 1 0 {name=l5 lab=VDD}
C {devices/lab_pin.sym} 320 20 3 0 {name=l6 lab=GND}
