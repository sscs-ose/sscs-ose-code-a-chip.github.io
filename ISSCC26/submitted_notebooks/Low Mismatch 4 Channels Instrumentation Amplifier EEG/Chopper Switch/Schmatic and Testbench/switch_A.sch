v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N -320 -500 -320 -370 {lab=Vin1}
N -260 -500 -260 -370 {lab=Vout1}
N -420 -440 -320 -440 {lab=Vin1}
N -260 -440 -150 -440 {lab=Vout1}
N -290 -500 -290 -450 {lab=VSS}
N -290 -410 -290 -370 {lab=VDD}
N -290 -590 -290 -540 {lab=CLK}
N -20 -500 -20 -370 {lab=Vin1}
N 40 -500 40 -370 {lab=Vout2}
N 10 -500 10 -450 {lab=VSS}
N 10 -410 10 -370 {lab=VDD}
N 10 -590 10 -540 {lab=_CLK}
N 10 -330 10 -270 {lab=CLK}
N -380 -620 -380 -440 {lab=Vin1}
N -380 -620 -70 -620 {lab=Vin1}
N -70 -620 -70 -440 {lab=Vin1}
N -70 -440 -20 -440 {lab=Vin1}
N 40 -440 90 -440 {lab=Vout2}
N -260 -190 -260 -60 {lab=Vout2}
N -320 -190 -320 -60 {lab=Vin2}
N -290 -110 -290 -60 {lab=VSS}
N -290 -190 -290 -150 {lab=VDD}
N -290 -20 -290 30 {lab=CLK}
N -290 -290 -290 -230 {lab=_CLK}
N 40 -190 40 -60 {lab=Vout1}
N -20 -190 -20 -60 {lab=Vin2}
N 10 -110 10 -60 {lab=VSS}
N 10 -190 10 -150 {lab=VDD}
N 10 -20 10 30 {lab=_CLK}
N 10 -270 10 -230 {lab=CLK}
N -420 -130 -320 -130 {lab=Vin2}
N 40 -130 90 -130 {lab=Vout1}
N -380 -130 -380 0 {lab=Vin2}
N -380 0 -70 0 {lab=Vin2}
N -70 -130 -70 0 {lab=Vin2}
N -70 -130 -20 -130 {lab=Vin2}
N -150 -440 -150 -290 {lab=Vout1}
N -150 -290 80 -290 {lab=Vout1}
N 80 -290 80 -130 {lab=Vout1}
N -260 -130 -130 -130 {lab=Vout2}
N -130 -250 -130 -130 {lab=Vout2}
N -130 -250 60 -250 {lab=Vout2}
N 60 -440 60 -250 {lab=Vout2}
N -290 -330 -290 -290 {lab=_CLK}
C {symbols/nfet_03v3.sym} -290 -520 1 0 {name=M1
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} -290 -350 3 0 {name=M2
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {ipin.sym} -420 -440 0 0 {name=p1 lab=Vin1}
C {lab_wire.sym} -290 -290 0 0 {name=p5 sig_type=std_logic lab=_CLK}
C {symbols/nfet_03v3.sym} 10 -520 1 0 {name=M3
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 10 -350 3 0 {name=M4
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {lab_wire.sym} 10 -460 0 0 {name=p6 sig_type=std_logic lab=VSS}
C {lab_wire.sym} 10 -390 0 0 {name=p7 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 10 -300 0 0 {name=p9 sig_type=std_logic lab=CLK}
C {opin.sym} 90 -440 0 0 {name=p11 lab=Vout2}
C {symbols/nfet_03v3.sym} -290 -40 3 0 {name=M5
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} -290 -210 1 0 {name=M6
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {lab_wire.sym} -290 -100 2 0 {name=p10 sig_type=std_logic lab=VSS}
C {lab_wire.sym} -290 -170 2 0 {name=p12 sig_type=std_logic lab=VDD}
C {lab_wire.sym} -290 10 2 0 {name=p13 sig_type=std_logic lab=CLK}
C {symbols/nfet_03v3.sym} 10 -40 3 0 {name=M7
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 10 -210 1 0 {name=M8
L=0.5u
W=15u
nf=5
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {lab_wire.sym} 10 -100 2 0 {name=p14 sig_type=std_logic lab=VSS}
C {lab_wire.sym} 10 -170 2 0 {name=p15 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 10 10 2 0 {name=p16 sig_type=std_logic lab=_CLK}
C {ipin.sym} -420 -130 0 0 {name=p17 lab=Vin2}
C {opin.sym} 90 -130 0 0 {name=p18 lab=Vout1}
C {ipin.sym} -290 -590 0 0 {name=p28 lab=CLK}
C {ipin.sym} 10 -590 0 0 {name=p4 lab=_CLK}
C {ipin.sym} -290 -410 0 0 {name=p8 lab=VDD}
C {ipin.sym} -290 -450 0 0 {name=p19 lab=VSS}
C {devices/code_shown.sym} 280 -290 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
