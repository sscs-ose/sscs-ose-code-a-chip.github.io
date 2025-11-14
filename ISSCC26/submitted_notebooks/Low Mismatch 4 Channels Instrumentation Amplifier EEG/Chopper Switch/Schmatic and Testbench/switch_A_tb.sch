v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 90 -220 90 -100 {lab=#net1}
N 50 -200 50 -100 {lab=#net2}
N -270 -190 -110 -190 {lab=CLK_IN}
N -180 -30 10 -30 {lab=Vin2}
N 140 -50 170 -50 {lab=Vout2}
N 140 -30 170 -30 {lab=Vout1}
N -40 -50 10 -50 {lab=Vin1}
N 50 -210 50 -200 {lab=#net2}
N 40 -210 50 -210 {lab=#net2}
N 40 -230 90 -230 {lab=#net1}
N 90 -230 90 -220 {lab=#net1}
C {clk.sym} 40 -210 0 0 {name=x2}
C {gnd.sym} -110 -210 1 0 {name=l1 lab=GND}
C {vsource.sym} -200 -230 1 0 {name=VDD value=3.3 savecurrent=false}
C {gnd.sym} -230 -230 1 0 {name=l2 lab=GND}
C {res.sym} -140 -230 3 0 {name=R1
value=150m
footprint=1206
device=resistor
m=1}
C {vsource.sym} -360 -190 1 0 {name=Vclkin value="PULSE(0 3.3 0 100n 100n 125u 250u)" savecurrent=false}
C {gnd.sym} -390 -190 1 0 {name=l3 lab=GND}
C {res.sym} -300 -190 3 0 {name=R2
value=50
footprint=1206
device=resistor
m=1}
C {vsource.sym} -130 -50 1 0 {name=Vinp value=1.75 savecurrent=false}
C {gnd.sym} -160 -50 1 0 {name=l5 lab=GND}
C {res.sym} -70 -50 3 0 {name=R3
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -270 -30 1 0 {name=Vinn value=1.55 savecurrent=false}
C {gnd.sym} -300 -30 1 0 {name=l7 lab=GND}
C {res.sym} -210 -30 3 0 {name=R4
value=50k
footprint=1206
device=resistor
m=1}
C {devices/code_shown.sym} 200 -230 0 0 {name=NGSPICE only_toplevel=true
value="
.tran 500u 0.5m
.control
run
plot v(Vin1)-v(Vin2)
plot v(Vout2)-v(Vout1)
plot v(CLK_IN)
.endc
"}
C {lab_pin.sym} 160 -50 1 0 {name=p1 sig_type=std_logic lab=Vout2}
C {lab_pin.sym} 150 -30 3 0 {name=p2 sig_type=std_logic lab=Vout1}
C {gnd.sym} 90 20 0 0 {name=l4 lab=GND}
C {vsource.sym} 60 110 0 0 {name=VDD1 value=3.3 savecurrent=false}
C {gnd.sym} 60 140 0 0 {name=l6 lab=GND}
C {res.sym} 60 50 2 0 {name=R5
value=150m
footprint=1206
device=resistor
m=1}
C {switch_A.sym} -30 20 0 0 {name=x1}
C {noconn.sym} 170 -50 0 0 {name=l8}
C {noconn.sym} 170 -30 0 0 {name=l9}
C {devices/code_shown.sym} 120 -370 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
C {lab_pin.sym} -10 -30 3 0 {name=p4 sig_type=std_logic lab=Vin2}
C {lab_pin.sym} -10 -50 1 0 {name=p5 sig_type=std_logic lab=Vin1}
C {lab_pin.sym} -160 -190 3 0 {name=p6 sig_type=std_logic lab=CLK_IN}
