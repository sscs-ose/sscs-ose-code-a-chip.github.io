v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 340 -300 340 -290 {lab=CLK}
N 380 -300 380 -290 {lab=_CLK}
N 640 -300 640 -290 {lab=CLK}
N 680 -300 680 -290 {lab=_CLK}
N 930 -300 930 -290 {lab=CLK}
N 970 -300 970 -290 {lab=_CLK}
N 10 -110 940 -110 {lab=VDD}
N 940 -160 940 -110 {lab=VDD}
N 940 -170 940 -160 {lab=VDD}
N 650 -170 650 -110 {lab=VDD}
N 350 -170 350 -110 {lab=VDD}
N 50 -170 50 -110 {lab=VDD}
N 10 -80 970 -80 {lab=VSS}
N 970 -170 970 -80 {lab=VSS}
N 680 -170 680 -80 {lab=VSS}
N 380 -170 380 -80 {lab=VSS}
N 80 -170 80 -80 {lab=VSS}
C {switch_A.sym} 260 -170 0 0 {name=x1}
C {switch_A.sym} 560 -170 0 0 {name=x2}
C {switch_A.sym} 850 -170 0 0 {name=x3}
C {switch_A.sym} -40 -170 0 0 {name=x4}
C {ipin.sym} 0 -240 0 0 {name=p1 lab=Vin1p
}
C {ipin.sym} 300 -240 0 0 {name=p2 lab=Vin2p
}
C {opin.sym} 130 -240 0 0 {name=p5 lab=Vout1p
}
C {opin.sym} 430 -240 0 0 {name=p6 lab=Vout2p

}
C {ipin.sym} 890 -220 0 0 {name=p3 lab=Vin4n
}
C {opin.sym} 1020 -220 0 0 {name=p4 lab=Vout4n

}
C {ipin.sym} 890 -240 0 0 {name=p7 lab=Vin2n
}
C {opin.sym} 1020 -240 0 0 {name=p8 lab=Vout2n

}
C {ipin.sym} 600 -220 0 0 {name=p9 lab=Vin3n
}
C {opin.sym} 730 -220 0 0 {name=p10 lab=Vout3n

}
C {ipin.sym} 600 -240 0 0 {name=p11 lab=Vin1n
}
C {opin.sym} 730 -240 0 0 {name=p12 lab=Vout1n

}
C {ipin.sym} 300 -220 0 0 {name=p13 lab=Vin4p
}
C {opin.sym} 430 -220 0 0 {name=p14 lab=Vout4p

}
C {ipin.sym} 0 -220 0 0 {name=p15 lab=Vin3p
}
C {opin.sym} 130 -220 0 0 {name=p16 lab=Vout3p

}
C {ipin.sym} 40 -290 1 0 {name=p17 lab=CLK}
C {ipin.sym} 80 -290 1 0 {name=p18 lab=_CLK
}
C {lab_wire.sym} 340 -300 0 0 {name=p19 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 380 -300 0 0 {name=p20 sig_type=std_logic lab=_CLK}
C {lab_wire.sym} 640 -300 0 0 {name=p21 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 680 -300 0 0 {name=p22 sig_type=std_logic lab=_CLK}
C {lab_wire.sym} 930 -300 0 0 {name=p23 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 970 -300 0 0 {name=p24 sig_type=std_logic lab=_CLK}
C {ipin.sym} 10 -110 0 0 {name=p25 lab=VDD
}
C {ipin.sym} 10 -80 0 0 {name=p26 lab=VSS}
