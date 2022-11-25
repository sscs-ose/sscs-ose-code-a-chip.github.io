v {xschem version=3.0.0 file_version=1.2 }
G {}
K {}
V {}
S {}
E {}
T {PULSE(VL VH TD TR TF PW PER PHASE) } -380 -120 0 0 0.4 0.4 {}
N -830 -210 -830 -190 { lab=GND}
N -830 -320 -830 -270 { lab=VSS}
N -750 -210 -750 -190 { lab=GND}
N -750 -320 -750 -270 { lab=VH}
N 200 -500 250 -500 {
lab=D1_s}
N 200 -450 250 -450 {
lab=D2_s}
N 200 -400 250 -400 {
lab=D2_N_s}
N 200 -350 250 -350 {
lab=D1_N_s}
N 890 -450 950 -450 {
lab=VOUT_CORE}
N 1010 -450 1060 -450 {
lab=VOUT_CORE}
N 610 -450 680 -450 {
lab=V_res}
N 610 -500 640 -500 {
lab=VH}
N 610 -400 640 -400 {
lab=VSS}
N 950 -450 1010 -450 {
lab=VOUT_CORE}
N 1010 -240 1010 -200 {
lab=VSS}
N 1010 -450 1010 -420 {
lab=VOUT_CORE}
N 860 -450 890 -450 {
lab=VOUT_CORE}
N -920 -210 -920 -190 { lab=GND}
N -920 -320 -920 -270 { lab=VDIG}
N 220 -550 250 -550 {
lab=VDIG}
N -910 -790 -910 -780 {
lab=D1_s}
N -910 -790 -900 -790 {
lab=D1_s}
N -910 -720 -910 -710 {
lab=VSS}
N -920 -710 -910 -710 {
lab=VSS}
N -910 -700 -910 -690 {
lab=D2_s}
N -910 -700 -900 -700 {
lab=D2_s}
N -910 -630 -910 -620 {
lab=VSS}
N -920 -620 -910 -620 {
lab=VSS}
N -910 -610 -910 -600 {
lab=D2_N_s}
N -910 -610 -900 -610 {
lab=D2_N_s}
N -910 -540 -910 -530 {
lab=VSS}
N -920 -530 -910 -530 {
lab=VSS}
N -910 -520 -910 -510 {
lab=D1_N_s}
N -910 -520 -900 -520 {
lab=D1_N_s}
N -910 -450 -910 -440 {
lab=VSS}
N -920 -440 -910 -440 {
lab=VSS}
N -660 -210 -660 -190 { lab=GND}
N -660 -320 -660 -270 { lab=VH_LS}
N 1010 -360 1010 -300 {
lab=#net1}
N 900 -390 900 -350 {
lab=VSS}
N 760 -450 800 -450 {
lab=V_inductor}
N 680 -450 700 -450 {
lab=V_res}
N 430 -650 460 -650 {
lab=VH_LS}
N 390 -250 390 -220 {
lab=V_CFTOP}
N 470 -250 470 -220 {
lab=V_CFBOT}
N 390 -160 390 -130 {
lab=#net2}
N 390 -130 400 -130 {
lab=#net2}
N 470 -160 470 -130 {
lab=#net3}
N 460 -130 470 -130 {
lab=#net3}
C {devices/vsource.sym} -830 -240 0 0 {name=V2 value=0}
C {devices/gnd.sym} -830 -190 0 0 {name=l9 lab=GND}
C {devices/code_shown.sym} -850 -80 0 0 {name=s1 only_toplevel=false value="
.param VIN = 5
.param VDIG = 1.8
.param VH = 5
.param RL = 50
.option scale=1e-6
*.option temp=70
.ic v(V_CFTOP) = VH/2
.ic v(vout_core)=3
.ic v(V_CFBOT) = 0
*.probe vd(MP2:G:S)
.save v(D1) v(D2) v(D1_N) v(D2_N) v(VOUT_CORE) v(vh) i(v9) i(v3) i(v4) v(v_cftop,v_cfbot) v(D1,v_cftop) v(D2,vout_core) v(D2_N,v_cfbot) v(D1_Nv,VSS) v(v_out_ls1) v(v_out_ls2) v(d2_n,v_cfbot) v(D1_s) v(D2_s)	v(D2_N_s) v(D1_N_s)
.save @m.xm4.msky130_fd_pr__nfet_g5v0d10v5[vds]
.param mc_mm_switch=0

.lib /foss/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice TT

.options savecurrents


.control
compose resist values 300 44 22 11 (5.5) 3
foreach res $&resist
alterparam RL=$res
reset
tran 1n 30u
run
wrdata /foss/designs/personal/3LFCC_AC3E/xschem/testbench/Core/3LFCC_core_wfilter.txt tran.v(vout_core) tran.i(v3) tran.i(v4) tran.i(v9)
set appendwrite
end

*Relación Pulso P y N para acondicionar tiempos muertos (reducir peaks)







**Problema actual, eficiencia no se logra calcular debido a que no transicionan bien todo los estados, (Cuando el Flycap esta flotante no esta consumiendo energía, es decir la carga no esta conectada a la fuente de entrada...)
** Si bien D1- D1_N y D2- D2_N estan con sus respectivos tiempos muertos (redución de peaks), falta sincronizar bien D1 con D2 para lograr la conexión correcta para que la carga se conecte a la fuente en estado de flycap flotante.

.endc
"}
C {devices/vsource.sym} -750 -240 0 0 {name=V3 value=\{VH\}}
C {devices/gnd.sym} -750 -190 0 0 {name=l23 lab=GND}
C {devices/lab_wire.sym} -750 -320 0 0 {name=l24 sig_type=std_logic lab=VH}
C {devices/lab_wire.sym} 200 -500 0 0 {name=l18 sig_type=std_logic lab=D1_s}
C {devices/lab_wire.sym} 200 -450 0 0 {name=l20 sig_type=std_logic lab=D2_s}
C {devices/lab_wire.sym} 200 -400 0 0 {name=l25 sig_type=std_logic lab=D2_N_s}
C {devices/lab_wire.sym} 200 -350 0 0 {name=l26 sig_type=std_logic lab=D1_N_s}
C {devices/lab_wire.sym} 390 -250 0 0 {name=l27 sig_type=std_logic lab=V_CFTOP}
C {devices/lab_wire.sym} 470 -250 0 0 {name=l28 sig_type=std_logic lab=V_CFBOT}
C {devices/lab_wire.sym} 860 -450 0 1 {name=l29 sig_type=std_logic lab=VOUT_CORE}
C {devices/lab_wire.sym} 640 -500 2 0 {name=l32 sig_type=std_logic lab=VH}
C {devices/lab_wire.sym} 640 -400 2 0 {name=l33 sig_type=std_logic lab=VSS}
C {devices/isource.sym} 1090 -390 0 0 {name=I0 value=0.15
}
C {devices/lab_wire.sym} 1010 -200 0 0 {name=l1 sig_type=std_logic lab=VSS}
C {devices/res.sym} 1010 -270 0 0 {name=RL
value=\{RL\}
footprint=1206
device=resistor
m=1}
C {devices/vsource.sym} -920 -240 0 0 {name=V8 value=\{VDIG\}}
C {devices/gnd.sym} -920 -190 0 0 {name=l23 lab=GND}
C {devices/lab_wire.sym} -920 -320 0 0 {name=l24 sig_type=std_logic lab=VDIG}
C {devices/lab_wire.sym} 220 -550 0 0 {name=l24 sig_type=std_logic lab=VDIG}
C {devices/lab_wire.sym} -900 -790 0 1 {name=l11 sig_type=std_logic lab=D1_s}
C {devices/vsource.sym} -910 -570 0 0 {name=V6 value="PULSE(0 1.8 176n 1n 1n 316n 1000n)"}
C {devices/vsource.sym} -910 -660 0 0 {name=V5 value="PULSE(0 1.8 166n 1n 1n 333n 1000n)"}
C {devices/lab_wire.sym} -900 -700 0 1 {name=l43 sig_type=std_logic lab=D2_s}
C {devices/lab_pin.sym} -900 -610 0 1 {name=l2 sig_type=std_logic lab=D2_N_s
}
C {devices/vsource.sym} -910 -480 0 0 {name=V7 value="PULSE(0 1.8 676n 1n 1n 313n 1000n)"}
C {devices/lab_pin.sym} -900 -520 0 1 {name=l3 sig_type=std_logic lab=D1_N_s
}
C {devices/lab_wire.sym} -920 -440 0 0 {name=l45 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} -920 -710 0 0 {name=l4 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} -920 -620 0 0 {name=l5 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} -920 -530 0 0 {name=l6 sig_type=std_logic lab=VSS}
C {devices/vsource.sym} -910 -750 0 0 {name=V1 value="PULSE(1.8 0 10n 1n 1n 646n 1000n)"}
C {devices/lab_wire.sym} -830 -320 0 0 {name=l15 sig_type=std_logic lab=VSS}
C {devices/vsource.sym} -660 -240 0 0 {name=V4 value=\{VH\}}
C {devices/gnd.sym} -660 -190 0 0 {name=l23 lab=GND}
C {devices/lab_wire.sym} -660 -320 0 0 {name=l24 sig_type=std_logic lab=VH_LS}
C {devices/vsource.sym} 1010 -390 0 0 {name=V9 value=0}
C {devices/capa.sym} 900 -420 0 0 {name=C4
m=1
value=5.1n
footprint=1206
device="ceramic capacitor"}
C {devices/lab_wire.sym} 900 -350 0 0 {name=l19 sig_type=std_logic lab=VSS}
C {devices/ind.sym} 830 -450 1 0 {name=L1
m=1
value=51u
footprint=1206
device=inductor}
C {devices/lab_wire.sym} 780 -450 1 1 {name=l21 sig_type=std_logic lab=V_inductor}
C {devices/res.sym} 730 -450 1 0 {name=R1
value=0
footprint=1206
device=resistor
m=1}
C {devices/lab_wire.sym} 680 -450 1 1 {name=l22 sig_type=std_logic lab=V_res}
C {personal/3LFCC_AC3E/xschem/hierarchy_sch/core.sym} 190 -350 0 0 {name=X1}
C {devices/lab_wire.sym} 460 -650 2 0 {name=l7 sig_type=std_logic lab=VH_LS}
C {devices/capa.sym} 430 -130 3 0 {name=C3
m=1
value=680n
footprint=1206
device="ceramic capacitor"}
C {devices/ind.sym} 390 -190 2 0 {name=L2
m=1
value=1n
footprint=1206
device=inductor}
C {devices/ind.sym} 470 -190 2 0 {name=L3
m=1
value=1n
footprint=1206
device=inductor}
