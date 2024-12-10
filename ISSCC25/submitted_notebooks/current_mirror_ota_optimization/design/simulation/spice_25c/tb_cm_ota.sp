
.include ./design/simulation/spice_-25c/cm_ota_params.sp


V1 avdd_1v8_ext GND 1.8
C1 out_ext GND 4p m=1
V3 inn_ext GND DC 1
V4 inp_ext GND DC 1 AC 1
X1 iref_ext out_ext inn_ext inp_ext GND avdd_1v8_ext cm_ota_extracted
I1 GND iref_ext {iref_post_layout}


V11 vdd GND 1.8
C11 out GND 4p m=1
V31 inn GND DC 1
V41 inp GND DC 1 AC 1
X11 vdd out inp inn itail GND cm_ota w1_2={w1_2} w3_4={w3_4} w5_6={w5_6}
									+w7_8={w7_8} w9_10={w9_10} beta={beta} 
									+ nf1_2={nf1_2} nf3_4={nf3_4} nf5_6={nf5_6}
									+nf7_8={nf7_8} nf9_10={nf9_10}
I31 GND itail {iref_ideal}


.lib $PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.temp 25

.save all
.save v(out_ext) v(out)
.save ph(v(out)) ph(v(out_ext))
.control
	ac dec 100 1 1e15
	set filetype=ascii

	* Write and plot AC analysis results
	wrdata ac_output_ext.txt frequency vdb(out_ext) cph(out_ext)
	wrdata ac_output.txt frequency vdb(out) cph(out)
	plot vdb(out) vdb(out_ext)vs frequency
	plot (180*cph(out)/pi) (180*cph(out_ext)/pi)vs frequency
	
	* Measure Gain, unity-gain frequency and phase at gbw

	let phase_vector_ext = 180*cph(out_ext)/pi
	let gain_vector_ext = vdb(out_ext)
	
	meas ac unity_gain_freq_ext when vdb(out_ext)=0
	meas ac unity_gain_freq_ideal when vdb(out)=0

	meas ac dc_gain_ext find vdb(out_ext) at=10Hz
	meas ac dc_gain_ideal find vdb(out) at=10Hz

	let dc_gain = dc_gain_ext
	
	meas ac phase_at_unity_ext find ph(v(out_ext) at=unity_gain_freq_ext
	meas ac phase_at_unity_ideal find ph(v(out)) at=unity_gain_freq_ideal

	* Convert phase from radians to degrees
	let phase_deg_at_unity_ext = 180 * phase_at_unity_ext / pi
	let phase_deg_at_unity_ideal = 180 * phase_at_unity_ideal / pi

	
	* Calculate phase margin
	let phase_margin_ext = 180 + phase_deg_at_unity_ext
	let phase_margin_ideal = 180 + phase_deg_at_unity_ideal

	print phase_margin_ext
	print phase_margin_ideal

	meas ac p1_val_ext when phase_vector_ext=-45 cross=1
	meas ac p2_val_ext when phase_vector_ext=-135 cross=1
	
	meas ac p1_val when phase_vector_ideal=-45 cross=1
	meas ac p2_val when phase_vector_ideal=-135 cross=1
	
	let phase_vector_ideal = 180*cph(out)/pi
	let gain_vector_ideal = vdb(out)
	
	meas ac dc_gain_ideal find vdb(out) at=10Hz
	let dc_gain = dc_gain_ideal


	*write tb_cm_ota_working_v2_extracted.raw
	// set hcopyscolor=1 //v1
	*echo 'GBWP = ' gbw
	*echo 'DC Gain = ' dc_gain
	*echo 'pole1 freq = ' pole1_freq
	*echo 'pole2 freq = ' pole2_freq
	*echo '3dB BW = ' bandwidth


	op
	let gm1 = @m.x11.xm1.msky130_fd_pr__nfet_01v8[gm]
	let gm2 = @m.x11.xm2.msky130_fd_pr__nfet_01v8[gm]
	let gm3 = @m.x11.xm3.msky130_fd_pr__pfet_01v8[gm]
	let gm4 = @m.x11.xm4.msky130_fd_pr__pfet_01v8[gm]
	let gm5 = @m.x11.xm5.msky130_fd_pr__nfet_01v8[gm]
	let gm6 = @m.x11.xm6.msky130_fd_pr__nfet_01v8[gm]
	let gm7 = @m.x11.xm7.msky130_fd_pr__pfet_01v8[gm]
	let gm8 = @m.x11.xm8.msky130_fd_pr__pfet_01v8[gm]

	let id1 = @m.x11.xm1.msky130_fd_pr__nfet_01v8[id]
	let id2 = @m.x11.xm2.msky130_fd_pr__nfet_01v8[id]
	let id3 = @m.x11.xm3.msky130_fd_pr__pfet_01v8[id]
	let id4 = @m.x11.xm4.msky130_fd_pr__pfet_01v8[id]
	let id5 = @m.x11.xm5.msky130_fd_pr__nfet_01v8[id]
	let id6 = @m.x11.xm6.msky130_fd_pr__nfet_01v8[id]
	let id7 = @m.x11.xm7.msky130_fd_pr__pfet_01v8[id]
	let id8 = @m.x11.xm8.msky130_fd_pr__pfet_01v8[id]

	let cgg1 = @m.x11.xm1.msky130_fd_pr__nfet_01v8[cgg]
	let cgg4 = @m.x11.xm4.msky130_fd_pr__pfet_01v8[cgg]
	let cgg6 = @m.x11.xm6.msky130_fd_pr__nfet_01v8[cgg]
	let cgg8 = @m.x11.xm8.msky130_fd_pr__pfet_01v8[cgg]

	let current_scale = id5/id1
	
	let kgm1 = gm1/id1
	let kgm2 = gm2/id2
	let kgm3 = gm3/id3
	let kgm4 = gm4/id4
	let kgm5 = gm5/id5
	let kgm6 = gm6/id6
	let kgm7 = gm7/id7
	let kgm8 = gm8/id8

	let kcgg1 = cgg1/id1
	let kcgg4 = cgg4/id4
	let kcgg6 = cgg6/id6
	let kcgg8 = cgg8/id8
	
	let kco = kcgg6 + kcgg8
	let current_consumption = id2 + id6

	let vds4 = @m.x11.xm4.msky130_fd_pr__pfet_01v8[vds]
	let vds8 = @m.x11.xm8.msky130_fd_pr__pfet_01v8[vds]

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

	print kcgg1
	print kcgg4
	print kcgg6
	print kcgg8
	print kco
	print current_consumption
	print vds4
	print vds8
	
	*print current_scale
	*print dc_gain_val
	*print p1_val
	*print p2_val

.endc


.include ./design/simulation/spice_-25c/cm_ota_schematic.sp
.include ./design/simulation/spice_-25c/cm_ota_extracted.sp

.GLOBAL GND
.end
