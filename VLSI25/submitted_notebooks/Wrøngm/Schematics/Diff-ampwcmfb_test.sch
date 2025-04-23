v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 440 190 440 250 {lab=S}
N 650 190 650 250 {lab=S}
N 550 250 650 250 {lab=S}
N 550 370 550 400 {lab=GND}
N 550 250 550 310 {lab=S}
N 440 250 550 250 {lab=S}
N 330 160 330 180 {lab=#net1}
N 330 240 330 270 {lab=GND}
N 440 -90 550 -90 {lab=VDD}
N 550 -130 550 -90 {lab=VDD}
N 330 -50 330 -30 {lab=VDD}
N 330 30 330 60 {lab=GND}
N 440 -90 440 -50 {lab=VDD}
N 650 -90 650 -50 {lab=VDD}
N 600 160 650 160 {lab=GND}
N 600 160 600 400 {lab=GND}
N 440 160 600 160 {lab=GND}
N 550 400 600 400 {lab=GND}
N 690 160 720 160 {lab=#net1}
N 550 400 550 430 {lab=GND}
N 440 40 440 130 {lab=D1}
N 650 10 650 130 {lab=D2}
N 370 160 400 160 {lab=#net1}
N 370 160 370 200 {lab=#net1}
N 330 160 370 160 {lab=#net1}
N 370 200 720 200 {lab=#net1}
N 720 160 720 200 {lab=#net1}
N 440 40 550 40 {lab=D1}
N 440 10 440 40 {lab=D1}
N 550 -40 610 -40 {lab=VDD}
N 550 -90 650 -90 {lab=VDD}
N 550 0 610 0 {lab=D1}
N 550 0 550 40 {lab=D1}
N 480 0 550 0 {lab=D1}
N 550 -90 550 -40 {lab=VDD}
N 480 -40 550 -40 {lab=VDD}
N 90 70 90 80 {lab=GND}
N 90 -20 90 10 {lab=Gx_Value}
N 180 80 180 90 {lab=GND}
N 180 -20 180 20 {lab=Gx_Value}
N 90 -20 180 -20 {lab=Gx_Value}
C {isource.sym} 550 340 0 0 {name=I0 value=2u}
C {gnd.sym} 550 430 0 0 {name=l1 lab=GND}
C {vsource.sym} 330 210 0 0 {name=V1 value=0.825 savecurrent=false}
C {gnd.sym} 330 270 0 0 {name=l2 lab=GND}
C {vdd.sym} 550 -130 0 0 {name=l3 lab=VDD}
C {vsource.sym} 330 0 0 0 {name=V2 value=1.65 savecurrent=false}
C {gnd.sym} 330 60 0 0 {name=l4 lab=GND}
C {vdd.sym} 330 -50 0 0 {name=l5 lab=VDD}
C {lab_pin.sym} 440 60 0 1 {name=p1 sig_type=std_logic lab=D1}
C {lab_pin.sym} 650 60 0 0 {name=p2 sig_type=std_logic lab=D2}
C {lab_pin.sym} 550 250 3 1 {name=p3 sig_type=std_logic lab=S}
C {devices/code_shown.sym} -670 40 0 0 {name=COMMANDS1 only_toplevel=false
value="
* ngspice commands
.param wx=0.5u
.param Gx=1u
.options savecurrents

.control
  let start_w = 0.5u
  let stop_w = 20u
  let delta_w = 0.25u

  let start_gx = 1u
  let stop_gx = 10u
  let delta_gx = 1u

  let w_act = start_w

  while w_act le stop_w
    let gx_act = start_gx

    while gx_act le stop_gx
      alterparam wx = $&w_act
      alterparam Gx = $&gx_act

      reset
      save all

      dc v1 0 1.65 0.1

      wrdata /foss/designs/CAC/STG1/Model-1/without-CMFB/5T-OTA/Diff_amp_wcmfb_L3_0.txt @n.xm1.nsg13_lv_nmos[w] v(D1) v(D2) v(S) @n.xm1.nsg13_lv_nmos[gm] @n.xm1.nsg13_lv_nmos[gds] @n.xm1.nsg13_lv_nmos[vgs] @n.xm1.nsg13_lv_nmos[vth] @n.xm1.nsg13_lv_nmos[vsat] @n.xm1.nsg13_lv_nmos[vds] @n.xm1.nsg13_lv_nmos[ids] @n.xm1.nsg13_lv_nmos[cgg] v(Gx_Value)

      let gx_act = gx_act + delta_gx
      set appendwrite
    end

    let w_act = w_act + delta_w
  end
.endc

"}
C {devices/code_shown.sym} -690 -300 0 0 {name=COMMANDS2 only_toplevel=false
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
C {devices/code_shown.sym} -230 190 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value=".lib cornerMOSlv.lib mos_tt
"}
C {devices/launcher.sym} -170 130 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/Diff-amp_test.raw; set show_hidden_texts 1; xschem annotate_op"}
C {vccs.sym} 440 -20 0 1 {name=G1 value=\{Gx\}}
C {vccs.sym} 650 -20 0 0 {name=G2 value=\{Gx\}}
C {sg13g2_pr/sg13_lv_nmos.sym} 420 160 0 0 {name=M1
l=3u
w=\{wx\}
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13g2_pr/sg13_lv_nmos.sym} 670 160 0 1 {name=M2
l=3u
w=\{wx\}
ng=1
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {vsource.sym} 90 40 0 0 {name=V3 value=\{Gx\} savecurrent=false}
C {gnd.sym} 90 80 0 0 {name=l6 lab=GND}
C {res.sym} 180 50 0 0 {name=R1
value=1
footprint=1206
device=resistor
m=1}
C {gnd.sym} 180 90 0 0 {name=l7 lab=GND}
C {lab_pin.sym} 130 -20 1 0 {name=p4 sig_type=std_logic lab=Gx_Value}
