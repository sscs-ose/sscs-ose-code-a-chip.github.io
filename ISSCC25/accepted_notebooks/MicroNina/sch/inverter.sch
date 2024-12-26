v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 150 -60 150 -10 {
lab=VDD}
N 110 20 110 120 {
lab=VIN}
N 150 50 150 90 {
lab=VOUT}
N 150 150 150 180 {
lab=GND}
N 150 70 180 70 {
lab=VOUT}
N 80 70 110 70 {
lab=VIN}
C {pmos.sym} 130 20 0 0 {name=M1 
model=DMP2035U 
device=DMP2035U 
m=1}
C {nmos.sym} 130 120 0 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} 150 -60 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 80 70 0 0 {name=p2 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 180 70 0 1 {name=p4 sig_type=std_logic lab=VOUT
}
C {gnd.sym} 150 180 0 0 {name=l1 lab=GND}
