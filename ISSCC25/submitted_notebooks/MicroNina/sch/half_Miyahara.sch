v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 150 30 150 50 {
lab=#net1}
N 30 50 150 50 {
lab=#net1}
N 30 30 30 50 {
lab=#net1}
N 150 -70 150 -30 {
lab=#net2}
N 30 -50 30 -30 {
lab=#net2}
N 30 -50 150 -50 {
lab=#net2}
N 70 -220 70 -200 {
lab=GND}
N 70 -200 160 -200 {
lab=GND}
N 160 -220 160 -200 {
lab=GND}
N 70 -280 160 -280 {
lab=#net4}
N 200 -360 200 -250 {
lab=#net5}
N 160 -450 160 -390 {
lab=#net6}
N 80 -390 160 -390 {
lab=#net6}
N 30 -360 30 -250 {
lab=#net2}
N 30 -480 30 -360 {
lab=#net2}
N 30 -480 120 -480 {
lab=#net2}
N 160 -330 160 -280 {
lab=#net4}
N 160 -540 160 -510 {
lab=VDD}
N 150 -170 150 -130 {
lab=VDD}
N 30 -250 30 -40 {
lab=#net2}
N -50 0 -10 0 {
lab=Vb}
N 90 0 90 20 {
lab=Vin-}
N 90 0 110 0 {
lab=Vin-}
N 80 -120 80 -100 {
lab=CLK}
N 80 -100 110 -100 {
lab=CLK}
N 70 -390 80 -390 {
lab=#net6}
N 110 -100 140 -100 {
lab=CLK}
C {nmos.sym} 130 0 2 1 {name=M5 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 10 0 2 1 {name=M1 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 50 -250 2 1 {name=M6 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 180 -250 2 0 {name=M7 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 50 -360 2 1 {name=M10 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {pmos.sym} 140 -480 0 0 {name=M13 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} 180 -360 0 1 {name=M14 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} 130 -100 0 0 {name=M16 
model=DMP2035U 
device=DMP2035U 
m=1}
C {gnd.sym} 110 -200 0 0 {name=l2 lab=GND}
C {gnd.sym} 70 -330 0 0 {name=l6 lab=GND}
C {lab_pin.sym} 160 -540 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 150 -170 0 0 {name=p3 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -50 0 0 0 {name=p5 sig_type=std_logic lab=Vb
}
C {lab_pin.sym} 90 20 0 0 {name=p6 sig_type=std_logic lab=Vin-}
C {lab_pin.sym} 80 -120 0 0 {name=p9 sig_type=std_logic lab=CLK}
