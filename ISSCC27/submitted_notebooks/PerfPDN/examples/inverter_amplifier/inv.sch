v {xschem version=3.4.4 file_version=1.2
# Explicit MOS expressions support the installed Xschem 3.4.4.
}
G {}
K {}
V {}
S {}
F {}
E {}
T {Analog inverter amplifier - SKY130} -170 -190 0 0 0.35 0.35 {}
T {VDD = 1.8 V | VIN = 0.89284 V | VOUT target = 0.9 V} -170 -150 0 0 0.22 0.22 {}
N 20 40 20 60 {lab=out}
N 20 -10 160 -10 {lab=vdd}
N 160 -70 160 -10 {lab=vdd}
N 20 -70 160 -70 {lab=vdd}
N 20 -70 20 -40 {lab=vdd}
N 20 90 160 90 {lab=vss}
N 160 90 160 180 {lab=vss}
N 20 180 160 180 {lab=vss}
N 20 120 20 180 {lab=vss}
N -60 90 -20 90 {lab=in}
N -60 -10 -20 -10 {lab=in}
N -130 40 -60 40 {lab=in}
N -60 40 -60 90 {lab=in}
N -60 -10 -60 40 {lab=in}
N 20 40 140 40 {lab=out}
N 20 20 20 40 {lab=out}
N -110 -70 20 -70 {lab=vdd}
N -100 180 20 180 {lab=vss}
C {sky130_fd_pr/pfet_01v8.sym} 0 -10 0 0  {name=M1
W=6.325
L=0.15
nf=1
mult=1
model=pfet_01v8
spiceprefix=X
format="@spiceprefix@name @pinlist sky130_fd_pr__@model L=@L W=@W nf=@nf
+ ad='int(( @nf + 1 ) / 2 ) * @W / @nf * 0.29' as='int(( @nf + 2 ) / 2 ) * @W / @nf * 0.29'
+ pd='2 * int(( @nf + 1 ) / 2 ) * ( @W / @nf + 0.29 )' ps='2 * int(( @nf + 2 ) / 2 ) * ( @W / @nf + 0.29 )'
+ nrd='0.29 / @W ' nrs='0.29 / @W ' sa=0 sb=0 sd=0 mult=@mult m=@mult" 
}
C {sky130_fd_pr/nfet_01v8.sym} 0 90 0 0  {name=M2
W=1.67
L=0.15
nf=1
mult=1
model=nfet_01v8
spiceprefix=X
format="@spiceprefix@name @pinlist sky130_fd_pr__@model L=@L W=@W nf=@nf
+ ad='int(( @nf + 1 ) / 2 ) * @W / @nf * 0.29' as='int(( @nf + 2 ) / 2 ) * @W / @nf * 0.29'
+ pd='2 * int(( @nf + 1 ) / 2 ) * ( @W / @nf + 0.29 )' ps='2 * int(( @nf + 2 ) / 2 ) * ( @W / @nf + 0.29 )'
+ nrd='0.29 / @W ' nrs='0.29 / @W ' sa=0 sb=0 sd=0 mult=@mult m=@mult" 
}
C {ipin.sym} -130 40 0 0 {name=p1 lab=in
}
C {opin.sym} 140 40 0 0 {name=p2 lab=out}
C {iopin.sym} -110 -70 2 0 {name=p3 lab=vdd}
C {iopin.sym} -100 180 2 0 {name=p4 lab=vss}
