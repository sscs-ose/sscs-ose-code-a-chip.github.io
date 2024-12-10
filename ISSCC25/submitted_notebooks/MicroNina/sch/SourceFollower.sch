v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -230 0 -200 0 {
lab=Vin2}
N -160 -50 -120 -50 {
lab=Vin2}
N -160 -90 -160 -30 {
lab=Vin2}
N -230 -120 -200 -120 {
lab=Vin1}
N -160 -180 -160 -150 {
lab=VDD}
C {nmos.sym} -180 -120 0 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} -160 -180 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {nmos.sym} -180 0 0 0 {name=M3 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {lab_pin.sym} -120 -50 0 1 {name=p3 sig_type=std_logic lab=Vin2}
C {lab_pin.sym} -230 0 0 0 {name=p4 sig_type=std_logic lab=Vin2


}
C {lab_pin.sym} -230 -120 0 0 {name=p6 sig_type=std_logic lab=Vin1

}
C {gnd.sym} -160 30 0 0 {name=l1 lab=GND}
