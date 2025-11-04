v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 320 0 320 110 {lab=#net1}
N 320 0 410 0 {lab=#net1}
N 410 0 410 60 {lab=#net1}
N 410 120 410 160 {lab=CAN+}
N 410 220 410 260 {lab=#net2}
N 320 260 410 260 {lab=#net2}
N 320 170 320 260 {lab=#net2}
N 500 0 500 110 {lab=#net3}
N 500 0 590 0 {lab=#net3}
N 590 0 590 60 {lab=#net3}
N 590 120 590 160 {lab=CAN-}
N 590 220 590 260 {lab=#net2}
N 500 260 590 260 {lab=#net2}
N 500 170 500 260 {lab=#net2}
N -470 -10 -470 30 {lab=#net4}
N -470 90 -470 120 {lab=GND}
N -20 10 110 10 {lab=CAN+}
N 110 10 110 30 {lab=CAN+}
N -20 30 80 30 {lab=CAN-}
N 80 30 80 110 {lab=CAN-}
N 80 110 110 110 {lab=CAN-}
N 110 90 110 110 {lab=CAN-}
N 180 -10 200 -10 {lab=VCC}
N -20 -10 180 -10 {lab=VCC}
N 410 260 500 260 {lab=#net2}
N -20 50 60 50 {lab=GND}
N 60 50 60 140 {lab=GND}
N 60 140 200 140 {lab=GND}
N -20 70 30 70 {lab=#net5}
N 200 -10 200 -0 {lab=VCC}
N 200 60 200 70 {lab=#net6}
N 200 130 200 170 {lab=GND}
N -470 -10 -450 -10 {lab=#net4}
N -390 -10 -320 -10 {lab=TX}
N 30 70 30 80 {lab=#net5}
N 30 140 30 160 {lab=RX}
N -20 160 20 160 {lab=RX}
N 20 160 30 160 {lab=RX}
N 110 10 150 10 {lab=CAN+}
N 150 10 150 30 {lab=CAN+}
C {vsource.sym} 200 100 0 0 {name=V1 value=1.8 savecurrent=false}
C {res.sym} 110 60 0 0 {name=R1
value=60
footprint=1206
device=resistor
m=1}
C {vsource.sym} 320 140 0 0 {name=V3 value=5 savecurrent=false}
C {res.sym} 410 90 0 0 {name=R2
value=50k
footprint=1206
device=resistor
m=1}
C {res.sym} 410 190 0 0 {name=R3
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} 500 140 0 0 {name=V4 value=5 savecurrent=false}
C {res.sym} 590 90 0 0 {name=R4
value=50k
footprint=1206
device=resistor
m=1}
C {res.sym} 590 190 0 0 {name=R5
value=50k
footprint=1206
device=resistor
m=1}
C {sky130_fd_pr/corner.sym} -460 210 0 0 {name=CORNER only_toplevel=false corner=ss}
C {lab_wire.sym} 410 150 0 0 {name=p3 sig_type=std_logic lab=CAN+}
C {lab_wire.sym} 590 150 0 0 {name=p4 sig_type=std_logic lab=CAN-}
C {code_shown.sym} -280 200 0 0 {name=s1 only_toplevel=false value="
.temp 125

.option gmin=1e-7
.option abstol=1e-7
.option reltol=0.01
.option itl4=200

.control

tran 0.1m 2m

write
.endc
"}
C {vsource.sym} -470 60 0 0 {name=V2 value="PULSE(0 1.8 0 0.01m 0.01m 1m 2m)" savecurrent=false}
C {lab_wire.sym} 180 -10 0 0 {name=p9 sig_type=std_logic lab=VCC}
C {lab_wire.sym} -360 -10 0 0 {name=p5 sig_type=std_logic lab=TX}
C {gnd.sym} 200 170 0 0 {name=l2 lab=GND}
C {gnd.sym} -470 120 0 0 {name=l4 lab=GND}
C {lab_wire.sym} 70 30 0 0 {name=p2 sig_type=std_logic lab=CAN-}
C {lab_wire.sym} 60 10 0 0 {name=p7 sig_type=std_logic lab=CAN+}
C {lab_wire.sym} -20 160 0 0 {name=p11 sig_type=std_logic lab=RX}
C {res.sym} 200 30 0 0 {name=R6
value=10
footprint=1206
device=resistor
m=1}
C {res.sym} -420 -10 1 0 {name=R7
value=10
footprint=1206
device=resistor
m=1}
C {res.sym} 30 110 0 0 {name=R8
value=10
footprint=1206
device=resistor
m=1}
C {capa.sym} 10 190 0 0 {name=C1
m=1
value=100p
footprint=1206
device="ceramic capacitor"}
C {gnd.sym} 10 220 0 0 {name=l1 lab=GND}
C {capa.sym} -360 20 0 0 {name=C2
m=1
value=1p
footprint=1206
device="ceramic capacitor"}
C {gnd.sym} -360 50 0 0 {name=l3 lab=GND}
C {capa.sym} 150 60 0 0 {name=C4
m=1
value=5p
footprint=1206
device="ceramic capacitor"}
C {gnd.sym} 150 90 0 0 {name=l6 lab=GND}
C {can_ic.sym} -170 40 0 0 {name=x1}
