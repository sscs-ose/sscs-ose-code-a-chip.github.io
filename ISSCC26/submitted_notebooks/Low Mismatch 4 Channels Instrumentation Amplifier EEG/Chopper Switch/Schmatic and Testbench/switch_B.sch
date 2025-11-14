v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
P 4 1 130 140 {}
N 60 -50 90 -50 {lab=Vin1p}
N 60 -30 90 -30 {lab=Vin2p}
N 220 -50 250 -50 {lab=Vout2p}
N 220 -30 250 -30 {lab=Vout1p}
N 60 180 90 180 {lab=Vin1n}
N 60 200 90 200 {lab=Vin2n}
N 220 180 250 180 {lab=Vout2n}
N 220 200 250 200 {lab=Vout1n}
N 130 120 130 130 {lab=CLK}
N 170 120 170 130 {lab=_CLK}
N 140 20 140 40 {lab=VDD}
N 170 20 170 40 {lab=VSS}
N -50 30 140 30 {lab=VDD}
N -50 30 -50 260 {lab=VDD}
N -50 260 140 260 {lab=VDD}
N 140 250 140 260 {lab=VDD}
N 170 30 370 30 {lab=VSS}
N 370 60 370 250 {lab=VSS}
N 370 30 370 60 {lab=VSS}
N 370 250 370 260 {lab=VSS}
N 170 260 370 260 {lab=VSS}
N 170 250 170 260 {lab=VSS}
C {switch_A.sym} 50 20 0 0 {name=x1}
C {switch_A.sym} 50 250 0 0 {name=x2}
C {ipin.sym} 60 -50 0 0 {name=p1 lab=Vin1p
}
C {ipin.sym} 60 -30 0 0 {name=p2 lab=Vin2p
}
C {ipin.sym} 60 180 0 0 {name=p3 lab=Vin1n
}
C {ipin.sym} 60 200 0 0 {name=p4 lab=Vin2n
}
C {opin.sym} 250 -30 0 0 {name=p5 lab=Vout1p
}
C {opin.sym} 250 -50 0 0 {name=p6 lab=Vout2p

}
C {opin.sym} 250 200 0 0 {name=p7 lab=Vout1n}
C {opin.sym} 250 180 0 0 {name=p8 lab=Vout2n

}
C {ipin.sym} 130 -100 1 0 {name=p9 lab=CLK}
C {ipin.sym} 170 -100 1 0 {name=p10 lab=_CLK
}
C {lab_wire.sym} 130 120 0 0 {name=p11 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 170 120 0 0 {name=p12 sig_type=std_logic lab=_CLK}
C {ipin.sym} 140 40 3 0 {name=p13 lab=VDD}
C {ipin.sym} 170 40 3 0 {name=p14 lab=VSS}
