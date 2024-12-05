v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 0 -110 0 -80 {
lab=GND}
N 130 -230 130 -170 {
lab=vout_1v8}
N 90 -260 90 -140 {
lab=vin_1v8}
N -60 -110 0 -110 {
lab=GND}
N -0 -200 0 -170 {
lab=vin_1v8}
N 0 -200 90 -200 {
lab=vin_1v8}
N -60 -290 130 -290 {
lab=avdd_1v8}
N -60 -290 -60 -170 {
lab=avdd_1v8}
N 130 -260 150 -260 {
lab=avdd_1v8}
N 150 -290 150 -260 {
lab=avdd_1v8}
N 130 -290 150 -290 {
lab=avdd_1v8}
N 130 -140 150 -140 {
lab=GND}
N 150 -140 150 -110 {
lab=GND}
N 130 -110 150 -110 {
lab=GND}
N -0 -110 130 -110 {
lab=GND}
C {devices/vsource.sym} -60 -140 0 0 {name=V1 value=1.8 savecurrent=false}
C {devices/gnd.sym} 0 -80 0 0 {name=l1 lab=GND}
C {sky130_fd_pr/nfet_01v8.sym} 110 -140 0 0 {name=M1
L=0.15
W=1
nf=1 
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet_01v8.sym} 110 -260 0 0 {name=M2
L=0.15
W=1
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {devices/vsource.sym} 0 -140 0 0 {name=V2 value=0 savecurrent=false}
C {devices/iopin.sym} 30 -290 3 0 {name=p2 lab=avdd_1v8}
C {devices/iopin.sym} 90 -230 2 0 {name=p1 lab=vin_1v8}
C {devices/iopin.sym} 130 -200 2 1 {name=p3 lab=vout_1v8}
C {devices/code.sym} 120 -420 0 0 {name=spice only_toplevel=false value="

.lib /opt/pdk/open_pdks/sky130/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.control
	dc V2 0 1.8 0.01
	plot v(vout_1v8)
.endc

.save all

"}
