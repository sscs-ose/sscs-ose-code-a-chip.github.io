v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 0 -240 50 -240 {lab=#net1}
N 60 -240 60 -120 {lab=#net1}
N 50 -240 60 -240 {lab=#net1}
N 0 -220 20 -220 {lab=#net2}
N 20 -220 20 -120 {lab=#net2}
N -300 -210 -140 -210 {lab=#net3}
N -230 -20 -40 -20 {lab=Vin2p}
N -90 -50 -40 -50 {lab=Vin1p}
N -230 40 -40 40 {lab=Vin2n}
N -90 10 -40 10 {lab=Vin1n}
N 120 -50 150 -50 {lab=Vout1p}
N 120 -20 150 -20 {lab=Vout1n}
N 120 10 150 10 {lab=Vout2p}
N 120 40 150 40 {lab=Vout2n}
C {clk.sym} 10 -230 0 0 {name=x2}
C {gnd.sym} -140 -230 1 0 {name=l1 lab=GND}
C {vsource.sym} -230 -250 1 0 {name=VDD value=3.3 savecurrent=false}
C {gnd.sym} -260 -250 1 0 {name=l2 lab=GND}
C {res.sym} -170 -250 3 0 {name=R1
value=150m
footprint=1206
device=resistor
m=1}
C {vsource.sym} -390 -210 1 0 {name=Vclkin value="PULSE(0 3.3 0 100n 100n 250u 500u)" savecurrent=false}
C {gnd.sym} -420 -210 1 0 {name=l3 lab=GND}
C {res.sym} -330 -210 3 0 {name=R2
value=50
footprint=1206
device=resistor
m=1}
C {switch_B.sym} 100 100 0 0 {name=x1}
C {devices/code_shown.sym} 60 -320 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
C {devices/code_shown.sym} 270 -220 0 0 {name=NGSPICE only_toplevel=true
value="
.tran 500u 0.5m
.control
run
plot v(Vin1p)-v(Vin1n)
plot v(Vin2p)-v(Vin2n)
plot v(Vout1p)-v(Vout1n)
plot v(Vout2p)-v(Vout2n)
.endc
"}
C {vsource.sym} -180 -50 1 0 {name=Vinp value=1.75 savecurrent=false}
C {gnd.sym} -210 -50 1 0 {name=l5 lab=GND}
C {res.sym} -120 -50 3 0 {name=R3
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -320 -20 1 0 {name=Vinn value=1.55 savecurrent=false}
C {gnd.sym} -350 -20 1 0 {name=l7 lab=GND}
C {res.sym} -260 -20 3 0 {name=R4
value=50k
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -60 -50 1 0 {name=p3 sig_type=std_logic lab=Vin1p}
C {lab_pin.sym} -60 -20 3 0 {name=p4 sig_type=std_logic lab=Vin2p}
C {vsource.sym} -180 10 1 0 {name=Vinp1 value=1.85 savecurrent=false}
C {gnd.sym} -210 10 1 0 {name=l4 lab=GND}
C {res.sym} -120 10 3 0 {name=R5
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -320 40 1 0 {name=Vinn1 value=1.55 savecurrent=false}
C {gnd.sym} -350 40 1 0 {name=l6 lab=GND}
C {res.sym} -260 40 3 0 {name=R6
value=50k
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -60 10 1 0 {name=p1 sig_type=std_logic lab=Vin1n}
C {lab_pin.sym} -60 40 3 0 {name=p2 sig_type=std_logic lab=Vin2n}
C {gnd.sym} 60 100 0 0 {name=l8 lab=GND}
C {vsource.sym} 20 190 0 0 {name=VDD1 value=3.3 savecurrent=false}
C {gnd.sym} 20 220 0 0 {name=l9 lab=GND}
C {res.sym} 20 130 2 0 {name=R7
value=150m
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} 140 -50 1 0 {name=p5 sig_type=std_logic lab=Vout1p}
C {lab_pin.sym} 130 -20 3 0 {name=p6 sig_type=std_logic lab=Vout1n}
C {noconn.sym} 150 -50 0 0 {name=l10
lab=Vout1p}
C {noconn.sym} 150 -20 0 0 {name=l11}
C {lab_pin.sym} 140 10 1 0 {name=p7 sig_type=std_logic lab=Vout2p}
C {lab_pin.sym} 130 40 3 0 {name=p8 sig_type=std_logic lab=Vout2n}
C {noconn.sym} 150 10 0 0 {name=l12
lab=Vout2p}
C {noconn.sym} 150 40 0 0 {name=l13
lab=Vout2p}
