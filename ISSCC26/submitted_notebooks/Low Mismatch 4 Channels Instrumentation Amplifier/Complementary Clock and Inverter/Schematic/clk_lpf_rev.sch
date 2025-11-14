v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 900 -490 900 -450 {lab=VSS}
N 360 -740 420 -740 {lab=VDD}
N 420 -740 620 -740 {lab=VDD}
N 620 -740 670 -740 {lab=VDD}
N 620 -390 670 -390 {lab=VDD}
N 420 -390 620 -390 {lab=VDD}
N 420 -440 420 -390 {lab=VDD}
N 220 -440 420 -440 {lab=VDD}
N 760 -330 760 -220 {lab=CLK_IN}
N 800 -300 800 -240 {lab=#net1}
N 800 -390 800 -360 {lab=VDD}
N 800 -190 800 -140 {lab=VSS}
N 800 -330 850 -330 {lab=VDD}
N 850 -390 850 -330 {lab=VDD}
N 800 -390 850 -390 {lab=VDD}
N 800 -220 850 -220 {lab=VSS}
N 850 -220 850 -140 {lab=VSS}
N 800 -140 840 -140 {lab=VSS}
N 840 -140 850 -140 {lab=VSS}
N 1010 -330 1010 -220 {lab=#net1}
N 1050 -300 1050 -240 {lab=OUTN}
N 1050 -390 1050 -360 {lab=VDD}
N 1050 -190 1050 -140 {lab=VSS}
N 1050 -330 1100 -330 {lab=VDD}
N 1100 -390 1100 -330 {lab=VDD}
N 1050 -390 1100 -390 {lab=VDD}
N 1050 -220 1100 -220 {lab=VSS}
N 1100 -220 1100 -140 {lab=VSS}
N 1050 -140 1090 -140 {lab=VSS}
N 1090 -140 1100 -140 {lab=VSS}
N 800 -280 1010 -280 {lab=#net1}
N 850 -390 1050 -390 {lab=VDD}
N 850 -140 1050 -140 {lab=VSS}
N 1050 -280 1180 -280 {lab=OUTN}
N 760 -680 760 -570 {lab=INP}
N 800 -650 800 -590 {lab=#net2}
N 800 -740 800 -710 {lab=VDD}
N 800 -540 800 -490 {lab=VSS}
N 800 -680 850 -680 {lab=VDD}
N 850 -740 850 -680 {lab=VDD}
N 800 -740 850 -740 {lab=VDD}
N 800 -570 850 -570 {lab=VSS}
N 850 -570 850 -490 {lab=VSS}
N 800 -490 840 -490 {lab=VSS}
N 840 -490 850 -490 {lab=VSS}
N 1010 -680 1010 -570 {lab=#net2}
N 1050 -650 1050 -590 {lab=OUTP}
N 1050 -740 1050 -710 {lab=VDD}
N 1050 -540 1050 -490 {lab=VSS}
N 1050 -680 1100 -680 {lab=VDD}
N 1100 -740 1100 -680 {lab=VDD}
N 1050 -740 1100 -740 {lab=VDD}
N 1050 -570 1100 -570 {lab=VSS}
N 1100 -570 1100 -490 {lab=VSS}
N 1050 -490 1090 -490 {lab=VSS}
N 1090 -490 1100 -490 {lab=VSS}
N 800 -630 1010 -630 {lab=#net2}
N 850 -740 1050 -740 {lab=VDD}
N 850 -490 1050 -490 {lab=VSS}
N 1050 -630 1180 -630 {lab=OUTP}
N 670 -740 800 -740 {lab=VDD}
N 670 -390 800 -390 {lab=VDD}
N 210 -740 360 -740 {lab=VDD}
N 210 -740 210 -440 {lab=VDD}
N 210 -440 220 -440 {lab=VDD}
N 940 -780 940 -740 {lab=VDD}
N 1100 -490 1340 -490 {lab=VSS}
N 1340 -490 1340 -140 {lab=VSS}
N 1100 -140 1340 -140 {lab=VSS}
N 700 -650 760 -650 {lab=INP}
N 700 -270 760 -270 {lab=CLK_IN}
C {opin.sym} 1180 -630 0 0 {name=p25 sig_type=std_logic lab=OUTP}
C {symbols/pfet_03v3.sym} 780 -330 0 0 {name=M1
L=0.5u
W=1u
nf=2
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
C {symbols/nfet_03v3.sym} 780 -220 0 0 {name=M2
L=0.5u
W=1u
nf=1
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
C {symbols/pfet_03v3.sym} 1030 -330 0 0 {name=M5
L=0.5u
W=1u
nf=2
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
C {symbols/nfet_03v3.sym} 1030 -220 0 0 {name=M6
L=0.5u
W=1u
nf=1
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
C {opin.sym} 1180 -280 0 0 {name=p2 sig_type=std_logic lab=OUTN
}
C {symbols/pfet_03v3.sym} 780 -680 0 0 {name=M13
L=0.5u
W=1u
nf=2
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
C {symbols/nfet_03v3.sym} 780 -570 0 0 {name=M18
L=0.5u
W=1u
nf=1
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
C {symbols/pfet_03v3.sym} 1030 -680 0 0 {name=M21
L=0.5u
W=1u
nf=2
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
C {symbols/nfet_03v3.sym} 1030 -570 0 0 {name=M22
L=0.5u
W=1u
nf=1
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
C {ipin.sym} 940 -780 0 0 {name=p1 lab=VDD}
C {ipin.sym} 900 -450 0 0 {name=p4 lab=VSS}
C {ipin.sym} 700 -650 0 0 {name=p3 sig_type=std_logic lab=INP}
C {ipin.sym} 700 -270 0 0 {name=p5 sig_type=std_logic lab=INN
}
C {devices/code_shown.sym} 480 -890 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
