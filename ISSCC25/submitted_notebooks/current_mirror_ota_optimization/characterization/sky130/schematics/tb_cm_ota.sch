v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 80 -300 80 -280 {
lab=avss}
N 80 -290 150 -290 {
lab=avss}
N 80 -360 300 -360 {
lab=#net1}
N 280 -280 300 -280 {
lab=GND}
N 500 -320 550 -320 {
lab=out}
N 550 -260 550 -240 {
lab=GND}
N 400 -270 400 -250 {
lab=#net2}
N 170 -340 300 -340 {
lab=inn}
N 170 -340 170 -280 {
lab=inn}
N 240 -300 240 -240 {
lab=inp}
N 240 -300 300 -300 {
lab=inp}
C {devices/vsource.sym} 80 -330 0 0 {name=V1 value=1.8 savecurrent=false}
C {devices/vsource.sym} 80 -250 0 0 {name=V2 value=0 savecurrent=false}
C {devices/lab_pin.sym} 140 -290 0 0 {name=p1 sig_type=std_logic lab=avss}
C {devices/gnd.sym} 80 -220 0 0 {name=l1 lab=GND}
C {devices/gnd.sym} 280 -280 0 0 {name=l2 lab=GND}
C {devices/capa.sym} 550 -290 0 0 {name=C1
m=1
value=50f
footprint=1206
device="ceramic capacitor"}
C {devices/gnd.sym} 550 -240 0 0 {name=l3 lab=GND}
C {devices/gnd.sym} 400 -190 0 0 {name=l4 lab=GND}
C {devices/vsource.sym} 170 -250 0 0 {name=V3
value="0.9 AC 1"}
C {devices/gnd.sym} 170 -220 0 0 {name=l5 lab=GND}
C {devices/vsource.sym} 240 -210 0 0 {name=V4 value=0.9 savecurrent=false}
C {devices/gnd.sym} 240 -180 0 0 {name=l6 lab=GND}
C {devices/lab_wire.sym} 540 -320 0 0 {name=p2 sig_type=std_logic lab=out}
C {devices/lab_pin.sym} 270 -340 0 0 {name=p3 sig_type=std_logic lab=inn}
C {devices/lab_pin.sym} 280 -300 0 0 {name=p4 sig_type=std_logic lab=inp}
C {devices/code.sym} 560 -610 0 0 {name=TT_MODELS
only_toplevel=true
format="tcleval( @value )"
value="
** opencircuitdesign pdks isntsall
//.lib /opt/pdk/open_pdks/sky130/sky130A/libs.tech/ngspice/sky130.lib.spice tt

"
//spice_ignore=false}
C {devices/code_shown.sym} 720 -670 0 0 {name="AC Analysis Broken" only_toplevel=false value="

.temp 27
.ac dec 100 10 100G
.print ac V(out)
.measure ac unity_freq when vdb(out)=0
//.measure ac gain_max MAX vdb(out)
.measure ac pole1_freq when vp(out)=-45 cross=1
.measure ac pole2_freq when vp(out)=-90 cross=1
//.measure ac bandwidth when vdb(out)= '(gain_max - 3)' cross=1
.control
	//run
	//save all
	//ac dec 10 1 1e11
	//settype decibel out
	//setcurplottitle=Loopgain
	//let frequency ac1.frequency
.endc

"}
C {cm_ota.sym} 300 -260 0 0 {name=X1 w1_2=1.00 w3_4=1.00 w5_6=1.00 w7_8=1.00}
C {devices/code.sym} 710 -140 0 0 {name="AC Analysis" only_toplevel=false value="
.lib /opt/pdk/open_pdks/sky130/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.temp 27
.option savecurrents
.save all
.ac dec 100 1 100e15
.print ac V(out)
.measure ac gbw when vdb(out)=0
.measure ac dc_gain find vdb(out) at=10
.measure ac pole1_freq when 180*cph(out)/pi=-45 cross=1
.measure ac pole2_freq when 180*cph(out)/pi cross=1
//.measure ac bandwidth when vdb(out)= '(dc_gain - 3)' cross=1
.control
	// run //v1
	// set hcopyscolor=1 //v1
	run
	plot vdb(out) vs frequency
	plot 180*cph(out)/pi vs frequency
	opran 0 0 0 10n 10u 0
	op
	write tb_cm_ota.raw
	echo 'GBWP = ' gbw
	echo 'DC Gain = ' dc_gain
	echo 'pole1 freq = ' pole1_freq
	echo 'pole2 freq = ' pole2_freq
	echo '3dB BW = ' bandwidth
.endc
"}
C {devices/isource.sym} 400 -220 2 0 {name=I2 value=47.4685u}
