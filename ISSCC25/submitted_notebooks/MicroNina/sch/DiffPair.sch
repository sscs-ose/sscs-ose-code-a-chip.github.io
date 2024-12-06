v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -20 60 100 60 {
lab=Ibias}
N -20 -70 -20 0 {
lab=Ibias}
N 100 -70 100 0 {
lab=Iout}
N -90 30 -60 30 {
lab=Vin1}
N 140 30 180 30 {
lab=Vin2}
C {nmos.sym} -40 30 0 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} -20 -70 0 0 {name=p1 sig_type=std_logic lab=Ibias}
C {lab_pin.sym} 100 -70 0 1 {name=p2 sig_type=std_logic lab=Iout}
C {nmos.sym} 120 30 0 1 {name=M3 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} 180 30 0 1 {name=p3 sig_type=std_logic lab=Vin2}
C {lab_pin.sym} -90 30 0 0 {name=p4 sig_type=std_logic lab=Vin1

}
C {lab_pin.sym} 50 60 1 1 {name=p5 sig_type=std_logic lab=Ibias
}
