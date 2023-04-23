v {xschem version=3.1.0 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
P 4 5 1190 -300 1290 -300 1290 -160 1190 -160 1190 -300 {}
T {IO Pins} 1210 -300 0 0 0.4 0.4 {}
N 440 -380 570 -380 { lab=Va}
N 220 -90 220 -60 { lab=GND}
N 160 -120 220 -120 { lab=GND}
N 160 -120 160 -60 { lab=GND}
N 440 -380 440 -360 { lab=Va}
N 440 -300 440 -280 { lab=#net1}
N 570 -380 570 -360 { lab=Va}
N 570 -300 570 -280 { lab=#net2}
N 90 -380 90 -360 { lab=Va}
N 90 -300 90 -280 { lab=#net3}
N 440 -220 440 -150 { lab=vbneg}
N 90 -200 90 -60 { lab=GND}
N 570 -190 570 -60 { lab=GND}
N 480 -120 480 -60 { lab=GND}
N 440 -90 440 -60 { lab=GND}
N 400 -120 440 -120 { lab=GND}
N 400 -120 400 -60 { lab=GND}
N 260 -120 280 -120 { lab=GND}
N 280 -120 280 -60 { lab=GND}
N 70 -250 70 -200 { lab=GND}
N 70 -200 90 -200 { lab=GND}
N 550 -250 550 -190 { lab=GND}
N 550 -190 570 -190 { lab=GND}
N 340 -250 420 -250 { lab=GND}
N 340 -250 340 -60 { lab=GND}
N 220 -300 220 -150 { lab=Veb}
N 220 -380 220 -360 { lab=Va}
N 220 -380 290 -380 { lab=Va}
N 90 -380 220 -380 { lab=Va}
N 160 -60 220 -60 { lab=GND}
N 90 -60 160 -60 { lab=GND}
N 480 -60 570 -60 { lab=GND}
N 440 -60 480 -60 { lab=GND}
N 400 -60 440 -60 { lab=GND}
N 340 -60 400 -60 { lab=GND}
N 220 -60 280 -60 { lab=GND}
N 90 -220 90 -200 { lab=GND}
N 570 -220 570 -190 { lab=GND}
N 280 -60 340 -60 { lab=GND}
N 590 -60 760 -60 {
lab=GND}
N 780 -220 780 -60 {
lab=GND}
N 760 -250 760 -190 {
lab=GND}
N 760 -190 780 -190 {
lab=GND}
N -20 -350 -20 -320 { lab=Va}
N -20 -260 -20 -60 {
lab=GND}
N -20 -60 100 -60 {
lab=GND}
N -20 -380 -20 -350 {
lab=Va}
N -20 -380 90 -380 {
lab=Va}
N 220 -690 440 -690 { lab=VDD}
N 440 -560 440 -490 { lab=#net4}
N 220 -560 220 -500 { lab=#net5}
N 220 -690 220 -620 { lab=VDD}
N 320 -600 320 -540 {
lab=vgate}
N 440 -430 440 -380 {
lab=Va}
N 220 -440 220 -380 {
lab=Va}
N 780 -630 780 -600 { lab=VDD}
N 710 -600 740 -600 { lab=vgate}
N 780 -690 780 -630 { lab=VDD}
N 780 -570 780 -540 { lab=#net6}
N 570 -60 590 -60 {
lab=GND}
N 260 -600 400 -600 {
lab=vgate}
N 220 -570 220 -560 {
lab=#net5}
N 220 -620 220 -600 {
lab=VDD}
N 440 -630 440 -600 {
lab=VDD}
N 440 -690 440 -630 {
lab=VDD}
N 440 -570 440 -560 {
lab=#net4}
N 680 -480 680 -450 {
lab=GND}
N 380 -650 550 -650 {
lab=vgate}
N 380 -650 380 -600 {
lab=vgate}
N 760 -60 780 -60 {
lab=GND}
N 680 -600 710 -600 {
lab=vgate}
N 780 -400 820 -400 {
lab=vbg}
N 780 -480 780 -400 {
lab=vbg}
N 780 -400 780 -280 {
lab=vbg}
N 680 -450 680 -60 {
lab=GND}
N 550 -650 550 -600 {
lab=vgate}
N 550 -600 680 -600 {
lab=vgate}
N 680 -600 680 -510 {
lab=vgate}
N 440 -690 780 -690 {
lab=VDD}
N 350 -380 450 -380 {
lab=Va}
N 260 -440 280 -440 {
lab=VDD}
N 360 -440 380 -440 {
lab=GND}
C {sky130_fd_pr/pnp_05v5.sym} 240 -120 0 1 {name=Q2
model=pnp_05v5_W3p40L3p40
spiceprefix=X
}
C {devices/lab_pin.sym} 290 -380 3 0 {name=l5 lab=Va}
C {devices/ammeter.sym} 570 -330 0 0 {name=Vr4 current=5.7238e-06}
C {devices/ammeter.sym} 440 -330 0 0 {name=Vr2 current=4.3334e-06}
C {devices/ammeter.sym} 90 -330 0 0 {name=Vr1 current=5.7228e-06}
C {devices/ammeter.sym} 220 -330 0 0 {name=Vq2 current=4.3346e-06}
C {sky130_fd_pr/pnp_05v5.sym} 460 -120 0 1 {name=Q1
model="pnp_05v5_W3p40L3p40"
spiceprefix=X
m=39
}
C {devices/lab_pin.sym} 440 -190 0 0 {name=l4 lab=vbneg}
C {devices/lab_pin.sym} 220 -270 2 0 {name=l10 lab=Veb}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 90 -250 0 0 {name=R1
W=0.35
L=21.839
model=res_xhigh_po_0p35
spiceprefix=X
mult=1}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 570 -250 0 0 {name=R2
W=0.35
L=21.839
model=res_xhigh_po_0p35
spiceprefix=X
mult=1}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 440 -250 0 0 {name=R3
W=0.35
L=3.763
model=res_xhigh_po_0p35
spiceprefix=X
mult=1}
C {devices/ngspice_probe.sym} 440 -190 0 0 {name=r9}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 780 -250 0 0 {name=R6
W=0.35
L=17.38
model=res_xhigh_po_0p35
spiceprefix=X
mult=1}
C {devices/lab_pin.sym} 820 -400 0 1 {name=l2 lab=vbg}
C {devices/iopin.sym} 1260 -260 2 0 {name=p3 lab=vbg}
C {devices/capa.sym} -20 -290 0 0 {name=C2
m=1
value=20p
footprint=1206
device="ceramic capacitor"}
C {devices/vdd.sym} 370 -690 0 0 {name=l7 lab=VDD}
C {devices/ammeter.sym} 220 -470 0 0 {name=Vm1 current=1.0057e-05}
C {devices/ammeter.sym} 440 -460 0 0 {name=Vm2 current=1.0057e-05}
C {devices/lab_wire.sym} 340 -600 0 0 {name=l11 lab=vgate}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 240 -600 0 1 {name=M1
L=2
W=1
nf=1
mult=386.6
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 420 -600 0 0 {name=M2
L=2
W=1
nf=1
mult=386.6
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {devices/ngspice_probe.sym} 340 -600 0 0 {name=r7}
C {devices/ngspice_get_value.sym} 240 -520 0 0 {name=r20 node=@m.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]
descr="gm="}
C {devices/ngspice_get_value.sym} 410 -520 0 1 {name=r21 node=@m.xm2.msky130_fd_pr__pfet_01v8_lvt[gm]
descr="gm="}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 660 -480 0 0 {name=M10
L='2'
W='1'
nf=1
mult=34
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {devices/lab_pin.sym} 640 -480 0 0 {name=l15 lab=porst}
C {devices/ammeter.sym} 780 -510 0 0 {name=Vm3 current=1.0239e-05}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 760 -600 0 0 {name=M3
L=2
W=1
nf=1
mult=386.6
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {devices/ngspice_get_value.sym} 790 -550 0 0 {name=r22 node=@m.xm3.msky130_fd_pr__pfet_01v8_lvt[gm]
descr="gm="}
C {devices/lab_pin.sym} 2640 -650 3 0 {name=l3 lab=Va}
C {devices/iopin.sym} 1230 -200 0 0 {name=p4 lab=VDD}
C {devices/iopin.sym} 1230 -180 0 0 {name=p5 lab=GND}
C {devices/iopin.sym} 1260 -240 2 0 {name=p1 lab=porst}
C {devices/lab_wire.sym} 270 -440 0 0 {name=p2 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 370 -440 0 0 {name=p6 sig_type=std_logic lab=GND}
C {devices/lab_wire.sym} 740 -60 0 0 {name=p7 sig_type=std_logic lab=GND}
C {amplifier_v01.sym} 320 -540 3 0 {name=x1}
C {devices/lab_pin.sym} 350 -380 3 0 {name=l1 lab=Vb}
