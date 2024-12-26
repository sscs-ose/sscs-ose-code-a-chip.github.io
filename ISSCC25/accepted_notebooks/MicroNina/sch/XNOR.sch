v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -40 -130 -40 -80 {
lab=Ibias}
N -40 -110 -10 -110 {
lab=Ibias}
N -100 -80 30 -80 {
lab=Ibias}
N -100 -80 -40 -80 {
lab=Ibias}
N -160 -50 -140 -50 {
lab=VIN1}
N -140 -50 -140 10 {
lab=VIN1}
N -140 10 -40 10 {
lab=VIN1}
N -40 10 0 -20 {
lab=VIN1}
N 0 -20 30 -20 {
lab=VIN1}
N 70 -50 100 -50 {
lab=VIN2}
N 70 -50 70 30 {
lab=VIN2}
N -40 30 70 30 {
lab=VIN2}
N -70 -20 -40 30 {
lab=VIN2}
N -100 -20 -70 -20 {
lab=VIN2}
C {nmos.sym} -120 -50 0 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} -40 -130 0 0 {name=p1 sig_type=std_logic lab=Ibias}
C {lab_pin.sym} 100 -50 0 1 {name=p2 sig_type=std_logic lab=VIN2}
C {lab_pin.sym} -10 -110 0 1 {name=p4 sig_type=std_logic lab=VOUT
}
C {nmos.sym} 50 -50 0 1 {name=M3 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} -160 -50 0 0 {name=p3 sig_type=std_logic lab=VIN1}
