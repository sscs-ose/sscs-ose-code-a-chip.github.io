v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 310 -570 310 -550 {lab=#net1}
N 230 -550 310 -550 {lab=#net1}
N 310 -550 390 -550 {lab=#net1}
N 230 -490 230 -430 {lab=out1}
N 390 -490 390 -430 {lab=out2}
N 230 -520 260 -520 {lab=#net1}
N 260 -550 260 -520 {lab=#net1}
N 170 -600 270 -600 {lab=VB}
N 170 -650 310 -650 {lab=VDD}
N 310 -650 310 -630 {lab=VDD}
N 310 -600 330 -600 {lab=VDD}
N 330 -650 330 -600 {lab=VDD}
N 310 -650 330 -650 {lab=VDD}
N 230 -370 230 -310 {lab=#net2}
N 390 -370 390 -310 {lab=#net2}
N 230 -340 390 -340 {lab=#net2}
N 230 -250 230 -220 {lab=VSS}
N 230 -220 390 -220 {lab=VSS}
N 390 -250 390 -220 {lab=VSS}
N 390 -280 420 -280 {lab=VSS}
N 420 -280 420 -220 {lab=VSS}
N 390 -220 420 -220 {lab=VSS}
N 230 -400 260 -400 {lab=#net2}
N 260 -400 260 -340 {lab=#net2}
N 290 -460 290 -320 {lab=out1}
N 230 -460 290 -460 {lab=out1}
N 330 -280 350 -280 {lab=out2}
N 330 -460 330 -280 {lab=out2}
N 330 -460 390 -460 {lab=out2}
N 100 -460 230 -460 {lab=out1}
N 390 -460 520 -460 {lab=out2}
N 100 -400 190 -400 {lab=in1}
N 460 -440 460 -400 {lab=in2}
N 460 -400 520 -400 {lab=in2}
N 150 -520 190 -520 {lab=in1}
N 150 -520 150 -400 {lab=in1}
N 150 -400 150 -210 {lab=in1}
N 460 -400 460 -210 {lab=in2}
N 150 -150 150 -130 {lab=VCM}
N 150 -130 460 -130 {lab=VCM}
N 460 -150 460 -130 {lab=VCM}
N 110 -180 110 -130 {lab=VCM}
N 110 -130 150 -130 {lab=VCM}
N 320 -220 320 -200 {lab=VSS}
N 460 -480 460 -440 {lab=in2}
N 320 -130 320 -100 {lab=VCM}
N 430 -520 460 -520 {lab=in2}
N 460 -520 460 -480 {lab=in2}
N 370 -520 390 -520 {lab=#net1}
N 360 -520 370 -520 {lab=#net1}
N 360 -550 360 -520 {lab=#net1}
N 360 -400 390 -400 {lab=#net2}
N 360 -400 360 -340 {lab=#net2}
N 430 -400 460 -400 {lab=in2}
N 200 -280 230 -280 {lab=VSS}
N 200 -280 200 -220 {lab=VSS}
N 200 -220 230 -220 {lab=VSS}
N 270 -280 290 -280 {lab=out1}
N 290 -320 290 -280 {lab=out1}
N 440 -180 460 -180 {lab=in2}
N 440 -230 440 -180 {lab=in2}
N 440 -230 460 -230 {lab=in2}
N 500 -180 500 -130 {lab=VCM}
N 460 -130 500 -130 {lab=VCM}
N 150 -180 170 -180 {lab=in1}
N 170 -230 170 -180 {lab=in1}
N 150 -230 170 -230 {lab=in1}
C {devices/code_shown.sym} 700 -100 0 0 {name=MODELS1 only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
.lib $::180MCU_MODELS/smbb000149.ngspice typical
"}
C {symbols/pfet_03v3.sym} 290 -600 0 0 {name=M10
L=3u
W=0.36u
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
C {symbols/pfet_03v3.sym} 210 -520 0 0 {name=M11
L=3u
W=6u
nf=6
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
C {symbols/pfet_03v3.sym} 410 -520 0 1 {name=M12
L=3u
W=6u
nf=6
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
C {symbols/nfet_03v3.sym} 210 -400 0 0 {name=M13
L=3u
W=3u
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
C {symbols/nfet_03v3.sym} 410 -400 0 1 {name=M14
L=3u
W=3u
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
C {symbols/nfet_03v3.sym} 250 -280 0 1 {name=M15
L=3u
W=0.36u
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
C {symbols/nfet_03v3.sym} 370 -280 0 0 {name=M16
L=3u
W=0.36u
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
C {symbols/pfet_03v3.sym} 130 -180 0 0 {name=M17
L=3u
W=0.36u
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
C {symbols/pfet_03v3.sym} 480 -180 0 1 {name=M18
L=3u
W=0.36u
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
C {opin.sym} 100 -460 2 0 {name=p11 lab=out1}
C {opin.sym} 520 -460 0 0 {name=p12 lab=out2}
C {ipin.sym} 100 -400 0 0 {name=p13 lab=in1}
C {ipin.sym} 520 -400 2 0 {name=p14 lab=in2}
C {iopin.sym} 170 -650 2 0 {name=p9 lab=VDD}
C {iopin.sym} 170 -600 2 0 {name=p10 lab=VB}
C {iopin.sym} 320 -200 1 0 {name=p15 lab=VSS}
C {iopin.sym} 320 -100 1 0 {name=p1 lab=VCM}
