v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N -1080 -530 -980 -530 {lab=Vin1}
N -980 -590 -980 -460 {lab=Vin1}
N -920 -590 -920 -460 {lab=#net1}
N -950 -590 -950 -540 {lab=VSS}
N -950 -500 -950 -460 {lab=VDD}
N -950 -680 -950 -630 {lab=_CLK}
N -950 -420 -950 -360 {lab=CLK}
N -920 -530 -870 -530 {lab=#net1}
N -920 -280 -920 -150 {lab=#net2}
N -980 -280 -980 -150 {lab=Vin2}
N -950 -200 -950 -150 {lab=VSS}
N -950 -280 -950 -240 {lab=VDD}
N -950 -110 -950 -60 {lab=_CLK}
N -950 -360 -950 -320 {lab=CLK}
N -1080 -220 -980 -220 {lab=Vin2}
N -920 -220 -870 -220 {lab=#net2}
N -870 -530 -750 -530 {lab=#net1}
N -870 -220 -750 -220 {lab=#net2}
N -750 -220 -600 -220 {lab=#net2}
N -750 -530 -600 -530 {lab=#net1}
N -480 -590 -480 -460 {lab=#net1}
N -420 -590 -420 -460 {lab=#net3}
N -450 -590 -450 -540 {lab=VSS}
N -450 -500 -450 -460 {lab=VDD}
N -450 -680 -450 -630 {lab=CLK1}
N -450 -420 -450 -360 {lab=_CLK1}
N -420 -530 -370 -530 {lab=#net3}
N -420 -280 -420 -150 {lab=#net4}
N -480 -280 -480 -150 {lab=#net2}
N -450 -200 -450 -150 {lab=VSS}
N -450 -280 -450 -240 {lab=VDD}
N -450 -110 -450 -60 {lab=CLK1}
N -450 -360 -450 -320 {lab=_CLK1}
N -600 -530 -480 -530 {lab=#net1}
N -600 -220 -480 -220 {lab=#net2}
N -370 -530 -300 -530 {lab=#net3}
N -420 -220 -380 -220 {lab=#net4}
N -150 -530 -60 -530 {lab=Vout1}
N -300 -430 -300 -390 {lab=#net3}
N -150 -530 -150 -490 {lab=Vout1}
N -300 -530 -300 -490 {lab=#net3}
N -750 -420 -750 -390 {lab=#net1}
N -600 -420 -600 -390 {lab=#net1}
N -750 -530 -750 -480 {lab=#net1}
N -600 -530 -600 -480 {lab=#net1}
N -750 -330 -750 -300 {lab=#net2}
N -600 -330 -600 -300 {lab=#net2}
N -750 -240 -750 -220 {lab=#net2}
N -600 -240 -600 -220 {lab=#net2}
N -300 -330 -300 -290 {lab=#net4}
N -300 -230 -300 -220 {lab=#net4}
N -100 -220 -60 -220 {lab=Vout2}
N -150 -430 -150 -390 {lab=Vout1}
N -150 -330 -150 -290 {lab=Vout2}
N -150 -230 -150 -220 {lab=Vout2}
N -300 -490 -300 -430 {lab=#net3}
N -150 -490 -150 -430 {lab=Vout1}
N -380 -220 -300 -220 {lab=#net4}
N -150 -220 -100 -220 {lab=Vout2}
N -300 -290 -300 -230 {lab=#net4}
N -150 -290 -150 -230 {lab=Vout2}
N -600 -300 -600 -240 {lab=#net2}
N -750 -300 -750 -240 {lab=#net2}
N -750 -480 -750 -420 {lab=#net1}
N -600 -480 -600 -420 {lab=#net1}
N -240 -530 -150 -530 {lab=Vout1}
N -300 -220 -280 -220 {lab=#net4}
N -220 -220 -150 -220 {lab=Vout2}
C {symbols/nfet_03v3.sym} -950 -610 1 0 {name=M3
L=0.3u
W=5u
nf=3
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
C {symbols/pfet_03v3.sym} -950 -440 3 0 {name=M4
L=0.3u
W=5u
nf=3
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
C {ipin.sym} -950 -540 0 0 {name=p6 sig_type=std_logic lab=VSS
nf=1
L=0.3u
m=1
W=4u}
C {ipin.sym} -950 -500 0 0 {name=p7 sig_type=std_logic lab=VDD
nf=1
L=0.3u
m=1
W=4u}
C {ipin.sym} -950 -680 0 0 {name=p8 sig_type=std_logic lab=_CLK}
C {ipin.sym} -950 -390 0 0 {name=p9 sig_type=std_logic lab=CLK
L=0.3u
nf=1
m=5
W=4u}
C {symbols/nfet_03v3.sym} -950 -130 3 0 {name=M7
L=0.3u
W=5u
nf=3
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
C {symbols/pfet_03v3.sym} -950 -300 1 0 {name=M8
L=0.3u
W=5u
nf=3
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
C {lab_wire.sym} -950 -190 2 0 {name=p14 sig_type=std_logic lab=VSS
nf=1
L=0.3u
m=1
W=4u}
C {lab_wire.sym} -950 -260 2 0 {name=p15 sig_type=std_logic lab=VDD
nf=1
L=0.3u
m=1
W=4u}
C {lab_wire.sym} -950 -80 2 0 {name=p16 sig_type=std_logic lab=_CLK
W=4u}
C {ipin.sym} -1080 -530 0 0 {name=p1 sig_type=std_logic lab=Vin1}
C {ipin.sym} -1080 -220 0 0 {name=p17 sig_type=std_logic lab=Vin2}
C {symbols/nfet_03v3.sym} -450 -610 1 0 {name=M19
L=0.3u
W=5u
nf=3
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
C {symbols/pfet_03v3.sym} -450 -440 3 0 {name=M20
L=0.3u
W=5u
nf=3
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
C {lab_wire.sym} -450 -550 0 0 {name=p26 sig_type=std_logic lab=VSS
nf=1
L=0.3u
m=1
W=4u}
C {lab_wire.sym} -450 -480 0 0 {name=p27 sig_type=std_logic lab=VDD
nf=1
L=0.3u
m=1
W=4u}
C {ipin.sym} -450 -680 0 0 {name=p28 sig_type=std_logic lab=CLK1
W=4u}
C {ipin.sym} -450 -390 0 0 {name=p29 sig_type=std_logic lab=_CLK1
L=0.3u
nf=1
m=5
W=4u}
C {symbols/nfet_03v3.sym} -450 -130 3 0 {name=M23
L=0.3u
W=5u
nf=3
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
C {symbols/pfet_03v3.sym} -450 -300 1 0 {name=M24
L=0.3u
W=5u
nf=3
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
C {lab_wire.sym} -450 -190 2 0 {name=p34 sig_type=std_logic lab=VSS
nf=1
L=0.3u
m=1
W=4u}
C {lab_wire.sym} -450 -260 2 0 {name=p35 sig_type=std_logic lab=VDD
nf=1
L=0.3u
m=1
W=4u}
C {lab_wire.sym} -450 -80 2 0 {name=p36 sig_type=std_logic lab=CLK1
W=4u}
C {opin.sym} -60 -530 1 0 {name=p30 sig_type=std_logic lab=Vout1}
C {opin.sym} -60 -220 3 0 {name=p37 sig_type=std_logic lab=Vout2}
C {symbols/cap_mim_1f0fF.sym} -600 -360 0 0 {name=C1
W=10e-6
L=10e-6
model=cap_mim_2f0fF
spiceprefix=X
m=3}
C {symbols/cap_mim_1f0fF.sym} -750 -360 0 0 {name=C2
W=10e-6
L=10e-6
model=cap_mim_2f0fF
spiceprefix=X
m=3}
C {symbols/cap_mim_1f0fF.sym} -300 -360 0 0 {name=C3
W=10e-6
L=10e-6
model=cap_mim_2f0fF
spiceprefix=X
m=3}
C {ind.sym} -270 -530 3 0 {name=L13
m=1
value=20n
footprint=1206
device=inductor}
C {capa.sym} -150 -360 0 0 {name=C4
m=1
value=20p
footprint=1206
device="ceramic capacitor"}
C {ind.sym} -250 -220 3 0 {name=L14
m=1
value=20n
footprint=1206
device=inductor}
C {devices/code_shown.sym} -830 -790 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
