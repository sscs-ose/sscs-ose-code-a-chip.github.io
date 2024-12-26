v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -180 -120 -180 -70 {
lab=VDD}
N -80 90 -80 120 {
lab=GND}
N -80 10 -50 10 {
lab=VTIE}
N -180 -10 -180 30 {
lab=#net1}
N -140 -40 -140 -0 {
lab=#net1}
N -140 0 -140 30 {
lab=#net1}
N -180 30 -180 60 {
lab=#net1}
N -140 30 -140 60 {
lab=#net1}
N -180 60 -120 60 {
lab=#net1}
N -80 10 -80 30 {
lab=VTIE}
C {pmos.sym} -160 -40 0 1 {name=M1 
model=DMP2035U 
device=DMP2035U 
m=1}
C {nmos.sym} -100 60 0 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} -180 -120 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -50 10 0 1 {name=p4 sig_type=std_logic lab=VTIE

}
C {gnd.sym} -80 120 0 0 {name=l1 lab=GND}
