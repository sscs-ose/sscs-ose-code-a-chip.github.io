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
N 480 -180 530 -180 {
lab=DIFFIN}
N 480 -140 530 -140 {
lab=AVSS}
N 440 -130 440 -120 {
lab=IPCM}
N 440 -110 570 -110 {
lab=IPCM}
N 570 -130 570 -120 {
lab=IPCM}
N 440 -210 440 -190 {
lab=INP}
N 570 -210 570 -190 {
lab=INM}
N 440 -120 440 -110 {
lab=IPCM}
N 570 -120 570 -110 {
lab=IPCM}
N 650 -210 650 -190 {
lab=IPCM}
N 650 -130 650 -110 {
lab=AVSS}
N 790 -210 790 -190 {
lab=DIFFIN}
N 790 -130 790 -110 {
lab=AVSS}
N 150 -470 150 -450 {
lab=AVDD}
N 170 -470 170 -440 {
lab=IBIAS1_10U}
N 190 -450 190 -430 {
lab=IBIAS2_10U}
N 150 -330 150 -310 {
lab=AVSS}
N 60 -370 80 -370 {
lab=INM}
N 60 -410 80 -410 {
lab=INP}
N 260 -390 280 -390 {
lab=VOUT}
N 280 -330 280 -310 {
lab=AVSS}
C {devices/vsource.sym} 50 -160 0 0 {name=V0 value=0 savecurrent=false}
C {devices/gnd.sym} 50 -130 0 0 {name=l3 lab=GND}
C {devices/lab_wire.sym} 50 -210 0 0 {name=p7 sig_type=std_logic lab=AVSS
}
C {devices/vsource.sym} 130 -160 0 0 {name=V1 value=CACE\{AVDD\} savecurrent=false}
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
C {devices/vcvs.sym} 440 -160 0 1 {name=E1 value=0.5}
C {devices/vcvs.sym} 570 -160 0 0 {name=E3 value=-0.5}
C {devices/lab_wire.sym} 440 -210 0 0 {name=p8 sig_type=std_logic lab=INP
}
C {devices/lab_wire.sym} 570 -210 0 0 {name=p9 sig_type=std_logic lab=INM
}
C {devices/vsource.sym} 650 -160 0 0 {name=V2 value="dc CACE\{IPCM\} ac 1" savecurrent=false}
C {devices/lab_wire.sym} 650 -210 0 0 {name=p10 sig_type=std_logic lab=IPCM
}
C {devices/lab_wire.sym} 650 -110 2 1 {name=p11 sig_type=std_logic lab=AVSS
}
C {devices/lab_wire.sym} 520 -140 0 0 {name=p12 sig_type=std_logic lab=AVSS
}
C {devices/lab_wire.sym} 520 -180 0 0 {name=p13 sig_type=std_logic lab=DIFFIN
}
C {devices/vsource.sym} 790 -160 0 0 {name=V3 value=dc 0 savecurrent=false}
C {devices/lab_wire.sym} 790 -210 0 0 {name=p14 sig_type=std_logic lab=DIFFIN
}
C {devices/lab_wire.sym} 790 -110 2 1 {name=p15 sig_type=std_logic lab=AVSS
}
C {devices/lab_wire.sym} 520 -110 0 0 {name=p16 sig_type=std_logic lab=IPCM
}
C {devices/lab_wire.sym} 150 -470 0 0 {name=p17 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 170 -470 0 1 {name=p18 sig_type=std_logic lab=IBIAS1_10U
}
C {devices/lab_wire.sym} 190 -450 0 1 {name=p19 sig_type=std_logic lab=IBIAS2_10U
}
C {devices/lab_wire.sym} 60 -410 0 0 {name=p20 sig_type=std_logic lab=INP
}
C {devices/lab_wire.sym} 60 -370 0 0 {name=p21 sig_type=std_logic lab=INM
}
C {devices/lab_wire.sym} 280 -390 0 1 {name=p22 sig_type=std_logic lab=VOUT
}
C {devices/lab_wire.sym} 150 -310 2 1 {name=p23 sig_type=std_logic lab=AVSS
}
C {sky130_fd_pr/corner.sym} 400 -480 0 0 {name=CORNER only_toplevel=false corner=CACE\{corner\}}
C {devices/code_shown.sym} 600 -440 0 0 {name=CONTROL only_toplevel=false value=".control
ac dec 20 1 1e12
let out_db = db(abs(v(VOUT)))
meas ac CMRR_DC find out_db at=1
echo $&CMRR_DC > CACE\{simpath\}/CACE\{filename\}_CACE\{N\}.data
quit

.endc"
}
C {devices/capa.sym} 280 -360 0 0 {name=C1
m=1
value=CACE\{C_LOAD\}
footprint=1206
device="ceramic capacitor"}
C {devices/lab_wire.sym} 280 -310 2 1 {name=p24 sig_type=std_logic lab=AVSS
}
C {devices/title.sym} 160 -40 0 0 {name=l1 author="Analog Vibes"}
C {/home/sscspico/test_tools/analog_vibes/xschem/ota.sym} 140 -390 0 0 {name=x1}
C {devices/code_shown.sym} 600 -520 0 0 {name=SETUP only_toplevel=false value=".temp CACE\{temperature\}"
}
C {devices/isource.sym} 350 -160 0 0 {name=I2 value=CACE\{IB\}}
