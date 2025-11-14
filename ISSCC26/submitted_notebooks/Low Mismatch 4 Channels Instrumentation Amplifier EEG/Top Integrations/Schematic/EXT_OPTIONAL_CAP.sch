v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {EXTERNAL CAP} -180 -430 0 0 0.4 0.4 {}
N -60 -170 -20 -170 {lab=OUTCH4PFIN}
N -60 -60 -20 -60 {lab=OUTCH4NFIN}
N 40 -170 100 -170 {lab=OUTCH4P
}
N 50 -60 100 -60 {lab=OUTCH4N}
N 40 -60 50 -60 {lab=OUTCH4N}
N 80 -170 80 -150 {lab=OUTCH4P}
N 80 -90 80 -60 {lab=OUTCH4N}
N -60 -340 -20 -340 {lab=OUTCH3PFIN}
N -60 -230 -20 -230 {lab=OUTCH3NFIN}
N 40 -340 100 -340 {lab=OUTCH3P
}
N 50 -230 100 -230 {lab=OUTCH3N}
N 40 -230 50 -230 {lab=OUTCH3N}
N 80 -340 80 -320 {lab=OUTCH3P}
N 80 -260 80 -230 {lab=OUTCH3N}
N -370 -170 -330 -170 {lab=OUTCH2PFIN}
N -370 -60 -330 -60 {lab=OUTCH2NFIN}
N -270 -170 -210 -170 {lab=OUTCH2P
}
N -260 -60 -210 -60 {lab=OUTCH2N}
N -270 -60 -260 -60 {lab=OUTCH2N}
N -230 -170 -230 -150 {lab=OUTCH2P}
N -230 -90 -230 -60 {lab=OUTCH2N}
N -370 -340 -330 -340 {lab=OUTCH1PFIN}
N -370 -230 -330 -230 {lab=OUTCH1NFIN}
N -270 -340 -210 -340 {lab=OUTCH1P
}
N -260 -230 -210 -230 {lab=OUTCH1N}
N -270 -230 -260 -230 {lab=OUTCH1N}
N -230 -340 -230 -320 {lab=OUTCH1P}
N -230 -260 -230 -230 {lab=OUTCH1N}
C {ind.sym} 10 -170 1 0 {name=L1
m=1
value=20n
footprint=1206
device=inductor}
C {ind.sym} 10 -60 1 0 {name=L3
m=1
value=20n
footprint=1206
device=inductor}
C {lab_pin.sym} -50 -170 2 0 {name=p86 sig_type=std_logic lab=OUTCH4PFIN}
C {lab_pin.sym} -50 -60 2 0 {name=p87 sig_type=std_logic lab=OUTCH4NFIN}
C {capa.sym} 80 -120 0 0 {name=C1
m=1
value=20p
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} 90 -170 2 0 {name=p88 sig_type=std_logic lab=OUTCH4P}
C {lab_pin.sym} 90 -60 2 0 {name=p89 sig_type=std_logic lab=OUTCH4N}
C {ind.sym} -300 -60 1 0 {name=L9
m=1
value=20n
footprint=1206
device=inductor}
C {ind.sym} 10 -230 1 0 {name=L11
m=1
value=20n
footprint=1206
device=inductor}
C {lab_pin.sym} -50 -340 2 0 {name=p94 sig_type=std_logic lab=OUTCH3PFIN}
C {lab_pin.sym} -50 -230 2 0 {name=p95 sig_type=std_logic lab=OUTCH3NFIN}
C {capa.sym} 80 -290 0 0 {name=C2
m=1
value=20p
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} 90 -340 2 0 {name=p96 sig_type=std_logic lab=OUTCH3P}
C {lab_pin.sym} 90 -230 2 0 {name=p97 sig_type=std_logic lab=OUTCH3N}
C {ind.sym} -300 -170 1 0 {name=L105
m=1
value=20n
footprint=1206
device=inductor}
C {lab_pin.sym} -360 -170 2 0 {name=p98 sig_type=std_logic lab=OUTCH2PFIN
}
C {lab_pin.sym} -360 -60 2 0 {name=p99 sig_type=std_logic lab=OUTCH2NFIN}
C {capa.sym} -230 -120 0 0 {name=C3
m=1
value=20p
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} -220 -170 2 0 {name=p100 sig_type=std_logic lab=OUTCH2P}
C {lab_pin.sym} -220 -60 2 0 {name=p101 sig_type=std_logic lab=OUTCH2N}
C {ind.sym} 10 -340 1 0 {name=L106
m=1
value=20n
footprint=1206
device=inductor}
C {ind.sym} -300 -230 1 0 {name=L107
m=1
value=20n
footprint=1206
device=inductor}
C {ind.sym} -300 -340 1 0 {name=L108
m=1
value=20n
footprint=1206
device=inductor}
C {lab_pin.sym} -360 -340 2 0 {name=p102 sig_type=std_logic lab=OUTCH1PFIN
}
C {lab_pin.sym} -360 -230 2 0 {name=p103 sig_type=std_logic lab=OUTCH1NFIN}
C {capa.sym} -230 -290 0 0 {name=C4
m=1
value=20p
footprint=1206
device="ceramic capacitor"}
C {lab_pin.sym} -220 -340 2 0 {name=p104 sig_type=std_logic lab=OUTCH1P}
C {lab_pin.sym} -220 -230 2 0 {name=p105 sig_type=std_logic lab=OUTCH1N}
