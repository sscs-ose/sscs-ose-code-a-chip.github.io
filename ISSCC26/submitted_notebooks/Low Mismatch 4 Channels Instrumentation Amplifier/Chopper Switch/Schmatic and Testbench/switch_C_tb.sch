v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N -450 -490 -400 -490 {lab=#net1}
N -390 -490 -390 -370 {lab=#net1}
N -400 -490 -390 -490 {lab=#net1}
N -450 -470 -430 -470 {lab=#net2}
N -430 -470 -430 -370 {lab=#net2}
N -750 -460 -590 -460 {lab=#net3}
N -710 -280 -520 -280 {lab=Vin2p}
N -570 -310 -520 -310 {lab=Vin1p}
N -710 -220 -520 -220 {lab=Vin2n}
N -570 -250 -520 -250 {lab=Vin1n}
N -300 -310 -270 -310 {lab=Vout1p}
N -300 -280 -270 -280 {lab=Vout1n}
N -300 -250 -270 -250 {lab=Vout2p}
N -300 -220 -270 -220 {lab=Vout2n}
N -300 -190 -270 -190 {lab=Vout3p}
N -300 -160 -270 -160 {lab=Vout3n}
N -300 -130 -270 -130 {lab=Vout4p}
N -300 -100 -270 -100 {lab=Vout4n}
N -710 -160 -520 -160 {lab=Vin4p}
N -570 -190 -520 -190 {lab=Vin3p}
N -710 -100 -520 -100 {lab=Vin4n}
N -570 -130 -520 -130 {lab=Vin3n}
C {clk.sym} -440 -480 0 0 {name=x2}
C {gnd.sym} -590 -480 1 0 {name=l1 lab=GND}
C {vsource.sym} -680 -500 1 0 {name=VDD value=3.3 savecurrent=false}
C {gnd.sym} -710 -500 1 0 {name=l2 lab=GND}
C {res.sym} -620 -500 3 0 {name=R1
value=150m
footprint=1206
device=resistor
m=1}
C {vsource.sym} -840 -460 1 0 {name=Vclkin value="PULSE(0 3.3 0 1n 1n 0.5m 1m)" savecurrent=false}
C {gnd.sym} -870 -460 1 0 {name=l3 lab=GND}
C {res.sym} -780 -460 3 0 {name=R2
value=50
footprint=1206
device=resistor
m=1}
C {devices/code_shown.sym} -260 -640 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
C {devices/code_shown.sym} -160 -550 0 0 {name=NGSPICE only_toplevel=true
value="
.tran 500u 4m
.control
run
plot v(Vin1p)-v(Vin1n)
plot v(Vin2p)-v(Vin2n)
plot v(Vin3p)-v(Vin3n)
plot v(Vin4p)-v(Vin4n)
plot v(Vout1p)-v(Vout1n)
plot v(Vout2p)-v(Vout2n)
plot v(Vout3p)-v(Vout3n)
plot v(Vout4p)-v(Vout4n)
.endc
"}
C {vsource.sym} -660 -310 1 0 {name=Vinp value=1.75 savecurrent=false}
C {gnd.sym} -690 -310 1 0 {name=l5 lab=GND}
C {res.sym} -600 -310 3 0 {name=R3
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -800 -280 1 0 {name=Vinn value=1.55 savecurrent=false}
C {gnd.sym} -830 -280 1 0 {name=l7 lab=GND}
C {res.sym} -740 -280 3 0 {name=R4
value=50k
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -540 -310 1 0 {name=p3 sig_type=std_logic lab=Vin1p}
C {lab_pin.sym} -540 -280 3 0 {name=p4 sig_type=std_logic lab=Vin2p}
C {vsource.sym} -660 -250 1 0 {name=Vinp1 value=1.85 savecurrent=false}
C {gnd.sym} -690 -250 1 0 {name=l4 lab=GND}
C {res.sym} -600 -250 3 0 {name=R5
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -800 -220 1 0 {name=Vinn1 value=1.55 savecurrent=false}
C {gnd.sym} -830 -220 1 0 {name=l6 lab=GND}
C {res.sym} -740 -220 3 0 {name=R6
value=50k
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -540 -250 1 0 {name=p1 sig_type=std_logic lab=Vin1n}
C {lab_pin.sym} -540 -220 3 0 {name=p2 sig_type=std_logic lab=Vin2n}
C {gnd.sym} -390 -30 0 0 {name=l8 lab=GND}
C {vsource.sym} -430 60 0 0 {name=VDD1 value=3.3 savecurrent=false}
C {gnd.sym} -430 90 0 0 {name=l9 lab=GND}
C {res.sym} -430 0 2 0 {name=R7
value=150m
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -280 -310 2 0 {name=p5 sig_type=std_logic lab=Vout1p}
C {lab_pin.sym} -280 -280 2 0 {name=p6 sig_type=std_logic lab=Vout1n}
C {noconn.sym} -270 -310 0 0 {name=l10
lab=Vout1p}
C {noconn.sym} -270 -280 0 0 {name=l11}
C {lab_pin.sym} -280 -250 2 0 {name=p7 sig_type=std_logic lab=Vout2p}
C {lab_pin.sym} -280 -220 2 0 {name=p8 sig_type=std_logic lab=Vout2n}
C {noconn.sym} -270 -250 0 0 {name=l12
lab=Vout2p}
C {noconn.sym} -270 -220 0 0 {name=l13
lab=Vout2p}
C {switch_C.sym} -410 -250 0 0 {name=x1}
C {lab_pin.sym} -280 -190 2 0 {name=p9 sig_type=std_logic lab=Vout3p}
C {noconn.sym} -270 -190 0 0 {name=l14
lab=Vout1p}
C {noconn.sym} -270 -160 0 0 {name=l15}
C {lab_pin.sym} -280 -130 2 0 {name=p10 sig_type=std_logic lab=Vout4p}
C {noconn.sym} -270 -130 0 0 {name=l16
lab=Vout2p}
C {noconn.sym} -270 -100 0 0 {name=l17
lab=Vout2p}
C {lab_pin.sym} -280 -160 2 0 {name=p11 sig_type=std_logic lab=Vout3n}
C {lab_pin.sym} -280 -100 2 0 {name=p12 sig_type=std_logic lab=Vout4n}
C {vsource.sym} -660 -190 1 0 {name=Vinp2 value=1.70 savecurrent=false}
C {gnd.sym} -690 -190 1 0 {name=l18 lab=GND}
C {res.sym} -600 -190 3 0 {name=R8
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -800 -160 1 0 {name=Vinn2 value=1.60 savecurrent=false}
C {gnd.sym} -830 -160 1 0 {name=l19 lab=GND}
C {res.sym} -740 -160 3 0 {name=R9
value=50k
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -540 -190 1 0 {name=p13 sig_type=std_logic lab=Vin3p}
C {lab_pin.sym} -540 -160 3 0 {name=p14 sig_type=std_logic lab=Vin4p}
C {vsource.sym} -660 -130 1 0 {name=Vinp3 value=1.95 savecurrent=false}
C {gnd.sym} -690 -130 1 0 {name=l20 lab=GND}
C {res.sym} -600 -130 3 0 {name=R10
value=50k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -800 -100 1 0 {name=Vinn3 value=1.45 savecurrent=false}
C {gnd.sym} -830 -100 1 0 {name=l21 lab=GND}
C {res.sym} -740 -100 3 0 {name=R11
value=50k
footprint=1206
device=resistor
m=1}
C {lab_pin.sym} -540 -130 1 0 {name=p15 sig_type=std_logic lab=Vin3n}
C {lab_pin.sym} -540 -100 3 0 {name=p16 sig_type=std_logic lab=Vin4n}
