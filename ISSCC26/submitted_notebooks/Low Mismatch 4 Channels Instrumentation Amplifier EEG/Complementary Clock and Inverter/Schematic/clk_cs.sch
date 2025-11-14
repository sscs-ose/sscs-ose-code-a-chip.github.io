v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 690 -690 690 -580 {lab=CLK_IN}
N 500 -630 690 -630 {lab=CLK_IN}
N 730 -660 730 -600 {lab=_CLK}
N 730 -630 870 -630 {lab=_CLK}
N 730 -750 730 -720 {lab=#net3}
N 730 -550 730 -500 {lab=VSS}
N 730 -690 780 -690 {lab=#net3}
N 780 -750 780 -690 {lab=#net3}
N 730 -750 780 -750 {lab=#net3}
N 730 -580 780 -580 {lab=VSS}
N 780 -580 780 -500 {lab=VSS}
N 730 -500 770 -500 {lab=VSS}
N 770 -500 780 -500 {lab=VSS}
N 440 -340 440 -230 {lab=CLK_IN}
N 480 -310 480 -250 {lab=#net4}
N 480 -400 480 -370 {lab=#net3}
N 480 -200 480 -150 {lab=VSS}
N 480 -340 530 -340 {lab=#net3}
N 530 -400 530 -340 {lab=#net3}
N 480 -400 530 -400 {lab=#net3}
N 480 -230 530 -230 {lab=VSS}
N 530 -230 530 -150 {lab=VSS}
N 480 -150 520 -150 {lab=VSS}
N 520 -150 530 -150 {lab=VSS}
N 380 -420 380 -290 {lab=CLK_IN}
N 380 -290 440 -290 {lab=CLK_IN}
N 690 -340 690 -230 {lab=#net4}
N 730 -310 730 -250 {lab=CLK}
N 730 -400 730 -370 {lab=#net3}
N 730 -200 730 -150 {lab=VSS}
N 730 -340 780 -340 {lab=#net3}
N 780 -400 780 -340 {lab=#net3}
N 730 -400 780 -400 {lab=#net3}
N 730 -230 780 -230 {lab=VSS}
N 780 -230 780 -150 {lab=VSS}
N 730 -150 770 -150 {lab=VSS}
N 770 -150 780 -150 {lab=VSS}
N 480 -290 690 -290 {lab=#net4}
N 730 -290 870 -290 {lab=CLK}
N 530 -400 730 -400 {lab=#net3}
N 530 -150 730 -150 {lab=VSS}
N 870 -290 1000 -290 {lab=CLK}
N 870 -630 1000 -630 {lab=_CLK}
N 780 -500 920 -500 {lab=VSS}
N 780 -150 910 -150 {lab=VSS}
N 1080 -500 1080 -150 {lab=VSS}
N 920 -150 1080 -150 {lab=VSS}
N 920 -500 1070 -500 {lab=VSS}
N 1070 -500 1080 -500 {lab=VSS}
N 910 -150 920 -150 {lab=VSS}
N 380 -630 380 -420 {lab=CLK_IN}
N 380 -630 500 -630 {lab=CLK_IN}
N 250 -420 380 -420 {lab=CLK_IN}
N 530 -750 730 -750 {lab=#net3}
N 530 -750 530 -400 {lab=#net3}
N 730 -500 730 -480 {lab=VSS}
C {symbols/pfet_03v3.sym} 710 -690 0 0 {name=M11
L=0.3u
W=1u
nf=1
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
C {symbols/nfet_03v3.sym} 710 -580 0 0 {name=M12
L=0.3u
W=0.5u
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
C {symbols/pfet_03v3.sym} 460 -340 0 0 {name=M13
L=0.3u
W=1u
nf=1
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
C {symbols/nfet_03v3.sym} 460 -230 0 0 {name=M14
L=0.3u
W=0.5u
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
C {symbols/pfet_03v3.sym} 710 -340 0 0 {name=M15
L=0.3u
W=1u
nf=1
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
C {symbols/nfet_03v3.sym} 710 -230 0 0 {name=M16
L=0.3u
W=0.5u
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
C {opin.sym} 1000 -290 0 0 {name=p1 sig_type=std_logic lab=CLK}
C {opin.sym} 1000 -630 0 0 {name=p2 sig_type=std_logic lab=_CLK}
C {ipin.sym} 250 -420 0 0 {name=p12 lab=CLK_IN}
C {ipin.sym} 730 -480 0 0 {name=p7 lab=VSS}
C {ipin.sym} 730 -750 1 0 {name=p10 lab=VDD}
C {devices/code_shown.sym} 260 -920 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
"}
