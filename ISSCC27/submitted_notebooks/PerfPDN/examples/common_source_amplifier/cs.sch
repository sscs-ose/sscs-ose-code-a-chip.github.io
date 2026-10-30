v {xschem version=3.4.4 file_version=1.2
# Explicit MOS expressions support the installed Xschem 3.4.4.
}
G {}
K {}
V {}
S {}
F {}
E {}
P 4 1 -80 -140 {}
N 20 -60 20 -40 {lab=out}
N 20 -10 100 -10 {lab=vss}
N 20 20 20 70 {lab=vss}
N 20 70 100 70 {lab=vss}
N 20 -180 20 -130 {lab=vdd}
N -100 -180 20 -180 {lab=vdd}
N -80 70 20 70 {lab=vss}
N 100 -10 100 70 {lab=vss}
N 20 -60 160 -60 {lab=out}
N 20 -70 20 -60 {lab=out}
N -90 -10 -20 -10 {lab=in}
C {sky130_fd_pr/res_high_po_0p35.sym} 20 -100 0 0 {name=R1
L=8.67
model=res_high_po_0p35
spiceprefix=X
mult=1
}
C {iopin.sym} -100 -180 0 1 {name=p1 lab=vdd}
C {iopin.sym} -80 70 0 1 {name=p2 lab=vss}
C {ipin.sym} -90 -10 0 0 {name=p3 lab=in
}
C {opin.sym} 160 -60 0 0 {name=p4 lab=out
}
C {lab_pin.sym} -50 -10 0 0 {name=p5 sig_type=std_logic lab=in}
C {lab_pin.sym} 130 -60 0 0 {name=p6 sig_type=std_logic lab=out}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 0 -10 0 0  {name=M1
W=0.865
L=0.235
nf=1
mult=1
model=nfet_01v8_lvt
spiceprefix=X
format="@spiceprefix@name @pinlist sky130_fd_pr__@model L=@L W=@W nf=@nf
+ ad='int(( @nf + 1 ) / 2 ) * @W / @nf * 0.29' as='int(( @nf + 2 ) / 2 ) * @W / @nf * 0.29'
+ pd='2 * int(( @nf + 1 ) / 2 ) * ( @W / @nf + 0.29 )' ps='2 * int(( @nf + 2 ) / 2 ) * ( @W / @nf + 0.29 )'
+ nrd='0.29 / @W ' nrs='0.29 / @W ' sa=0 sb=0 sd=0 mult=@mult m=@mult" 
}

N 0 -100 -40 -100 {lab=vss}
C {lab_pin.sym} -40 -100 0 0 {name=pbulk lab=vss}
