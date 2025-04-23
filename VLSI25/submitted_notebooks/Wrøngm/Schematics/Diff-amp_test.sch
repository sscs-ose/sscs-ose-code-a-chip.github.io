v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N -820 -400 -820 -340 {lab=S}
N -610 -400 -610 -340 {lab=S}
N -710 -340 -610 -340 {lab=S}
N -710 -220 -710 -190 {lab=GND}
N -710 -340 -710 -280 {lab=S}
N -820 -340 -710 -340 {lab=S}
N -930 -430 -930 -410 {lab=#net1}
N -930 -350 -930 -320 {lab=GND}
N -820 -680 -710 -680 {lab=VDD}
N -710 -720 -710 -680 {lab=VDD}
N -710 -680 -610 -680 {lab=VDD}
N -930 -640 -930 -620 {lab=VDD}
N -930 -560 -930 -530 {lab=GND}
N -820 -680 -820 -640 {lab=VDD}
N -610 -680 -610 -640 {lab=VDD}
N -660 -430 -610 -430 {lab=GND}
N -660 -430 -660 -190 {lab=GND}
N -820 -430 -660 -430 {lab=GND}
N -710 -190 -660 -190 {lab=GND}
N -570 -430 -540 -430 {lab=#net1}
N -710 -190 -710 -160 {lab=GND}
N -610 -550 -610 -460 {lab=D2}
N -820 -550 -820 -460 {lab=D1}
N -720 -550 -720 -510 {lab=#net2}
N -430 -530 -430 -510 {lab=#net2}
N -430 -530 -340 -530 {lab=#net2}
N -400 -490 -400 -460 {lab=#net3}
N -400 -490 -340 -490 {lab=#net3}
N -720 -550 -700 -550 {lab=#net2}
N -730 -550 -720 -550 {lab=#net2}
N -720 -510 -430 -510 {lab=#net2}
N -820 -550 -790 -550 {lab=D1}
N -820 -580 -820 -550 {lab=D1}
N -640 -550 -610 -550 {lab=D2}
N -610 -580 -610 -550 {lab=D2}
N -300 -480 -300 -450 {lab=GND}
N -720 -590 -650 -590 {lab=#net4}
N -780 -630 -650 -630 {lab=GND}
N -300 -570 -300 -540 {lab=#net4}
N -720 -570 -300 -570 {lab=#net4}
N -720 -590 -720 -570 {lab=#net4}
N -780 -590 -720 -590 {lab=#net4}
N -400 -400 -400 -380 {lab=GND}
N -890 -430 -860 -430 {lab=#net1}
N -890 -430 -890 -390 {lab=#net1}
N -930 -430 -890 -430 {lab=#net1}
N -890 -390 -540 -390 {lab=#net1}
N -540 -430 -540 -390 {lab=#net1}
C {sg13g2_pr/sg13_lv_nmos.sym} -840 -430 2 1 {name=M1
l=3
w=\{wx\}
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} -590 -430 2 0 {name=M2
l=3
w=\{wx\}
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {isource.sym} -710 -250 0 0 {name=I0 value=2u}
C {gnd.sym} -710 -160 0 0 {name=l1 lab=GND}
C {vsource.sym} -930 -380 0 0 {name=V1 value=0.825 savecurrent=false}
C {gnd.sym} -930 -320 0 0 {name=l2 lab=GND}
C {vdd.sym} -710 -720 0 0 {name=l3 lab=VDD}
C {vsource.sym} -930 -590 0 0 {name=V2 value=1.65 savecurrent=false}
C {gnd.sym} -930 -530 0 0 {name=l4 lab=GND}
C {vdd.sym} -930 -640 0 0 {name=l5 lab=VDD}
C {lab_pin.sym} -820 -530 0 1 {name=p1 sig_type=std_logic lab=D1}
C {lab_pin.sym} -610 -530 0 0 {name=p2 sig_type=std_logic lab=D2}
C {lab_pin.sym} -710 -340 3 1 {name=p3 sig_type=std_logic lab=S}
C {devices/code_shown.sym} -1920 -570 0 0 {name=COMMANDS1 only_toplevel=false
value="
* ngspice commands
.param wx=1u
.options savecurrents

.control
  let start_w = 0.5u
  let stop_w = 20u
  let delta_w = 0.1u
  let w_act = start_w

  while w_act le stop_w
    let wx = w_act

    alterparam wx = $&w_act
    reset
    save all

    dc v1 0 1.65 1m  
    wrdata /foss/designs/CAC/5T-OTA/Diff-amp_test_3.txt v(D1) v(D2) v(S) @n.xm1.nsg13_lv_nmos[gm] @n.xm1.nsg13_lv_nmos[gds] @n.xm1.nsg13_lv_nmos[vgs] @n.xm1.nsg13_lv_nmos[vth] @n.xm1.nsg13_lv_nmos[vsat] @n.xm1.nsg13_lv_nmos[vds] @n.xm1.nsg13_lv_nmos[ids] @n.xm1.nsg13_lv_nmos[cgg] 
    let w_act = w_act + delta_w
    set appendwrite  
  end
.endc
"}
C {devices/code_shown.sym} -1950 -890 0 0 {name=COMMANDS2 only_toplevel=false
value="
.save @n.xm1.nsg13_lv_nmos[gds]
.save @n.xm1.nsg13_lv_nmos[gm]
.save @n.xm1.nsg13_lv_nmos[gmb]
.save @n.xm1.nsg13_lv_nmos[ids]
.save @n.xm1.nsg13_lv_nmos[l]
.save @n.xm1.nsg13_lv_nmos[vth]
.save @n.xm2.nsg13_lv_nmos[cgd]
.save @n.xm2.nsg13_lv_nmos[cgg]
.save @n.xm2.nsg13_lv_nmos[cgs]
.save @n.xm2.nsg13_lv_nmos[gds]
.save @n.xm2.nsg13_lv_nmos[gm]
.save @n.xm2.nsg13_lv_nmos[gmb]
.save @n.xm2.nsg13_lv_nmos[ids]
.save @n.xm2.nsg13_lv_nmos[l]
.save @n.xm2.nsg13_lv_nmos[vth]
"}
C {devices/code_shown.sym} -1490 -400 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
"}
C {devices/launcher.sym} -1430 -460 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/Diff-amp_test.raw; set show_hidden_texts 1; xschem annotate_op"}
C {vcvs.sym} -300 -510 0 0 {name=E1 value=10k}
C {res.sym} -760 -550 1 0 {name=R1
value=100k
footprint=1206
device=resistor
m=1}
C {res.sym} -670 -550 1 0 {name=R2
value=100k
footprint=1206
device=resistor
m=1}
C {vsource.sym} -400 -430 0 0 {name=V3 value=0.825 savecurrent=false}
C {vccs.sym} -820 -610 0 1 {name=G1 value=1e-6}
C {vccs.sym} -610 -610 0 0 {name=G2 value=1e-6}
C {gnd.sym} -300 -450 0 0 {name=l6 lab=GND}
C {gnd.sym} -720 -630 0 0 {name=l7 lab=GND}
C {gnd.sym} -400 -380 0 0 {name=l8 lab=GND}
