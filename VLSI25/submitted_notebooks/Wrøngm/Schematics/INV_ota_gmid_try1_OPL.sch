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
N 300 -350 300 -260 {lab=Vin}
N 300 -450 340 -450 {lab=Vin}
N 300 -260 340 -260 {lab=Vin}
N 1000 -350 1080 -350 {lab=VDZP}
N 1000 -430 1000 -350 {lab=VDZP}
N 1000 -430 1040 -430 {lab=VDZP}
N 1080 -400 1080 -350 {lab=VDZP}
N 1080 -510 1080 -430 {lab=VDD}
N 1080 -290 1080 -250 {lab=GND}
N 1320 -510 1320 -480 {lab=VDD}
N 1320 -400 1320 -380 {lab=VDZN}
N 1220 -350 1280 -350 {lab=VDZN}
N 1220 -400 1220 -350 {lab=VDZN}
N 1220 -400 1320 -400 {lab=VDZN}
N 1320 -420 1320 -400 {lab=VDZN}
N 1320 -350 1320 -280 {lab=GND}
N 900 -210 900 -170 {lab=GND}
N 900 -290 900 -270 {lab=VDD}
N 1010 -210 1010 -170 {lab=GND}
N 1010 -290 1010 -270 {lab=vcm}
N 120 -160 120 -120 {lab=GND}
N 120 -260 120 -220 {lab=#net1}
N 390 -550 420 -550 {lab=VDZP}
N 390 -550 390 -490 {lab=VDZP}
N 350 -550 350 -490 {lab=vcm}
N 320 -550 350 -550 {lab=vcm}
N 390 -220 390 -170 {lab=VDZN}
N 390 -170 420 -170 {lab=VDZN}
N 350 -220 350 -170 {lab=vcm}
N 320 -170 350 -170 {lab=vcm}
N 300 -450 300 -350 {lab=Vin}
N 540 -350 750 -350 {lab=Vout}
N 120 -350 300 -350 {lab=Vin}
N 120 -350 120 -320 {lab=Vin}
N 750 -350 780 -350 {lab=Vout}
N 750 -210 750 -160 {lab=GND}
N 540 -160 750 -160 {lab=GND}
N 540 -260 540 -160 {lab=GND}
N 750 -350 750 -270 {lab=Vout}
C {gnd.sym} 540 -140 0 0 {name=l1 lab=GND}
C {vdd.sym} 540 -530 0 0 {name=l2 lab=VDD}
C {vsource.sym} 120 -190 0 0 {name=Vin value=0.825 savecurrent=false}
C {vcvs.sym} 370 -450 1 0 {name=E1 value=1}
C {vcvs.sym} 370 -260 1 1 {name=E2 value=1}
C {isource.sym} 1080 -320 0 0 {name=I0 value=1u}
C {vdd.sym} 1080 -510 0 0 {name=l4 lab=VDD}
C {gnd.sym} 1080 -250 0 0 {name=l5 lab=GND}
C {isource.sym} 1320 -450 0 0 {name=I1 value=1u}
C {vdd.sym} 1320 -510 0 0 {name=l6 lab=VDD}
C {gnd.sym} 1320 -280 0 0 {name=l7 lab=GND}
C {vsource.sym} 900 -240 0 0 {name=V2 value=1.65 savecurrent=false}
C {vsource.sym} 1010 -240 0 0 {name=V3 value=0.825 savecurrent=false}
C {vdd.sym} 900 -290 0 0 {name=l8 lab=VDD}
C {gnd.sym} 900 -170 0 0 {name=l9 lab=GND}
C {gnd.sym} 1010 -170 0 0 {name=l10 lab=GND}
C {lab_pin.sym} 1010 -290 0 0 {name=p1 sig_type=std_logic lab=vcm}
C {lab_pin.sym} 320 -550 0 0 {name=p2 sig_type=std_logic lab=vcm}
C {lab_pin.sym} 320 -170 0 0 {name=p3 sig_type=std_logic lab=vcm}
C {lab_pin.sym} 1220 -380 0 0 {name=p4 sig_type=std_logic lab=VDZN}
C {lab_pin.sym} 420 -170 2 0 {name=p5 sig_type=std_logic lab=VDZN}
C {lab_pin.sym} 420 -550 0 1 {name=p7 sig_type=std_logic lab=VDZP}
C {lab_pin.sym} 1000 -390 2 1 {name=p6 sig_type=std_logic lab=VDZP}
C {gnd.sym} 120 -120 0 0 {name=l11 lab=GND}
C {title.sym} 160 -30 0 0 {name=l12 author="Nithin Purushothama"}
C {code_shown.sym} -330 -500 0 0 {
name=TT_MODELS
only_toplevel=true
value="
** IHP models
.lib cornerMOSlv.lib mos_tt
.lib cornerMOShv.lib mos_tt
"
spice_ignore=false
      }
C {devices/code_shown.sym} -690 -570 0 0 {name=NGSPICE1 only_toplevel=true 
value="
.ic v(vout)=0.825 v(Vin)=0.825 v(vgn)=0.67213 v(vgp)=0.99954 v(Vx)=0.825
.option wnflag=1
.option savecurrents
.temp 27
.control
save all
write INV_ota_gmid_try1_OPL.raw
set appendwrite 
op
write INV_ota_gmid_try1_OPL.raw
**dc V1 0 1.65 1m
**tran 1n 8u 0.1n
ac dec 20 1 1e10
plot vdb(vout)
**plot v(vout) 
**plot v(vin) 
**plot v(vgp)
**plot v(vgn)
**plot @n.xmp_stg3.nsg13_hv_pmos[ids] @n.xmn_stg3.nsg13_hv_nmos[ids]
**plot @n.xmp_stg3.nsg13_hv_pmos[ids]
**plot @n.xmn_stg3.nsg13_hv_nmos[ids]
**plot @c1[i]
.endc
"}
C {lab_pin.sym} 780 -350 0 1 {name=p8 sig_type=std_logic lab=Vout}
C {devices/launcher.sym} -240 -340 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/RamP_tb1_CP_FB1.raw; set show_hidden_texts 1; xschem annotate_op"}
C {sg13g2_pr/sg13_hv_pmos.sym} 520 -450 0 0 {name=MP_STG3
l=0.5u
w=4.5u
ng=1
m=4
model=sg13_hv_pmos
spiceprefix=X
}
C {sg13g2_pr/sg13_hv_pmos.sym} 1060 -430 0 0 {name=MP_DZ_RP
l=0.5u
w=4.5u
ng=1
m=1
model=sg13_hv_pmos
spiceprefix=X
}
C {sg13g2_pr/sg13_hv_nmos.sym} 520 -260 0 0 {name=MN_STG3
l=1u
w=2.3u
ng=1
m=4
model=sg13_hv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_hv_nmos.sym} 1300 -350 0 0 {name=MN_DZ_RP
l=1u
w=2.3u
ng=1
m=1
model=sg13_hv_nmos
spiceprefix=X
}
C {code.sym} 70 -560 0 0 {name=SAVE_COMMANDS only_toplevel=false value="
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
C {sg13g2_pr/annotate_fet_params.sym} 630 -530 0 0 {name=annot1 ref=MP_STG3}
C {sg13g2_pr/annotate_fet_params.sym} 1190 -280 0 0 {name=annot2 ref=MN_DZ_RP}
C {sg13g2_pr/annotate_fet_params.sym} 640 -320 0 0 {name=annot3 ref=MN_STG3}
C {sg13g2_pr/annotate_fet_params.sym} 1170 -530 0 0 {name=annot4 ref=MP_DZ_RP}
C {ngspice_probe.sym} 120 -230 0 1 {name=r5}
C {lab_pin.sym} 460 -450 3 0 {name=p9 sig_type=std_logic lab=Vgp}
C {lab_pin.sym} 450 -260 1 0 {name=p10 sig_type=std_logic lab=Vgn}
C {lab_pin.sym} 120 -350 0 0 {name=p11 sig_type=std_logic lab=Vin}
C {capa.sym} 750 -240 0 0 {name=C1
m=1
value=1p
footprint=1206
device="ceramic capacitor"}
C {vsource.sym} 120 -290 0 0 {name=Vin1 value="0 ac 1" savecurrent=false}
