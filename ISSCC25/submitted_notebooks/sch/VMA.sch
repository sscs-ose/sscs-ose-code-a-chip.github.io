v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 370 590 510 590 {
lab=GND}
N 510 590 620 590 {
lab=GND}
N 620 590 770 590 {
lab=GND}
N 770 590 830 590 {
lab=GND}
N 830 590 970 590 {
lab=GND}
N 370 490 370 530 {
lab=#net1}
N 410 460 410 560 {
lab=#net2}
N 970 490 970 530 {
lab=#net3}
N 930 460 930 560 {
lab=#net4}
N 830 460 930 460 {
lab=#net4}
N 770 530 830 530 {
lab=#net5}
N 800 490 800 530 {
lab=#net5}
N 530 530 620 530 {
lab=#net6}
N 410 460 540 460 {
lab=#net2}
N 580 490 580 530 {
lab=#net6}
N 970 370 970 430 {
lab=#net7}
N 840 340 930 340 {
lab=#net8}
N 800 370 800 430 {
lab=#net4}
N 410 330 540 330 {
lab=#net9}
N 370 360 370 430 {
lab=#net10}
N 580 360 580 430 {
lab=#net2}
N 510 410 510 460 {
lab=#net2}
N 510 410 580 410 {
lab=#net2}
N 880 410 880 460 {
lab=#net4}
N 800 410 880 410 {
lab=#net4}
N 800 240 800 310 {
lab=#net8}
N 580 240 580 300 {
lab=#net9}
N 490 280 490 330 {
lab=#net9}
N 490 280 580 280 {
lab=#net9}
N 890 290 890 340 {
lab=#net8}
N 800 290 890 290 {
lab=#net8}
N 710 560 730 560 {
lab=#net2}
N 620 410 710 560 {
lab=#net2}
N 580 410 620 410 {
lab=#net2}
N 660 560 670 560 {
lab=#net4}
N 670 560 760 410 {
lab=#net4}
N 760 410 800 410 {
lab=#net4}
N 370 100 370 300 {
lab=#net11}
N 970 90 970 310 {
lab=VOUT}
N 410 70 930 70 {
lab=#net11}
N 410 -30 930 -30 {
lab=#net12}
N 370 -0 370 50 {
lab=#net12}
N 970 -0 970 40 {
lab=#net13}
N 370 -60 970 -60 {
lab=VDD}
N 370 20 430 20 {
lab=#net12}
N 430 -30 430 20 {
lab=#net12}
N 370 150 430 150 {
lab=#net11}
N 430 70 430 150 {
lab=#net11}
N 580 180 580 185 {
lab=IBIAS}
N 580 180 805 180 {
lab=IBIAS}
N 490 460 490 560 {
lab=#net2}
N 870 460 870 560 {
lab=#net4}
C {ipin.sym} 840 210 0 1 {name=p1 lab=VIN+}
C {ipin.sym} 540 210 0 0 {name=p2 lab=VIN-}
C {opin.sym} 970 200 0 0 {name=p3 lab=VOUT
}
C {pmos3.sym} 950 -30 0 0 {name=X2 model=irf5305}
C {pmos3.sym} 950 70 0 0 {name=X4 model=irf5305}
C {pmos3.sym} 390 -30 0 1 {name=X6 model=irf5305 w=1u l = 1u
}
C {pmos3.sym} 390 70 0 1 {name=X8 model=irf5305}
C {pmos3.sym} 820 210 0 1 {name=X9 model=irf5305}
C {pmos3.sym} 560 210 0 0 {name=X10 model=irf5305}
C {nmos3.sym} 950 340 0 0 {name=X11 model=irf540 m=1}
C {nmos3.sym} 560 330 0 0 {name=X12 model=irf540 m=1}
C {nmos3.sym} 820 340 0 1 {name=X13 model=irf540 m=1}
C {nmos3.sym} 390 330 0 1 {name=X14 model=irf540 m=1}
C {nmos3.sym} 390 460 0 1 {name=X15 model=irf540 m=1}
C {nmos3.sym} 390 560 0 1 {name=X16 model=irf540 m=1}
C {nmos3.sym} 560 460 0 0 {name=X17 model=irf540 m=1}
C {nmos3.sym} 510 560 0 0 {name=X18 model=irf540 m=1}
C {nmos3.sym} 640 560 0 1 {name=X19 model=irf540 m=1}
C {nmos3.sym} 750 560 0 0 {name=X20 model=irf540 m=1}
C {nmos3.sym} 850 560 0 1 {name=X21 model=irf540 m=1}
C {nmos3.sym} 820 460 0 1 {name=X22 model=irf540 m=1}
C {nmos3.sym} 950 560 0 0 {name=X23 model=irf540 m=1}
C {nmos3.sym} 950 460 0 0 {name=X24 model=irf540 m=1}
C {vdd.sym} 650 -60 0 0 {name=l1 lab=VDD}
C {gnd.sym} 690 590 0 0 {name=l2 lab=GND}
C {opin.sym} 690 180 1 1 {name=p4 lab=IBIAS

}
