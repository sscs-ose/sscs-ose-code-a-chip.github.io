v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 50 -210 50 -190 {
lab=AVSS}
N 130 -210 130 -190 {
lab=AVDD}
N 130 -130 130 -110 {
lab=AVSS}
N 260 -210 260 -190 {
lab=AVDD}
N 260 -130 260 -110 {
lab=IBIAS1_10U}
N 350 -210 350 -190 {
lab=AVDD}
N 350 -130 350 -110 {
lab=IBIAS2_10U}
N 430 -210 430 -190 {
lab=IPCM}
N 430 -130 430 -110 {
lab=AVSS}
N 530 -210 530 -190 {
lab=VIN}
N 530 -130 530 -110 {
lab=IPCM}
N 150 -470 150 -450 {
lab=AVDD}
N 170 -470 170 -440 {
lab=IBIAS1_10U}
N 190 -450 190 -430 {
lab=IBIAS2_10U}
N 150 -330 150 -310 {
lab=AVSS}
N 60 -370 80 -370 {
lab=VOUT}
N 60 -410 80 -410 {
lab=VIN}
N 260 -390 280 -390 {
lab=VOUT}
N 320 -330 320 -310 {
lab=AVSS}
N 60 -370 60 -280 {
lab=VOUT}
N 60 -280 280 -280 {
lab=VOUT}
N 280 -390 280 -280 {
lab=VOUT}
N 280 -390 320 -390 {
lab=VOUT}
C {devices/vsource.sym} 50 -160 0 0 {name=V0 value=0 savecurrent=false}
C {devices/gnd.sym} 50 -130 0 0 {name=l3 lab=GND}
C {devices/lab_wire.sym} 50 -210 0 0 {name=p7 sig_type=std_logic lab=AVSS
}
C {devices/vsource.sym} 130 -160 0 0 {name=V1 value="dc CACE\{AVDD\} ac 1" savecurrent=false}
C {devices/lab_wire.sym} 130 -210 0 0 {name=p1 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 130 -110 2 1 {name=p2 sig_type=std_logic lab=AVSS
}
C {devices/isource.sym} 260 -160 0 0 {name=I1 value=CACE\{IB\}}
C {devices/lab_wire.sym} 260 -210 0 0 {name=p3 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 260 -110 2 1 {name=p4 sig_type=std_logic lab=IBIAS1_10U
}
C {devices/lab_wire.sym} 350 -210 0 0 {name=p5 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 350 -110 2 1 {name=p6 sig_type=std_logic lab=IBIAS2_10U
}
C {devices/vsource.sym} 430 -160 0 0 {name=V2 value=CACE\{IPCM\} savecurrent=false}
C {devices/lab_wire.sym} 430 -210 0 0 {name=p10 sig_type=std_logic lab=IPCM
}
C {devices/lab_wire.sym} 430 -110 2 1 {name=p11 sig_type=std_logic lab=AVSS
}
C {devices/vsource.sym} 530 -160 0 0 {name=V3 value=0 savecurrent=false}
C {devices/lab_wire.sym} 530 -210 0 0 {name=p14 sig_type=std_logic lab=VIN
}
C {devices/lab_wire.sym} 530 -110 2 1 {name=p15 sig_type=std_logic lab=IPCM
}
C {devices/lab_wire.sym} 150 -470 0 0 {name=p17 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 170 -470 0 1 {name=p18 sig_type=std_logic lab=IBIAS1_10U
}
C {devices/lab_wire.sym} 190 -450 0 1 {name=p19 sig_type=std_logic lab=IBIAS2_10U
}
C {devices/lab_wire.sym} 60 -410 0 0 {name=p20 sig_type=std_logic lab=VIN
}
C {devices/lab_wire.sym} 320 -390 0 1 {name=p22 sig_type=std_logic lab=VOUT
}
C {devices/lab_wire.sym} 150 -310 2 1 {name=p23 sig_type=std_logic lab=AVSS
}
C {sky130_fd_pr/corner.sym} 400 -480 0 0 {name=CORNER only_toplevel=false corner=CACE\{corner\}}
C {devices/code_shown.sym} 600 -440 0 0 {name=CONTROL only_toplevel=false value=".control
ac dec 20 1 1e12
let out_db = db(abs(v(VOUT)))
meas ac PSRR_DC find out_db at=1
echo $&PSRR_DC > CACE\{simpath\}/CACE\{filename\}_CACE\{N\}.data
quit

.endc"
}
C {devices/capa.sym} 320 -360 0 0 {name=C1
m=1
value=CACE\{C_LOAD\}
footprint=1206
device="ceramic capacitor"}
C {devices/lab_wire.sym} 320 -310 2 0 {name=p24 sig_type=std_logic lab=AVSS
}
C {devices/title.sym} 160 -40 0 0 {name=l1 author="Analog Vibes"}
C {/home/sscspico/test_tools/analog_vibes/xschem/ota.sym} 140 -390 0 0 {name=x1}
C {devices/code_shown.sym} 600 -520 0 0 {name=SETUP only_toplevel=false value=".temp CACE\{temperature\}"
}
C {devices/isource.sym} 350 -160 0 0 {name=I2 value=CACE\{IB\}}
