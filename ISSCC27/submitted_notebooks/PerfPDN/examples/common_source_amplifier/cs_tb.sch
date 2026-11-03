v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
F {}
E {}
N -190 -80 -190 -60 {lab=in}
N -190 -80 -90 -80 {lab=in}
N -190 10 -190 50 {lab=0}
N 200 -40 230 -40 {lab=0}
N 230 30 230 40 {lab=0}
N 200 -60 260 -60 {lab=out}
N 260 -60 260 -10 {lab=out}
N 260 20 260 30 {lab=0}
N 230 30 260 30 {lab=0}
N 230 -40 230 30 {lab=0}
N 200 -80 260 -80 {lab=vdd}
N -250 -0 -250 50 {lab=0}
N -220 50 -190 50 {lab=0}
N -220 50 -220 60 {lab=0}
N -250 50 -220 50 {lab=0}
N -250 -110 -250 -60 {lab=vdd}
N -190 10 -90 10 {lab=0}
N -190 -0 -190 10 {lab=0}
C {cs.sym} 50 -60 0 0 {name=x1}
C {vsource.sym} -190 -30 0 0 {name=Vin value="dc 0.954725 ac 1"}
C {gnd.sym} 230 40 0 0 {name=l1 lab=0}
C {capa-2.sym} 260 -10 0 0 {name=C1
m=1
value=1p
footprint=1206
device=polarized_capacitor}
C {lab_wire.sym} 250 -80 0 0 {name=p1 sig_type=std_logic lab=vdd}
C {vsource.sym} -250 -30 0 0 {name=Vdd value=1.2 savecurrent=false}
C {gnd.sym} -220 60 0 0 {name=l2 lab=0}
C {lab_wire.sym} -250 -80 1 0 {name=p2 sig_type=std_logic lab=vdd}
C {code.sym} -280 180 0 0 {name=MODEL only_toplevel=true format="tcleval( @value )" 
value=".lib $::SKYWATER_MODELS/sky130.lib.spice tt
"
}

C {lab_pin.sym} -170 -80 0 0 {name=p3 sig_type=std_logic lab=in}
C {lab_pin.sym} 240 -60 0 0 {name=p4 sig_type=std_logic lab=out}
C {code.sym} 460 -80 0 0 {name=SIM only_toplevel=true
value=".option scale=1e-6 reltol=1e-8 abstol=1e-14
.temp 27
.control
op
ac dec 100 1k 10G
let gain_db=db(v(out))
wrdata cs_ac.txt gain_db
.endc
"}
T {Ground-return experiment: fixed input bias, 1 pF load} -280 -160 0 0 0.35 0.35 {}
