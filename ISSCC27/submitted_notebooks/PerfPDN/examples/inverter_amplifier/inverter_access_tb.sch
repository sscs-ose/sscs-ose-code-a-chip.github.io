v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
F {}
E {}
T {Analog inverter amplifier - 1.8 V, TT, 27 C, 100 fF} -300 -260 0 0 0.5 0.5 {}
N 530 120 570 120 {lab=out}
N 530 120 530 130 {lab=out}
N 530 190 530 210 {lab=GND}
N 10 100 50 100 {lab=in}
N 350 140 390 140 {lab=GND}
N 390 140 390 160 {lab=GND}
N -300 -80 -300 -60 {lab=vdd}
N -300 0 -300 20 {lab=GND}
N -200 0 -200 30 {lab=in}
N -200 90 -200 110 {lab=GND}
N 350 120 530 120 {lab=out}
N 350 100 390 100 {lab=vdd}
N 390 60 390 100 {lab=vdd}
C {devices/lab_pin.sym} 390 60 3 0 {name=p1 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 10 100 0 0 {name=p3 sig_type=std_logic lab=in}
C {devices/lab_pin.sym} 570 120 2 0 {name=p4 sig_type=std_logic lab=out}
C {devices/lab_pin.sym} -300 -80 3 0 {name=p5 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} -200 0 3 0 {name=p6 sig_type=std_logic lab=in}
C {devices/gnd.sym} 390 160 0 0 {name=l2 lab=GND}
C {devices/gnd.sym} 530 210 0 0 {name=l3 lab=GND}
C {devices/gnd.sym} -300 20 0 0 {name=l4 lab=GND}
C {devices/gnd.sym} -200 110 0 0 {name=l5 lab=GND}
C {devices/capa.sym} 530 160 0 0 {name=C1
m=1
value=100f
footprint=1206
device="ceramic capacitor"}
C {devices/vsource.sym} -300 -30 0 0 {name=Vdd value=1.8}
C {devices/vsource.sym} -200 60 0 0 {name=Vin value="dc 0.89 ac 1 sin(0.89 1m 10Meg)"}
C {devices/code.sym} -300 180 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value="
.lib $::SKYWATER_MODELS/sky130.lib.spice tt
"}
C {devices/code.sym} 260 -130 0 0 {name=NGSPICE only_toplevel=true
value="
.option scale=1e-6
.temp 27
.control
set wr_singlescale
set wr_vecnames
op
print v(in) v(out) i(Vdd)
ac dec 50 1k 100G
let gain_db=db(v(out))
wrdata analog_ac.txt gain_db
tran 500p 600n
let isupply=-i(Vdd)
meas tran iavg AVG isupply from=400n to=600n
wrdata analog_signal.txt v(in) v(out) isupply
.endc
"}

C {inv.sym} 200 120 0 0 {name=x1}
