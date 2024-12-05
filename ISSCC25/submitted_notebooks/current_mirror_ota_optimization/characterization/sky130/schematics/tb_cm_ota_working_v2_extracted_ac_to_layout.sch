v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 280 -280 300 -280 {
lab=GND}
N 500 -320 550 -320 {
lab=out}
N 550 -260 550 -240 {
lab=GND}
N 400 -270 400 -250 {
lab=iref}
N 260 -300 260 -240 {
lab=inp}
N 160 -340 160 -280 {
lab=inn}
N 260 -300 300 -300 {
lab=inp}
N 160 -340 300 -340 {
lab=inn}
N 80 -360 300 -360 {
lab=avdd_1v8}
N 360 -270 360 -180 {
lab=#net1}
N 310 -180 360 -180 {
lab=#net1}
C {devices/vsource.sym} 80 -330 0 0 {name=V1 value=1.8 savecurrent=false}
C {devices/gnd.sym} 80 -300 0 0 {name=l1 lab=GND}
C {devices/gnd.sym} 280 -280 0 0 {name=l2 lab=GND}
C {devices/capa.sym} 550 -290 0 0 {name=C1
m=1
value=500f
footprint=1206
device="ceramic capacitor"}
C {devices/gnd.sym} 550 -240 0 0 {name=l3 lab=GND}
C {devices/gnd.sym} 400 -190 0 0 {name=l4 lab=GND}
C {devices/vsource.sym} 160 -250 0 0 {name=V3
value="DC 1"}
C {devices/gnd.sym} 160 -220 0 0 {name=l5 lab=GND}
C {devices/vsource.sym} 260 -210 0 0 {name=V4
value="DC 1 AC 1"
savecurrent=false}
C {devices/gnd.sym} 260 -180 0 0 {name=l6 lab=GND}
C {devices/lab_wire.sym} 540 -320 0 0 {name=p2 sig_type=std_logic lab=out}
C {devices/lab_pin.sym} 270 -340 0 0 {name=p3 sig_type=std_logic lab=inn}
C {devices/lab_pin.sym} 280 -300 0 0 {name=p4 sig_type=std_logic lab=inp}
C {devices/code.sym} 460 -510 0 0 {name=TT_MODELS
only_toplevel=true
format="tcleval( @value )"
value="
** opencircuitdesign pdks isntsall
.lib /opt/pdk/open_pdks/sky130/sky130A/libs.tech/ngspice/sky130.lib.spice tt

"
spice_ignore=false}
C {cm_ota.sym} 300 -260 0 0 {name=X1 w1_2=6.3 w3_4=3.36 w5_6=30.24 w7_8=15.96 w9_10=3.25 nf1_2=1 nf3_4=1 nf5_6=1 nf7_8=1 nf9_10=1 beta=1 }
C {devices/code.sym} 590 -510 0 0 {name=AC only_toplevel=false value="

.temp 27
.option savecurrents
.save all
.control
	ac dec 100 1 1e15
	plot vdb(out) vs frequency
	plot (180*cph(out)/pi) vs frequency
	let phase_vector = 180*cph(out)/pi
	let gain_vector = vdb(out)
	meas ac unity_gain_freq_val when vdb(out)=0
	meas ac dc_gain_val find vdb(out) at=10Hz
	let dc_gain = dc_gain_val
	meas ac p1_val when phase_vector=-45 cross=1
	meas ac p2_val when phase_vector=-135 cross=1
	meas ac three_db when gain_vector=dc_gain_val -3 cross=1
	let p2 = p2_val
	let p1 = p1_val
	let dc_gain = dc_gain_val
	let unity_gain_freq = unity_gain_freq_val	
	op
	write tb_cm_ota_working_v2_extracted_ac.raw
	let gm1 = @m.x1.xm1.msky130_fd_pr__nfet_01v8[gm]
	let gm2 = @m.x1.xm2.msky130_fd_pr__nfet_01v8[gm]
	let gm3 = @m.x1.xm3.msky130_fd_pr__pfet_01v8[gm]
	let gm4 = @m.x1.xm4.msky130_fd_pr__pfet_01v8[gm]
	let gm5 = @m.x1.xm5.msky130_fd_pr__nfet_01v8[gm]
	let gm6 = @m.x1.xm6.msky130_fd_pr__nfet_01v8[gm]
	let gm7 = @m.x1.xm7.msky130_fd_pr__pfet_01v8[gm]
	let gm8 = @m.x1.xm8.msky130_fd_pr__pfet_01v8[gm]

	let id1 = @m.x1.xm1.msky130_fd_pr__nfet_01v8[id]
	let id2 = @m.x1.xm2.msky130_fd_pr__nfet_01v8[id]
	let id3 = @m.x1.xm3.msky130_fd_pr__pfet_01v8[id]
	let id4 = @m.x1.xm4.msky130_fd_pr__pfet_01v8[id]
	let id5 = @m.x1.xm5.msky130_fd_pr__nfet_01v8[id]
	let id6 = @m.x1.xm6.msky130_fd_pr__nfet_01v8[id]
	let id7 = @m.x1.xm7.msky130_fd_pr__pfet_01v8[id]
	let id8 = @m.x1.xm8.msky130_fd_pr__pfet_01v8[id]

	let current_scale = id5/id1
	
	let kgm1 = gm1/id1
	let kgm2 = gm2/id2
	let kgm3 = gm3/id3
	let kgm4 = gm4/id4
	let kgm5 = gm5/id5
	let kgm6 = gm6/id6
	let kgm7 = gm7/id7
	let kgm8 = gm8/id8
	
	print kgm1
	print kgm2
	print kgm3
	print kgm4
	print kgm5
	print kgm6
	print kgm7
	print kgm8

	print id1
	print id2
	print id3
	print id4
	print id5
	print id6
	print id7
	print id8
	
	print current_scale
	print dc_gain_val
	print p1_val
	print p2_val
.endc
"}
C {devices/lab_pin.sym} 400 -260 2 0 {name=p5 sig_type=std_logic lab=iref
}
C {devices/lab_pin.sym} 80 -360 0 0 {name=p6 sig_type=std_logic lab=avdd_1v8}
C {devices/isource.sym} 400 -220 2 0 {name=I1 value=0}
C {devices/isource.sym} 310 -150 0 0 {name=I3 value=69.4u}
C {devices/gnd.sym} 310 -120 0 0 {name=l8 lab=GND}
