v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 540 -350 540 -290 {lab=Vout}
N 540 -160 540 -140 {lab=GND}
N 400 -450 500 -450 {lab=Vgp}
N 400 -260 500 -260 {lab=Vgn}
N 540 -420 540 -350 {lab=Vout}
N 540 -530 540 -450 {lab=VDD}
N 300 -350 300 -260 {lab=Vx}
N 300 -450 340 -450 {lab=Vx}
N 300 -260 340 -260 {lab=Vx}
N 920 -350 1000 -350 {lab=VDZP}
N 920 -430 920 -350 {lab=VDZP}
N 920 -430 960 -430 {lab=VDZP}
N 1000 -400 1000 -350 {lab=VDZP}
N 1000 -510 1000 -430 {lab=VDD}
N 1000 -290 1000 -250 {lab=GND}
N 1250 -520 1250 -490 {lab=VDD}
N 1250 -410 1250 -390 {lab=VDZN}
N 1150 -360 1210 -360 {lab=VDZN}
N 1150 -410 1150 -360 {lab=VDZN}
N 1150 -410 1250 -410 {lab=VDZN}
N 1250 -430 1250 -410 {lab=VDZN}
N 1250 -360 1250 -290 {lab=GND}
N 820 -210 820 -170 {lab=GND}
N 820 -290 820 -270 {lab=VDD}
N 910 -210 910 -170 {lab=GND}
N 910 -290 910 -270 {lab=vcm}
N 60 -160 60 -120 {lab=GND}
N 60 -260 60 -220 {lab=#net1}
N 390 -550 420 -550 {lab=VDZP}
N 390 -550 390 -490 {lab=VDZP}
N 350 -550 350 -490 {lab=vcm}
N 320 -550 350 -550 {lab=vcm}
N 390 -220 390 -170 {lab=VDZN}
N 390 -170 420 -170 {lab=VDZN}
N 350 -220 350 -170 {lab=vcm}
N 320 -170 350 -170 {lab=vcm}
N 230 -350 300 -350 {lab=Vx}
N 300 -450 300 -350 {lab=Vx}
N 230 -680 230 -350 {lab=Vx}
N 230 -680 350 -680 {lab=Vx}
N 410 -680 670 -680 {lab=Vout}
N 670 -680 670 -350 {lab=Vout}
N 540 -350 670 -350 {lab=Vout}
N 200 -350 230 -350 {lab=Vx}
N 60 -350 140 -350 {lab=Vin}
N 60 -350 60 -320 {lab=Vin}
N 750 -350 780 -350 {lab=Vout}
N 750 -210 750 -160 {lab=GND}
N 540 -160 750 -160 {lab=GND}
N 540 -260 540 -160 {lab=GND}
N 750 -350 750 -330 {lab=Vout}
N 670 -350 750 -350 {lab=Vout}
C {gnd.sym} 540 -140 0 0 {name=l1 lab=GND}
C {vdd.sym} 540 -530 0 0 {name=l2 lab=VDD}
C {vsource.sym} 60 -190 0 0 {name=Vin value=0.66 savecurrent=false}
C {vcvs.sym} 370 -450 1 0 {name=E1 value=1}
C {vcvs.sym} 370 -260 1 1 {name=E2 value=1}
C {isource.sym} 1000 -320 0 0 {name=I0 value=1u}
C {vdd.sym} 1000 -510 0 0 {name=l4 lab=VDD}
C {gnd.sym} 1000 -250 0 0 {name=l5 lab=GND}
C {isource.sym} 1250 -460 0 0 {name=I1 value=1u}
C {vdd.sym} 1250 -520 0 0 {name=l6 lab=VDD}
C {gnd.sym} 1250 -290 0 0 {name=l7 lab=GND}
C {vsource.sym} 820 -240 0 0 {name=V2 value=1.65 savecurrent=false}
C {vsource.sym} 910 -240 0 0 {name=V3 value=0.825 savecurrent=false}
C {vdd.sym} 820 -290 0 0 {name=l8 lab=VDD}
C {gnd.sym} 820 -170 0 0 {name=l9 lab=GND}
C {gnd.sym} 910 -170 0 0 {name=l10 lab=GND}
C {lab_pin.sym} 910 -290 0 0 {name=p1 sig_type=std_logic lab=vcm}
C {lab_pin.sym} 320 -550 0 0 {name=p2 sig_type=std_logic lab=vcm}
C {lab_pin.sym} 320 -170 0 0 {name=p3 sig_type=std_logic lab=vcm}
C {lab_pin.sym} 1150 -410 0 0 {name=p4 sig_type=std_logic lab=VDZN}
C {lab_pin.sym} 420 -170 2 0 {name=p5 sig_type=std_logic lab=VDZN}
C {lab_pin.sym} 420 -550 0 1 {name=p7 sig_type=std_logic lab=VDZP}
C {lab_pin.sym} 920 -390 2 1 {name=p6 sig_type=std_logic lab=VDZP}
C {gnd.sym} 60 -120 0 0 {name=l11 lab=GND}
C {title.sym} 160 -30 0 0 {name=l12 author="Nithin P, Praveen Kumar, Pramoda S R"}
C {code_shown.sym} 1000 -670 0 0 {
name=TT_MODELS
only_toplevel=true
value="
** IHP models
.lib cornerMOSlv.lib mos_tt
.lib cornerMOShv.lib mos_tt
"
spice_ignore=false
      }
C {lab_pin.sym} 780 -350 0 1 {name=p8 sig_type=std_logic lab=Vout}
C {devices/launcher.sym} 770 -620 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/RamP_tb1_CP_FB1.raw; set show_hidden_texts 1; xschem annotate_op"}
C {ngspice_probe.sym} 300 -350 0 0 {name=r1}
C {sg13g2_pr/sg13_hv_pmos.sym} 520 -450 0 0 {name=MP_STG3
l=0.5u
w=6.1u
ng=1
m=4
model=sg13_hv_pmos
spiceprefix=X
}
C {sg13g2_pr/sg13_hv_pmos.sym} 980 -430 0 0 {name=MP_DZ_RP
l=0.5u
w=6.1u
ng=1
m=1
model=sg13_hv_pmos
spiceprefix=X
}
C {sg13g2_pr/sg13_hv_nmos.sym} 520 -260 0 0 {name=MN_STG3
l=1u
w=3.3u
ng=1
m=4
model=sg13_hv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_hv_nmos.sym} 1230 -360 0 0 {name=MN_DZ_RP
l=1u
w=3.3u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X
}
C {code.sym} 40 -510 0 0 {name=SAVE_COMMANDS only_toplevel=false value="
.save @n.xmp_stg3.nsg13_hv_pmos[gm]
.save @n.xmp_stg3.nsg13_hv_pmos[gds]
.save @n.xmp_stg3.nsg13_hv_pmos[vth]
.save @n.xmp_stg3.nsg13_hv_pmos[vdss]
.save @n.xmp_stg3.nsg13_hv_pmos[cgg]
.save @n.xmp_stg3.nsg13_hv_pmos[cgsol]
.save @n.xmp_stg3.nsg13_hv_pmos[cgdol]
.save @n.xmp_dz_rp.nsg13_hv_pmos[gm]
.save @n.xmp_dz_rp.nsg13_hv_pmos[gds]
.save @n.xmp_dz_rp.nsg13_hv_pmos[vth]
.save @n.xmp_dz_rp.nsg13_hv_pmos[vdss]
.save @n.xmp_dz_rp.nsg13_hv_pmos[cgg]
.save @n.xmp_dz_rp.nsg13_hv_pmos[cgsol]
.save @n.xmp_dz_rp.nsg13_hv_pmos[cgdol]
.save @n.xmn_stg3.nsg13_hv_nmos[gm]
.save @n.xmn_stg3.nsg13_hv_nmos[gds]
.save @n.xmn_stg3.nsg13_hv_nmos[vth]
.save @n.xmn_stg3.nsg13_hv_nmos[vdss]
.save @n.xmn_stg3.nsg13_hv_nmos[cgg]
.save @n.xmn_stg3.nsg13_hv_nmos[cgsol]
.save @n.xmn_stg3.nsg13_hv_nmos[cgdol]
.save @n.xmn_dz_rp.nsg13_hv_nmos[gm]
.save @n.xmn_dz_rp.nsg13_hv_nmos[gds]
.save @n.xmn_dz_rp.nsg13_hv_nmos[vth]
.save @n.xmn_dz_rp.nsg13_hv_nmos[vdss]
.save @n.xmn_dz_rp.nsg13_hv_nmos[cgg]
.save @n.xmn_dz_rp.nsg13_hv_nmos[cgsol]
.save @n.xmn_dz_rp.nsg13_hv_nmos[cgdol]

"}
C {sg13g2_pr/annotate_fet_params.sym} 680 -530 0 0 {name=annot1 ref=MP_STG3}
C {sg13g2_pr/annotate_fet_params.sym} 1110 -330 0 0 {name=annot2 ref=MN_DZ_RP}
C {sg13g2_pr/annotate_fet_params.sym} 800 -530 0 0 {name=annot3 ref=MN_STG3}
C {sg13g2_pr/annotate_fet_params.sym} 1060 -540 0 0 {name=annot4 ref=MP_DZ_RP}
C {capa.sym} 170 -350 1 0 {name=Cs
m=1
value=5p
footprint=1206
device="ceramic capacitor"}
C {capa.sym} 380 -680 1 0 {name=Cf
m=1
value=1p
footprint=1206
device="ceramic capacitor"}
C {ngspice_probe.sym} 60 -230 0 1 {name=r5}
C {lab_pin.sym} 460 -450 3 0 {name=p9 sig_type=std_logic lab=Vgp}
C {lab_pin.sym} 450 -260 1 0 {name=p10 sig_type=std_logic lab=Vgn}
C {lab_pin.sym} 60 -350 0 0 {name=p11 sig_type=std_logic lab=Vin}
C {lab_pin.sym} 300 -350 0 1 {name=p12 sig_type=std_logic lab=Vx}
C {capa.sym} 750 -240 0 0 {name=C1
m=1
value=100f
footprint=1206
device="ceramic capacitor"}
C {ammeter.sym} 750 -300 0 0 {name=Vmeas savecurrent=true spice_ignore=0}
C {code.sym} 30 -660 0 0 {name=NGSPICE only_toplevel=false value="
.ic v(vout)=0.825 v(Vin)=0.825 v(vgn)=0.67213 v(vgp)=0.99954 v(Vx)=0.825
.option wnflag=1
.option savecurrents
.temp 27
.control
save all
write INV_ota_rongm_try1.raw
set appendwrite 
op
write INV_ota_rongm_try1.raw
**dc V1 0 1.65 1m
tran 1n 3u 0.1n
**ac dec 20 1 1e10
plot v(vout) v(vin)
plot v(vout)
plot v(vin) 
plot v(vx)
plot v(vgp)
plot v(vgn)
plot @n.xmp_stg3.nsg13_hv_pmos[ids] @n.xmn_stg3.nsg13_hv_nmos[ids]
plot @n.xmp_stg3.nsg13_hv_pmos[ids]
plot @n.xmn_stg3.nsg13_hv_nmos[ids]
plot @c1[i]
wrdata /foss/designs/CAC/Inverter-OTA/Ron_gm/inv-OA-try1_Error3.txt v(vout) v(vx) v(vin) @n.xmp_stg3.nsg13_hv_pmos[ids]  @n.xmn_stg3.nsg13_hv_nmos[ids] @c1[i]
.endc
"
}
C {vsource.sym} 60 -290 0 0 {name=Vin2 value=" PULSE(0 0.33 1p 10n 10n 0.75u 1.5u 4)" savecurrent=false}
