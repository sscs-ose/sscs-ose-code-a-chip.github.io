v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N -570 220 -570 280 {lab=S}
N -360 220 -360 280 {lab=S}
N -460 280 -360 280 {lab=S}
N -460 400 -460 430 {lab=GND}
N -460 280 -460 340 {lab=S}
N -570 280 -460 280 {lab=S}
N -680 190 -680 210 {lab=#net1}
N -680 270 -680 300 {lab=GND}
N -570 -60 -460 -60 {lab=VDD}
N -460 -100 -460 -60 {lab=VDD}
N -460 -60 -360 -60 {lab=VDD}
N -680 -20 -680 0 {lab=VDD}
N -680 60 -680 90 {lab=GND}
N -570 -60 -570 -20 {lab=VDD}
N -360 -60 -360 -20 {lab=VDD}
N -410 190 -360 190 {lab=GND}
N -410 190 -410 430 {lab=GND}
N -570 190 -410 190 {lab=GND}
N -460 430 -410 430 {lab=GND}
N -320 190 -290 190 {lab=#net1}
N -460 430 -460 460 {lab=GND}
N -360 70 -360 160 {lab=D2}
N -570 70 -570 160 {lab=D1}
N -470 70 -470 110 {lab=#net2}
N -180 90 -180 110 {lab=#net2}
N -180 90 -90 90 {lab=#net2}
N -150 130 -150 160 {lab=#net3}
N -150 130 -90 130 {lab=#net3}
N -470 70 -450 70 {lab=#net2}
N -480 70 -470 70 {lab=#net2}
N -470 110 -180 110 {lab=#net2}
N -570 70 -540 70 {lab=D1}
N -570 40 -570 70 {lab=D1}
N -390 70 -360 70 {lab=D2}
N -360 40 -360 70 {lab=D2}
N -50 140 -50 170 {lab=GND}
N -470 30 -400 30 {lab=#net4}
N -530 -10 -400 -10 {lab=GND}
N -50 50 -50 80 {lab=#net4}
N -470 50 -50 50 {lab=#net4}
N -470 30 -470 50 {lab=#net4}
N -530 30 -470 30 {lab=#net4}
N -150 220 -150 240 {lab=GND}
N -640 190 -610 190 {lab=#net1}
N -640 190 -640 230 {lab=#net1}
N -680 190 -640 190 {lab=#net1}
N -640 230 -290 230 {lab=#net1}
N -290 190 -290 230 {lab=#net1}
C {sg13g2_pr/sg13_lv_nmos.sym} -590 190 2 1 {name=M1
l=0.5u
w=10u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} -340 190 2 0 {name=M2
l=0.5u
w=10u
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {isource.sym} -460 370 0 0 {name=I0 value=2u}
C {gnd.sym} -460 460 0 0 {name=l1 lab=GND}
C {vsource.sym} -680 240 0 0 {name=V1 value=0.825 savecurrent=false}
C {gnd.sym} -680 300 0 0 {name=l2 lab=GND}
C {vdd.sym} -460 -100 0 0 {name=l3 lab=VDD}
C {vsource.sym} -680 30 0 0 {name=V2 value=1.65 savecurrent=false}
C {gnd.sym} -680 90 0 0 {name=l4 lab=GND}
C {vdd.sym} -680 -20 0 0 {name=l5 lab=VDD}
C {lab_pin.sym} -570 90 0 1 {name=p1 sig_type=std_logic lab=D1}
C {lab_pin.sym} -360 90 0 0 {name=p2 sig_type=std_logic lab=D2}
C {lab_pin.sym} -460 280 3 1 {name=p3 sig_type=std_logic lab=S}
C {vcvs.sym} -50 110 0 0 {name=E1 value=100k}
C {res.sym} -510 70 1 0 {name=R1
value=100k
footprint=1206
device=resistor
m=1}
C {res.sym} -420 70 1 0 {name=R2
value=100k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -150 190 0 0 {name=V3 value=0.825 savecurrent=false}
C {vccs.sym} -570 10 0 1 {name=G1 value=1e-6}
C {vccs.sym} -360 10 0 0 {name=G2 value=1e-6}
C {gnd.sym} -50 170 0 0 {name=l6 lab=GND}
C {gnd.sym} -470 -10 0 0 {name=l7 lab=GND}
C {gnd.sym} -150 240 0 0 {name=l8 lab=GND}
C {devices/code_shown.sym} -1050 -100 0 0 {name=COMMANDS2 only_toplevel=false
value="
.save @n.xm1.nsg13_lv_nmos[gds]
.save @n.xm1.nsg13_lv_nmos[gm]
.save @n.xm1.nsg13_lv_nmos[gmb]
.save @n.xm1.nsg13_lv_nmos[ids]
.save @n.xm1.nsg13_lv_nmos[l]
.save @n.xm1.nsg13_lv_nmos[vth]
.save @n.xm2.nsg13_lv_nmos[cgd]
.save @n.xm2.nsg13_lv_nmos[cgg]
.save @n.xm2.nsg13_lv_nmos[cgs]
.save @n.xm2.nsg13_lv_nmos[gds]
.save @n.xm2.nsg13_lv_nmos[gm]
.save @n.xm2.nsg13_lv_nmos[gmb]
.save @n.xm2.nsg13_lv_nmos[ids]
.save @n.xm2.nsg13_lv_nmos[l]
.save @n.xm2.nsg13_lv_nmos[vth]
"}
C {devices/code_shown.sym} -1320 -90 0 0 {name="NGSPICE" only_toplevel=true 
value="
.option wnflag=1
.option savecurrents
.temp 27
.control
save all
write Diff-amp_1.raw
set appendwrite 
op
write Diff-amp_1.raw
**dc temp -50 150 1
tran 1m 10m 1m
**ac dec 20 1 1e8
**plot vdb(vout2) vdb(vout1)
.endc
"}
C {devices/launcher.sym} -1040 310 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/Diff-amp_1.raw; set show_hidden_texts 1; xschem annotate_op"}
C {devices/code_shown.sym} -1280 240 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
"}
