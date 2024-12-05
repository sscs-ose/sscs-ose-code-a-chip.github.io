v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 100 -100 100 -70 {
lab=npdrain}
N 100 -100 140 -100 {
lab=npdrain}
N 100 -230 100 -200 {
lab=npdrain}
N 100 -200 140 -200 {
lab=npdrain}
N 140 -200 140 -180 {
lab=npdrain}
N 140 -120 140 -100 {
lab=npdrain}
N 140 -230 150 -230 {
lab=psource}
N 150 -260 150 -230 {
lab=psource}
N 140 -260 150 -260 {
lab=psource}
N 140 -70 150 -70 {
lab=GND}
N 150 -70 150 -40 {
lab=GND}
N 140 -40 150 -40 {
lab=GND}
N 70 -120 70 -40 {
lab=GND}
N 70 -40 140 -40 {
lab=GND}
N 70 -260 70 -180 {
lab=psource}
N 70 -260 140 -260 {
lab=psource}
N 140 -180 140 -120 {
lab=npdrain}
C {sky130_fd_pr/pfet_01v8.sym} 120 -230 0 0 {name=mp
L=length_p
W=width_p
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=x
}
C {devices/isource.sym} 70 -150 2 1 {name=I0 value=1m}
C {devices/gnd.sym} 110 -40 0 0 {name=l1 lab=GND}
C {devices/code.sym} 230 -340 0 0 {name=spice only_toplevel=false value="

* geometry parameters
.param width_p = 1
.param width_n = 1
.param length_p = 0.15
.param length_n = 0.15
.param l = 0.15
.param w = 1

* sweep parameters
* .param start = 1u
* .param stop = 1m
* .param points_per_decade 25

.temp 27

.lib /opt/pdk/open_pdks/sky130/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.control

let start = 1n
let stop = 1m
let points_per_decade = 20

let stop_start_ratio = stop/start
let num_decades = log10(stop_start_ratio)

echo Stop/Start Ratio $&stop_start_ratio
echo Characterizing $&num_decades decades from $&start to $&stop
echo Simulating $&points_per_decade points per decade
echo  

let i_start = start
let i_end = i_start*10
let i_step = i_end/points_per_decade
let i_end = i_end - i_step


* let length_n_counter = length_n
* let length_p_counter = length_p

set pl = 0.15
set nl = 0.15

* Iterate for 10 different transistor lengths
set lengths = 10
let i = 0
let length_increment = 0.15
set appendwrite 

echo ' isweep  gm  i_id  id  i_cgg  cgg  i_cgs  cgs  i_cgd  cgd  i_cds  cds  i_css  css  i_cdd  cdd  i_gds  gds  i_vth  vth  i_vdsat  vdsat  i_vgs  vgs  i_vds  vds  i_rds  rds  i_wt  wt  i_ft  ft  i_gm_id  gm_id' > nfet_cid_characterization.csv
echo ' isweep  gm  i_id  id  i_cgg  cgg  i_cgs  cgs  i_cgd  cgd  i_cds  cds  i_css  css  i_cdd  cdd  i_gds  gds  i_vth  vth  i_vdsat  vdsat  i_vgs  vgs  i_vds  vds  i_rds  rds  i_wt  wt  i_ft  ft  i_gm_id  gm_id' > pfet_cid_characterization.csv


while i < num_decades

	set filetype=ascii
	set hcopydevtype=svg
	set format = cross
	save @m.xmn.msky130_fd_pr__nfet_01v8[gm]
	save @m.xmn.msky130_fd_pr__nfet_01v8[id]
	save @m.xmn.msky130_fd_pr__nfet_01v8[cgg]
	save @m.xmn.msky130_fd_pr__nfet_01v8[cgs]
	save @m.xmn.msky130_fd_pr__nfet_01v8[cgd]
	save @m.xmn.msky130_fd_pr__nfet_01v8[cds]
	save @m.xmn.msky130_fd_pr__nfet_01v8[css]
	save @m.xmn.msky130_fd_pr__nfet_01v8[cdd]
	save @m.xmn.msky130_fd_pr__nfet_01v8[gds]
	save @m.xmn.msky130_fd_pr__nfet_01v8[vth]
	save @m.xmn.msky130_fd_pr__nfet_01v8[vdsat]
	save @m.xmn.msky130_fd_pr__nfet_01v8[vgs]
	save @m.xmn.msky130_fd_pr__nfet_01v8[vds]

	save @m.xmp.msky130_fd_pr__pfet_01v8[gm]
	save @m.xmp.msky130_fd_pr__pfet_01v8[id]
	save @m.xmp.msky130_fd_pr__pfet_01v8[cgg]
	save @m.xmp.msky130_fd_pr__pfet_01v8[cgs]
	save @m.xmp.msky130_fd_pr__pfet_01v8[cgd]
	save @m.xmp.msky130_fd_pr__pfet_01v8[cds]
	save @m.xmp.msky130_fd_pr__pfet_01v8[css]
	save @m.xmp.msky130_fd_pr__pfet_01v8[cdd]
	save @m.xmp.msky130_fd_pr__pfet_01v8[gds]
	save @m.xmp.msky130_fd_pr__pfet_01v8[vth]
	save @m.xmp.msky130_fd_pr__pfet_01v8[vdsat]
	save @m.xmp.msky130_fd_pr__pfet_01v8[vgs]
	save @m.xmp.msky130_fd_pr__pfet_01v8[vds]

	let step_size = (stop/start)
	echo Simulating rom $&i_start to $&i_end with step size of $&i_step
	dc I0 $&i_start $&i_end $&i_step

	* Note let is for vectors and set is for scalars

	let n_gm = @m.xmn.msky130_fd_pr__nfet_01v8[gm]
	let n_id = @m.xmn.msky130_fd_pr__nfet_01v8[id]
	let n_cgg = @m.xmn.msky130_fd_pr__nfet_01v8[cgg]
	let n_cgs = @m.xmn.msky130_fd_pr__nfet_01v8[cgs]
	let n_cgd = @m.xmn.msky130_fd_pr__nfet_01v8[cgd]
	let n_cds = @m.xmn.msky130_fd_pr__nfet_01v8[cds]
	let n_css = @m.xmn.msky130_fd_pr__nfet_01v8[css]
	let n_cdd = @m.xmn.msky130_fd_pr__nfet_01v8[cdd]
	let n_gds = @m.xmn.msky130_fd_pr__nfet_01v8[gds]
	let n_vth = @m.xmn.msky130_fd_pr__nfet_01v8[vth]
	let n_vdsat = @m.xmn.msky130_fd_pr__nfet_01v8[vdsat]
	let n_vgs = @m.xmn.msky130_fd_pr__nfet_01v8[vgs]
	let n_vds = @m.xmn.msky130_fd_pr__nfet_01v8[vds]

	let p_gm = @m.xmp.msky130_fd_pr__pfet_01v8[gm]
	let p_id = @m.xmp.msky130_fd_pr__pfet_01v8[id]
	let p_cgg = @m.xmp.msky130_fd_pr__pfet_01v8[cgg]
	let p_cgs = @m.xmp.msky130_fd_pr__pfet_01v8[cgs]
	let p_cgd = @m.xmp.msky130_fd_pr__pfet_01v8[cgd]
	let p_cds = @m.xmp.msky130_fd_pr__pfet_01v8[cds]
	let p_css = @m.xmp.msky130_fd_pr__pfet_01v8[css]
	let p_cdd = @m.xmp.msky130_fd_pr__pfet_01v8[cdd]
	let p_gds = @m.xmp.msky130_fd_pr__pfet_01v8[gds]
	let p_vth = @m.xmp.msky130_fd_pr__pfet_01v8[vth]
	let p_vdsat = @m.xmp.msky130_fd_pr__pfet_01v8[vdsat]
	let p_vgs = @m.xmp.msky130_fd_pr__pfet_01v8[vgs]
	let p_vds = @m.xmp.msky130_fd_pr__pfet_01v8[vds]

	let n_rds = 1/n_gds
	let n_wt = n_gm/n_cgg
	let n_ft = n_wt/(2*pi)
	let n_gm_id = n_gm/n_id

	let p_rds = 1/p_gds
	let p_wt = p_gm/p_cgg
	let p_ft = p_wt/(2*pi)
	let p_gm_id = p_gm/p_id


	* write writes the outputs with information - use wrdata instead
	* write nfet_cid_characterization.txt n_gm n_id n_cgg n_cgs n_cgd n_cds n_css n_cdd n_gds n_vth n_vdsat n_vgs n_vds n_rds n_wt n_ft n_gm_id 
	* write pfet_cid_characterization.txt p_gm p_id p_cgg p_cgs p_cgd p_cds p_css p_cdd p_gds p_vth p_vdsat p_vgs p_vds p_rds p_wt p_ft p_gm_id 

	wrdata nfet_cid_characterization.csv n_gm n_id n_cgg n_cgs n_cgd n_cds n_css n_cdd n_gds n_vth n_vdsat n_vgs n_vds n_rds n_wt n_ft n_gm_id
	wrdata pfet_cid_characterization.csv p_gm p_id p_cgg p_cgs p_cgd p_cds p_css p_cdd p_gds p_vth p_vdsat p_vgs p_vds p_rds p_wt p_ft p_gm_id

	* print n_gm n_id n_cgg n_cgs n_cgd n_cds n_css n_cdd n_gds n_vth n_vdsat n_vgs n_vds n_rds n_wt n_ft n_gm_id >> nfet_cid_characterization.csv
	* alterparam length_p = pl
	* alterparam length_n = nl
	let i_start = i_start*10
	let i_end = i_start*10
	let i_step = i_end/points_per_decade
	let i_end = i_end - i_step
	let i = i + 1 
end

* plot ft_n vs gm_id_n ylog


.endc


.save all

"}
C {devices/lab_pin.sym} 70 -260 0 0 {name=p1 sig_type=std_logic lab=psource
}
C {devices/lab_pin.sym} 140 -160 0 1 {name=p2 sig_type=std_logic lab=npdrain}
C {sky130_fd_pr/nfet_01v8.sym} 120 -70 0 0 {name=mn
L=length_n
W=width_n
nf=1 
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=x
}
