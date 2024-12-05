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
N 290 -310 290 -290 {
lab=AVSS}
N 260 -390 290 -390 {
lab=VOUT}
N 290 -390 290 -370 {
lab=VOUT}
N 490 -180 540 -180 {
lab=DIFFIN}
N 490 -140 540 -140 {
lab=AVSS}
N 450 -130 450 -120 {
lab=IPCM}
N 450 -110 580 -110 {
lab=IPCM}
N 580 -130 580 -120 {
lab=IPCM}
N 450 -210 450 -190 {
lab=INP}
N 580 -210 580 -190 {
lab=INM}
N 450 -120 450 -110 {
lab=IPCM}
N 580 -120 580 -110 {
lab=IPCM}
N 660 -210 660 -190 {
lab=IPCM}
N 660 -130 660 -110 {
lab=AVSS}
N 740 -210 740 -190 {
lab=DIFFIN}
N 740 -130 740 -110 {
lab=AVSS}
C {devices/vsource.sym} 50 -160 0 0 {name=V0 value=0 savecurrent=false}
C {devices/gnd.sym} 50 -130 0 0 {name=l3 lab=GND}
C {devices/lab_wire.sym} 50 -210 0 0 {name=p7 sig_type=std_logic lab=AVSS
}
C {devices/vsource.sym} 130 -160 0 0 {name=V1 value=1.9 savecurrent=false}
C {devices/lab_wire.sym} 130 -210 0 0 {name=p1 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 130 -110 2 1 {name=p2 sig_type=std_logic lab=AVSS
}
C {devices/isource.sym} 260 -160 0 0 {name=I1 value=9.999999999999999e-06}
C {devices/lab_wire.sym} 260 -210 0 0 {name=p3 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 260 -110 2 1 {name=p4 sig_type=std_logic lab=IBIAS1_10U
}
C {devices/lab_wire.sym} 350 -210 0 0 {name=p5 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 350 -110 2 1 {name=p6 sig_type=std_logic lab=IBIAS2_10U
}
C {devices/lab_wire.sym} 150 -470 0 0 {name=p17 sig_type=std_logic lab=AVDD
}
C {devices/lab_wire.sym} 170 -470 0 1 {name=p18 sig_type=std_logic lab=IBIAS1_10U
}
C {devices/lab_wire.sym} 190 -450 0 1 {name=p19 sig_type=std_logic lab=IBIAS2_10U
}
C {devices/lab_wire.sym} 290 -370 0 1 {name=p22 sig_type=std_logic lab=VOUT
}
C {devices/lab_wire.sym} 150 -310 2 1 {name=p23 sig_type=std_logic lab=AVSS
}
C {sky130_fd_pr/corner.sym} 400 -480 0 0 {name=CORNER only_toplevel=false corner=ff}
C {devices/code_shown.sym} 600 -440 0 0 {name=CONTROL only_toplevel=false value=".control
tran 10n 150u
let rise_slew = maximum(deriv(v(VOUT)))
let fall_slew = minimum(deriv(v(VOUT)))*-1
echo $&rise_slew $&fall_slew > /home/sscspico/test_tools/coc_analog_vibes/ISSCC25/submitted_notebooks/analog_vibes/sim_sch/runs/RUN_2024-12-01_15-04-14/parameters/slew_params/run_23/tb_slew_23.data
quit
.endc"
}
C {devices/capa.sym} 290 -340 0 0 {name=C1
m=1
value=8e-11
footprint=1206
device="ceramic capacitor"}
C {devices/lab_wire.sym} 290 -290 2 0 {name=p24 sig_type=std_logic lab=AVSS
}
C {devices/title.sym} 160 -40 0 0 {name=l1 author="Analog Vibes"}
C {devices/code_shown.sym} 600 -520 0 0 {name=SETUP only_toplevel=false value=".temp 27"}
C {devices/vcvs.sym} 450 -160 0 1 {name=E1 value=0.5}
C {devices/vcvs.sym} 580 -160 0 0 {name=E3 value=-0.5}
C {devices/lab_wire.sym} 450 -210 0 0 {name=p8 sig_type=std_logic lab=INP
}
C {devices/lab_wire.sym} 580 -210 0 0 {name=p9 sig_type=std_logic lab=INM
}
C {devices/vsource.sym} 660 -160 0 0 {name=V4 value=0.9 savecurrent=false}
C {devices/lab_wire.sym} 660 -210 0 0 {name=p12 sig_type=std_logic lab=IPCM
}
C {devices/lab_wire.sym} 660 -110 2 1 {name=p13 sig_type=std_logic lab=AVSS
}
C {devices/lab_wire.sym} 530 -140 0 0 {name=p16 sig_type=std_logic lab=AVSS
}
C {devices/lab_wire.sym} 530 -180 0 0 {name=p21 sig_type=std_logic lab=DIFFIN
}
C {devices/vsource.sym} 740 -160 0 0 {name=V5 value="pulse(-1.8 1.8 50us 100ns 100ns 50us 100us)" savecurrent=false}
C {devices/lab_wire.sym} 740 -210 0 0 {name=p25 sig_type=std_logic lab=DIFFIN
}
C {devices/lab_wire.sym} 740 -110 2 1 {name=p26 sig_type=std_logic lab=AVSS
}
C {devices/lab_wire.sym} 530 -110 0 0 {name=p27 sig_type=std_logic lab=IPCM
}
C {devices/lab_wire.sym} 60 -410 0 0 {name=p10 sig_type=std_logic lab=INP
}
C {devices/lab_wire.sym} 60 -370 0 0 {name=p11 sig_type=std_logic lab=INM
}
C {devices/isource.sym} 350 -160 0 0 {name=I2 value=9.999999999999999e-06}
C {/home/sscspico/test_tools/coc_analog_vibes/ISSCC25/submitted_notebooks/analog_vibes/sim_sch/xschem/ota.sym} 140 -390 0 0 {name=x1}
