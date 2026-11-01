v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Capacitor-less LDO + ZTC hysteretic POR (SKY130, all g5v0d10v5) - generated from the notebook parameters} 0 -260 0 0 0.5 0.5 {}
T {Connections by net labels. Iref and VREF are ideal (see notebook).} 0 -220 0 0 0.35 0.35 {}
C {iopin.sym} 3300 -150 0 0 {name=p4 lab=VIN}
C {iopin.sym} 3300 -110 0 0 {name=p5 lab=GND}
C {ipin.sym} 3300 -70 0 0 {name=p6 lab=VREF}
C {opin.sym} 3300 -30 0 0 {name=p7 lab=VOUT}
C {opin.sym} 3300 10 0 0 {name=p8 lab=RST_N}
T {LDO} 0 -150 0 0 0.5 0.5 {}
C {isource.sym} 140 0 0 0 {name=Iref value=2.5e-07}
C {lab_pin.sym} 140 -30 0 1 {name=l11 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 140 30 0 1 {name=l12 sig_type=std_logic lab=nb}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 140 240 0 0 {name=MNB W=2 L=4 nf=1 mult=1 ad=0.58 as=0.58 pd=4.58 ps=4.58 nrd=0.145 nrs=0.145 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 160 210 0 1 {name=l14 sig_type=std_logic lab=nb}
C {lab_pin.sym} 120 240 0 0 {name=l15 sig_type=std_logic lab=nb}
C {lab_pin.sym} 160 270 0 1 {name=l16 sig_type=std_logic lab=GND}
C {lab_pin.sym} 160 240 0 1 {name=l17 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 590 500 0 0 {name=MN5 W=2 L=4 nf=1 mult=4 ad=0.58 as=0.58 pd=4.58 ps=4.58 nrd=0.145 nrs=0.145 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 610 470 0 1 {name=l19 sig_type=std_logic lab=tail}
C {lab_pin.sym} 570 500 0 0 {name=l20 sig_type=std_logic lab=nb}
C {lab_pin.sym} 610 530 0 1 {name=l21 sig_type=std_logic lab=GND}
C {lab_pin.sym} 610 500 0 1 {name=l22 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 450 240 0 0 {name=MN1 W=8 L=2 nf=1 mult=1 ad=2.32 as=2.32 pd=16.58 ps=16.58 nrd=0.03625 nrs=0.03625 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 470 210 0 1 {name=l24 sig_type=std_logic lab=n1}
C {lab_pin.sym} 430 240 0 0 {name=l25 sig_type=std_logic lab=VOUT}
C {lab_pin.sym} 470 270 0 1 {name=l26 sig_type=std_logic lab=tail}
C {lab_pin.sym} 470 240 0 1 {name=l27 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 810 240 0 0 {name=MN2 W=8 L=2 nf=1 mult=1 ad=2.32 as=2.32 pd=16.58 ps=16.58 nrd=0.03625 nrs=0.03625 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 830 210 0 1 {name=l29 sig_type=std_logic lab=vg}
C {lab_pin.sym} 790 240 0 0 {name=l30 sig_type=std_logic lab=VREF}
C {lab_pin.sym} 830 270 0 1 {name=l31 sig_type=std_logic lab=tail}
C {lab_pin.sym} 830 240 0 1 {name=l32 sig_type=std_logic lab=GND}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 450 0 0 0 {name=MP3 W=16 L=4 nf=1 mult=1 ad=4.64 as=4.64 pd=32.58 ps=32.58 nrd=0.01812 nrs=0.01812 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 470 30 0 1 {name=l34 sig_type=std_logic lab=n1}
C {lab_pin.sym} 430 0 0 0 {name=l35 sig_type=std_logic lab=n1}
C {lab_pin.sym} 470 -30 0 1 {name=l36 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 470 0 0 1 {name=l37 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 810 0 0 0 {name=MP4 W=16 L=4 nf=1 mult=1 ad=4.64 as=4.64 pd=32.58 ps=32.58 nrd=0.01812 nrs=0.01812 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 830 30 0 1 {name=l39 sig_type=std_logic lab=vg}
C {lab_pin.sym} 790 0 0 0 {name=l40 sig_type=std_logic lab=n1}
C {lab_pin.sym} 830 -30 0 1 {name=l41 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 830 0 0 1 {name=l42 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1440 0 0 0 {name=MPP W=400 L=0.5 nf=40 mult=1 ad=58 as=60.9 pd=411.6 ps=432.2 nrd=0.000725 nrs=0.000725 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1460 30 0 1 {name=l44 sig_type=std_logic lab=VOUT}
C {lab_pin.sym} 1420 0 0 0 {name=l45 sig_type=std_logic lab=vg}
C {lab_pin.sym} 1460 -30 0 1 {name=l46 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 1460 0 0 1 {name=l47 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1170 0 0 0 {name=MPS W=0.84 L=0.5 nf=1 mult=1 ad=0.2436 as=0.2436 pd=2.26 ps=2.26 nrd=0.3452 nrs=0.3452 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1190 30 0 1 {name=l49 sig_type=std_logic lab=na}
C {lab_pin.sym} 1150 0 0 0 {name=l50 sig_type=std_logic lab=vg}
C {lab_pin.sym} 1190 -30 0 1 {name=l51 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 1190 0 0 1 {name=l52 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1170 240 0 0 {name=MNA W=1 L=4 nf=1 mult=1 ad=0.29 as=0.29 pd=2.58 ps=2.58 nrd=0.29 nrs=0.29 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1190 210 0 1 {name=l54 sig_type=std_logic lab=na}
C {lab_pin.sym} 1150 240 0 0 {name=l55 sig_type=std_logic lab=na}
C {lab_pin.sym} 1190 270 0 1 {name=l56 sig_type=std_logic lab=GND}
C {lab_pin.sym} 1190 240 0 1 {name=l57 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 940 500 0 0 {name=MNA2 W=1 L=4 nf=1 mult=1 ad=0.29 as=0.29 pd=2.58 ps=2.58 nrd=0.29 nrs=0.29 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 960 470 0 1 {name=l59 sig_type=std_logic lab=tail}
C {lab_pin.sym} 920 500 0 0 {name=l60 sig_type=std_logic lab=na}
C {lab_pin.sym} 960 530 0 1 {name=l61 sig_type=std_logic lab=GND}
C {lab_pin.sym} 960 500 0 1 {name=l62 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1710 240 0 0 {name=MNBL W=2 L=4 nf=1 mult=20 ad=0.58 as=0.58 pd=4.58 ps=4.58 nrd=0.145 nrs=0.145 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1730 210 0 1 {name=l64 sig_type=std_logic lab=VOUT}
C {lab_pin.sym} 1690 240 0 0 {name=l65 sig_type=std_logic lab=nb}
C {lab_pin.sym} 1730 270 0 1 {name=l66 sig_type=std_logic lab=GND}
C {lab_pin.sym} 1730 240 0 1 {name=l67 sig_type=std_logic lab=GND}
C {sky130_fd_pr/cap_mim_m3_1.sym} 1480 260 0 0 {name=Cc model=cap_mim_m3_1 W=30 L=30 MF=1 spiceprefix=X}
C {lab_pin.sym} 1480 230 0 1 {name=l69 sig_type=std_logic lab=vg}
C {lab_pin.sym} 1480 290 0 1 {name=l70 sig_type=std_logic lab=VOUT}
T {class-AB current-buffer coupling (v2)} 1980.0 -150 0 0 0.4 0.4 {}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1980 0 0 0 {name=MPB2 W=4 L=4 nf=1 mult=1 ad=1.16 as=1.16 pd=8.58 ps=8.58 nrd=0.0725 nrs=0.0725 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 2000 30 0 1 {name=l73 sig_type=std_logic lab=pa}
C {lab_pin.sym} 1960 0 0 0 {name=l74 sig_type=std_logic lab=pa}
C {lab_pin.sym} 2000 -30 0 1 {name=l75 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 2000 0 0 1 {name=l76 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 1980 240 0 0 {name=Rsh L=205.9 model=res_xhigh_po_0p35 spiceprefix=X mult=1}
C {lab_pin.sym} 1980 210 0 1 {name=l78 sig_type=std_logic lab=pa}
C {lab_pin.sym} 1980 270 0 1 {name=l79 sig_type=std_logic lab=vbp}
C {lab_pin.sym} 1960 240 0 0 {name=l80 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1980 500 0 0 {name=MNB3 W=2 L=4 nf=1 mult=1 ad=0.58 as=0.58 pd=4.58 ps=4.58 nrd=0.145 nrs=0.145 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 2000 470 0 1 {name=l82 sig_type=std_logic lab=vbp}
C {lab_pin.sym} 1960 500 0 0 {name=l83 sig_type=std_logic lab=nb}
C {lab_pin.sym} 2000 530 0 1 {name=l84 sig_type=std_logic lab=GND}
C {lab_pin.sym} 2000 500 0 1 {name=l85 sig_type=std_logic lab=GND}
C {sky130_fd_pr/cap_mim_m3_1.sym} 2200 500 0 0 {name=Cbp model=cap_mim_m3_1 W=22 L=22 MF=1 spiceprefix=X}
C {lab_pin.sym} 2200 470 0 1 {name=l87 sig_type=std_logic lab=vbp}
C {lab_pin.sym} 2200 530 0 1 {name=l88 sig_type=std_logic lab=GND}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 2380 0 0 0 {name=MPT W=4 L=4 nf=1 mult=3 ad=1.16 as=1.16 pd=8.58 ps=8.58 nrd=0.0725 nrs=0.0725 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 2400 30 0 1 {name=l90 sig_type=std_logic lab=tx}
C {lab_pin.sym} 2360 0 0 0 {name=l91 sig_type=std_logic lab=pa}
C {lab_pin.sym} 2400 -30 0 1 {name=l92 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 2400 0 0 1 {name=l93 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 2380 240 0 0 {name=MPX W=4 L=4 nf=1 mult=3 ad=1.16 as=1.16 pd=8.58 ps=8.58 nrd=0.0725 nrs=0.0725 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 2400 270 0 1 {name=l95 sig_type=std_logic lab=vg}
C {lab_pin.sym} 2360 240 0 0 {name=l96 sig_type=std_logic lab=vbp}
C {lab_pin.sym} 2400 210 0 1 {name=l97 sig_type=std_logic lab=tx}
C {lab_pin.sym} 2400 240 0 1 {name=l98 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 2660 240 0 0 {name=MNX W=4 L=1 nf=1 mult=3 ad=1.16 as=1.16 pd=8.58 ps=8.58 nrd=0.0725 nrs=0.0725 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 2680 210 0 1 {name=l100 sig_type=std_logic lab=vg}
C {lab_pin.sym} 2640 240 0 0 {name=l101 sig_type=std_logic lab=VREF}
C {lab_pin.sym} 2680 270 0 1 {name=l102 sig_type=std_logic lab=sx}
C {lab_pin.sym} 2680 240 0 1 {name=l103 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 2660 500 0 0 {name=MNS W=2 L=4 nf=1 mult=3 ad=0.58 as=0.58 pd=4.58 ps=4.58 nrd=0.145 nrs=0.145 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 2680 470 0 1 {name=l105 sig_type=std_logic lab=sx}
C {lab_pin.sym} 2640 500 0 0 {name=l106 sig_type=std_logic lab=nb}
C {lab_pin.sym} 2680 530 0 1 {name=l107 sig_type=std_logic lab=GND}
C {lab_pin.sym} 2680 500 0 1 {name=l108 sig_type=std_logic lab=GND}
C {sky130_fd_pr/cap_mim_m3_1.sym} 2950 0 0 0 {name=Cfp model=cap_mim_m3_1 W=55 L=55 MF=1 spiceprefix=X}
C {lab_pin.sym} 2950 -30 0 1 {name=l110 sig_type=std_logic lab=VOUT}
C {lab_pin.sym} 2950 30 0 1 {name=l111 sig_type=std_logic lab=tx}
C {sky130_fd_pr/cap_mim_m3_1.sym} 2950 240 0 0 {name=Cfn model=cap_mim_m3_1 W=55 L=55 MF=1 spiceprefix=X}
C {lab_pin.sym} 2950 210 0 1 {name=l113 sig_type=std_logic lab=VOUT}
C {lab_pin.sym} 2950 270 0 1 {name=l114 sig_type=std_logic lab=sx}
C {sky130_fd_pr/cap_mim_m3_1.sym} 2950 500 0 0 {name=Cff model=cap_mim_m3_1 W=32 L=32 MF=1 spiceprefix=X}
C {lab_pin.sym} 2950 470 0 1 {name=l116 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 2950 530 0 1 {name=l117 sig_type=std_logic lab=sx}
T {POR} 0 675.0 0 0 0.5 0.5 {}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 180 840 0 0 {name=R1 L=279.4 model=res_xhigh_po_0p35 spiceprefix=X mult=1}
C {lab_pin.sym} 180 810 0 1 {name=l120 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 180 870 0 1 {name=l121 sig_type=std_logic lab=div}
C {lab_pin.sym} 160 840 0 0 {name=l122 sig_type=std_logic lab=GND}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 180 1020 0 0 {name=R2 L=470.5 model=res_xhigh_po_0p35 spiceprefix=X mult=1}
C {lab_pin.sym} 180 990 0 1 {name=l124 sig_type=std_logic lab=div}
C {lab_pin.sym} 180 1050 0 1 {name=l125 sig_type=std_logic lab=dm}
C {lab_pin.sym} 160 1020 0 0 {name=l126 sig_type=std_logic lab=GND}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 180 1200 0 0 {name=R3 L=188.2 model=res_xhigh_po_0p35 spiceprefix=X mult=1}
C {lab_pin.sym} 180 1170 0 1 {name=l128 sig_type=std_logic lab=dm}
C {lab_pin.sym} 180 1230 0 1 {name=l129 sig_type=std_logic lab=GND}
C {lab_pin.sym} 160 1200 0 0 {name=l130 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 450 1200 0 0 {name=MH W=1 L=0.5 nf=1 mult=1 ad=0.29 as=0.29 pd=2.58 ps=2.58 nrd=0.29 nrs=0.29 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 470 1170 0 1 {name=l132 sig_type=std_logic lab=dm}
C {lab_pin.sym} 430 1200 0 0 {name=l133 sig_type=std_logic lab=pgb}
C {lab_pin.sym} 470 1230 0 1 {name=l134 sig_type=std_logic lab=GND}
C {lab_pin.sym} 470 1200 0 1 {name=l135 sig_type=std_logic lab=GND}
C {sky130_fd_pr/res_xhigh_po_0p35.sym} 760 840 0 0 {name=Rpu L=588.1 model=res_xhigh_po_0p35 spiceprefix=X mult=1}
C {lab_pin.sym} 760 810 0 1 {name=l137 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 760 870 0 1 {name=l138 sig_type=std_logic lab=x}
C {lab_pin.sym} 740 840 0 0 {name=l139 sig_type=std_logic lab=GND}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 720 1050 0 0 {name=MD W=0.7 L=20 nf=1 mult=1 ad=0.203 as=0.203 pd=1.98 ps=1.98 nrd=0.4143 nrs=0.4143 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 740 1020 0 1 {name=l141 sig_type=std_logic lab=x}
C {lab_pin.sym} 700 1050 0 0 {name=l142 sig_type=std_logic lab=div}
C {lab_pin.sym} 740 1080 0 1 {name=l143 sig_type=std_logic lab=GND}
C {lab_pin.sym} 740 1050 0 1 {name=l144 sig_type=std_logic lab=GND}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1080 840 0 0 {name=MI1P W=0.84 L=4 nf=1 mult=1 ad=0.2436 as=0.2436 pd=2.26 ps=2.26 nrd=0.3452 nrs=0.3452 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1100 870 0 1 {name=l146 sig_type=std_logic lab=pg}
C {lab_pin.sym} 1060 840 0 0 {name=l147 sig_type=std_logic lab=x}
C {lab_pin.sym} 1100 810 0 1 {name=l148 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 1100 840 0 1 {name=l149 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1080 1050 0 0 {name=MI1N W=0.42 L=4 nf=1 mult=1 ad=0.1218 as=0.1218 pd=1.42 ps=1.42 nrd=0.6905 nrs=0.6905 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1100 1020 0 1 {name=l151 sig_type=std_logic lab=pg}
C {lab_pin.sym} 1060 1050 0 0 {name=l152 sig_type=std_logic lab=x}
C {lab_pin.sym} 1100 1080 0 1 {name=l153 sig_type=std_logic lab=GND}
C {lab_pin.sym} 1100 1050 0 1 {name=l154 sig_type=std_logic lab=GND}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1440 840 0 0 {name=MI2P W=0.84 L=0.5 nf=1 mult=1 ad=0.2436 as=0.2436 pd=2.26 ps=2.26 nrd=0.3452 nrs=0.3452 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1460 870 0 1 {name=l156 sig_type=std_logic lab=pgb}
C {lab_pin.sym} 1420 840 0 0 {name=l157 sig_type=std_logic lab=pg}
C {lab_pin.sym} 1460 810 0 1 {name=l158 sig_type=std_logic lab=VIN}
C {lab_pin.sym} 1460 840 0 1 {name=l159 sig_type=std_logic lab=VIN}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1440 1050 0 0 {name=MI2N W=0.42 L=0.5 nf=1 mult=1 ad=0.1218 as=0.1218 pd=1.42 ps=1.42 nrd=0.6905 nrs=0.6905 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1460 1020 0 1 {name=l161 sig_type=std_logic lab=pgb}
C {lab_pin.sym} 1420 1050 0 0 {name=l162 sig_type=std_logic lab=pg}
C {lab_pin.sym} 1460 1080 0 1 {name=l163 sig_type=std_logic lab=GND}
C {lab_pin.sym} 1460 1050 0 1 {name=l164 sig_type=std_logic lab=GND}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1800 840 0 0 {name=MI3P W=0.84 L=0.5 nf=1 mult=1 ad=0.2436 as=0.2436 pd=2.26 ps=2.26 nrd=0.3452 nrs=0.3452 sa=0 sb=0 sd=0 model=pfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1820 870 0 1 {name=l166 sig_type=std_logic lab=RST_N}
C {lab_pin.sym} 1780 840 0 0 {name=l167 sig_type=std_logic lab=pgb}
C {lab_pin.sym} 1820 810 0 1 {name=l168 sig_type=std_logic lab=VOUT}
C {lab_pin.sym} 1820 840 0 1 {name=l169 sig_type=std_logic lab=VOUT}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1800 1050 0 0 {name=MI3N W=0.42 L=0.5 nf=1 mult=1 ad=0.1218 as=0.1218 pd=1.42 ps=1.42 nrd=0.6905 nrs=0.6905 sa=0 sb=0 sd=0 model=nfet_g5v0d10v5 spiceprefix=X}
C {lab_pin.sym} 1820 1020 0 1 {name=l171 sig_type=std_logic lab=RST_N}
C {lab_pin.sym} 1780 1050 0 0 {name=l172 sig_type=std_logic lab=pgb}
C {lab_pin.sym} 1820 1080 0 1 {name=l173 sig_type=std_logic lab=GND}
C {lab_pin.sym} 1820 1050 0 1 {name=l174 sig_type=std_logic lab=GND}
