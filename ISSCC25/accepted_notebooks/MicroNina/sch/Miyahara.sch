v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -120 130 -120 150 {
lab=#net1}
N 60 130 60 150 {
lab=#net1}
N -20 150 -20 170 {
lab=#net1}
N -20 230 -20 260 {
lab=GND}
N 60 150 180 150 {
lab=#net1}
N 180 130 180 140 {
lab=#net1}
N 180 130 180 140 {
lab=#net1}
N 180 140 180 150 {
lab=#net1}
N -240 150 -120 150 {
lab=#net1}
N -240 130 -240 150 {
lab=#net1}
N -120 30 -120 70 {
lab=#net2}
N -240 50 -240 70 {
lab=#net2}
N -240 50 -120 50 {
lab=#net2}
N 60 30 60 70 {
lab=#net3}
N 180 50 180 70 {
lab=#net3}
N 60 50 180 50 {
lab=#net3}
N -200 -120 -200 -100 {
lab=GND}
N -200 -100 -110 -100 {
lab=GND}
N -110 -120 -110 -100 {
lab=GND}
N 50 -120 50 -100 {
lab=GND}
N 50 -100 140 -100 {
lab=GND}
N 140 -120 140 -100 {
lab=GND}
N -200 -180 -110 -180 {
lab=#net4}
N 50 -180 140 -180 {
lab=#net5}
N -70 -260 -70 -150 {
lab=#net5}
N 10 -260 10 -150 {
lab=#net4}
N -110 -350 -110 -290 {
lab=#net6}
N 50 -340 50 -290 {
lab=#net7}
N -190 -290 -110 -290 {
lab=#net6}
N 50 -290 130 -290 {
lab=#net7}
N -240 -260 -240 -150 {
lab=#net2}
N -240 -380 -240 -260 {
lab=#net2}
N -240 -380 -150 -380 {
lab=#net2}
N 180 -260 180 -150 {
lab=#net3}
N 90 -370 180 -370 {
lab=#net3}
N 180 -370 180 -260 {
lab=#net3}
N -110 -230 -110 -180 {
lab=#net4}
N 50 -230 50 -180 {
lab=#net5}
N -110 -210 10 -210 {
lab=#net4}
N -70 -200 50 -200 {
lab=#net5}
N -130 0 -0 0 {
lab=CLK}
N -110 -440 -110 -410 {
lab=VDD}
N 50 -440 50 -400 {
lab=VDD}
N -120 -70 -120 -30 {
lab=VDD}
N 60 -70 60 -30 {
lab=VDD}
N -120 150 60 150 {
lab=#net1}
N -240 -150 -240 60 {
lab=#net2}
N 180 -150 180 50 {
lab=#net3}
N -320 100 -280 100 {
lab=Vb}
N 100 100 130 100 {
lab=Vin+}
N 220 100 270 100 {
lab=VCh}
N 130 100 140 100 {
lab=Vin+}
N 140 100 140 110 {
lab=Vin+}
N -180 100 -180 120 {
lab=Vin-}
N -180 100 -160 100 {
lab=Vin-}
N 270 100 270 120 {
lab=VCh}
N -190 -20 -190 0 {
lab=CLK}
N -190 0 -160 0 {
lab=CLK}
N 130 -290 140 -290 {
lab=#net7}
N -200 -290 -190 -290 {
lab=#net6}
N 20 200 70 200 {
lab=CLK}
N 70 200 70 220 {
lab=CLK}
N 0 -0 20 0 {
lab=CLK}
N -160 0 -130 -0 {
lab=CLK}
C {nmos.sym} 80 100 2 0 {name=M2 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 0 200 2 0 {name=M4 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} -140 100 2 1 {name=M5 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {gnd.sym} -20 260 0 0 {name=l1 lab=GND}
C {nmos.sym} -260 100 2 1 {name=M1 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 200 100 2 0 {name=M3 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} -220 -150 2 1 {name=M6 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} -90 -150 2 0 {name=M7 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 30 -150 2 1 {name=M8 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 160 -150 2 0 {name=M9 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} -220 -260 2 1 {name=M10 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {nmos.sym} 160 -260 2 0 {name=M11 model=M2N7002 device=2N7002 footprint=SOT23 m=1}
C {pmos.sym} 30 -260 0 0 {name=M12 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} -130 -380 0 0 {name=M13 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} -90 -260 0 1 {name=M14 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} 70 -370 0 1 {name=M15 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} -140 0 0 0 {name=M16 
model=DMP2035U 
device=DMP2035U 
m=1}
C {pmos.sym} 40 0 0 0 {name=M17 
model=DMP2035U 
device=DMP2035U 
m=1}
C {gnd.sym} -160 -100 0 0 {name=l2 lab=GND}
C {gnd.sym} 100 -100 0 0 {name=l3 lab=GND}
C {gnd.sym} 140 -230 0 0 {name=l4 lab=GND}
C {gnd.sym} 100 -100 0 0 {name=l5 lab=GND}
C {gnd.sym} -200 -230 0 0 {name=l6 lab=GND}
C {lab_pin.sym} -110 -440 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 50 -440 0 0 {name=p2 sig_type=std_logic lab=VDD
}
C {lab_pin.sym} -120 -70 0 0 {name=p3 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 60 -70 0 0 {name=p4 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -320 100 0 0 {name=p5 sig_type=std_logic lab=Vb
}
C {lab_pin.sym} -180 120 0 0 {name=p6 sig_type=std_logic lab=Vin-}
C {lab_pin.sym} 140 110 0 0 {name=p7 sig_type=std_logic lab=Vin+}
C {lab_pin.sym} 270 120 0 0 {name=p8 sig_type=std_logic lab=VCh}
C {lab_pin.sym} -190 -20 0 0 {name=p9 sig_type=std_logic lab=CLK}
C {lab_pin.sym} 70 220 0 0 {name=p10 sig_type=std_logic lab=CLK}
