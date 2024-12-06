v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 10 240 130 240 {
lab=GND}
N 50 210 90 210 {
lab=Ibias}
N 50 160 50 210 {
lab=Ibias}
N 10 160 50 160 {
lab=Ibias}
N 10 110 10 180 {
lab=Ibias}
N 130 110 130 180 {
lab=Iout}
C {nmos.sym} 110 210 0 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} 10 110 0 0 {name=p1 sig_type=std_logic lab=Ibias}
C {lab_pin.sym} 130 110 0 1 {name=p2 sig_type=std_logic lab=Iout}
C {nmos.sym} 30 210 0 1 {name=M3 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {gnd.sym} 70 240 0 0 {name=l1 lab=GND}
