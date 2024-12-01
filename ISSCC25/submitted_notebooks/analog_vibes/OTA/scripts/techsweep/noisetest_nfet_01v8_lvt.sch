v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
B 2 900 -710 1360 -190 {flags=graph
y1=-14
y2=-7.1
ypos1=0
ypos2=2
divy=5
subdivy=8
unity=1
x1=0
x2=11
divx=5
subdivx=8
xlabmag=1.0
ylabmag=1.0
node="\\"total; onoise_spectrum\\"
\\"1/f; onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.1overf\\"
\\"id_thermal; onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.id\\""
color="4 10 5"
dataset=-1
unitx=1
logx=1
logy=1
rainbow=0}
T {tcleval(
gm = [to_eng [xschem raw value \\@m.xm1.msky130_fd_pr__nfet_01v8_lvt\\\\[gm\\\\]  0]]
ID = [to_eng [xschem raw value i(\\@m.xm1.msky130_fd_pr__nfet_01v8_lvt\\\\[id\\\\])  0]]
gm/ID = [to_eng [xschem raw value \\@m.xm1.msky130_fd_pr__nfet_01v8_lvt\\\\[gm\\\\]  0]/[xschem raw value i(\\@m.xm1.msky130_fd_pr__nfet_01v8_lvt\\\\[id\\\\])  0]]
id_thermal =[to_eng [xschem raw value onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.id 0] ]
gamma = [to_eng [expr [xschem raw value onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.id 0]**2/[xschem raw value \\@m.xm1.msky130_fd_pr__nfet_01v8_lvt\\\\[gm\\\\] 0]/4/1.38e-23/300 ]]
)} 610 -550 0 0 0.3 0.3 {floater=1}
N 510 -330 510 -310 {
lab=d}
N 390 -160 390 -130 {
lab=GND}
N 700 -160 700 -130 {
lab=GND}
N 610 -160 610 -130 {
lab=GND}
N 510 -250 510 -220 {
lab=GND}
N 610 -280 610 -220 {
lab=b}
N 390 -280 390 -220 {
lab=g}
N 390 -280 470 -280 {
lab=g}
N 510 -280 610 -280 {
lab=b}
N 510 -330 700 -330 {
lab=d}
N 700 -330 700 -220 {
lab=d}
N 510 -220 510 -130 {
lab=GND}
N 780 -160 780 -130 {
lab=GND}
N 780 -260 780 -220 {
lab=n}
C {devices/gnd.sym} 510 -130 0 0 {name=l1 lab=GND}
C {devices/vsource.sym} 390 -190 0 0 {name=vg value="DC 0.75 AC 1" savecurrent=false}
C {devices/gnd.sym} 390 -130 0 0 {name=l3 lab=GND}
C {devices/vsource.sym} 700 -190 0 0 {name=vd value=0.9 savecurrent=false}
C {devices/gnd.sym} 700 -130 0 0 {name=l2 lab=GND}
C {devices/vsource.sym} 610 -190 2 1 {name=vsb value=\{vbx\} savecurrent=false}
C {devices/lab_wire.sym} 440 -280 0 0 {name=p1 sig_type=std_logic lab=g}
C {devices/lab_wire.sym} 610 -330 0 0 {name=p2 sig_type=std_logic lab=d}
C {devices/lab_wire.sym} 610 -280 0 0 {name=p3 sig_type=std_logic lab=b}
C {devices/code_shown.sym} 20 -670 0 0 {name=COMMANDS1 only_toplevel=false
value="
.param wx=5 lx=0.15 vbx=0
.save all
.save @m.xm1.msky130_fd_pr__nfet_01v8_lvt[gm]
.save @m.xm1.msky130_fd_pr__nfet_01v8_lvt[id]

.control
set wr_vecnames
noise v(n) vg dec 10 1 1e11 1
noise v(n) vg lin  1 1 1 1
echo $plots
write noisetest_nfet_01v8_lvt.raw noise1.all

setplot noise3
print onoise_spectrum
print onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.1overf
print onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.id
.endc
"}
C {sky130_fd_pr/corner.sym} 120 -270 0 0 {name=CORNER only_toplevel=true corner=tt}
C {sky130_fd_pr/nfet_01v8_lvt.sym} 490 -280 0 0 {name=M1
L=\{lx\}
W=\{wx\}
nf=1
mult=1
ad="'int((nf+1)/2) * W/nf * 0.29'" 
pd="'2*int((nf+1)/2) * (W/nf + 0.29)'"
as="'int((nf+2)/2) * W/nf * 0.29'" 
ps="'2*int((nf+2)/2) * (W/nf + 0.29)'"
nrd="'0.29 / W'" nrs="'0.29 / W'"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {devices/title.sym} 160 -40 0 0 {name=l5 author="Boris Murmann"}
C {devices/launcher.sym} 620 -670 0 0 {name=h3
descr="save, netlist & simulate"
tclcommand="xschem save; xschem netlist; xschem simulate"
value="
.param wx=5 lx=0.15 vbx=0
.save all
.save @m.xm1.msky130_fd_pr__nfet_01v8_lvt[gm]
.save @m.xm1.msky130_fd_pr__nfet_01v8_lvt[id]

.control
noise v(n) vg dec 10 1 1e11 1
dc vg 0.5 1 0.5
noise v(n) vg lin  1 1 1 1
echo $plots
*write noisetest_nfet_01v8_lvt.raw noise1.all
write noisetest_nfet_01v8_lvt.raw dc2.all noise1.all
wrdata noisetest_nfet_01v8_lvt.txt dc2.all noise1.all

setplot noise3
print onoise_spectrum
print onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.1overf
print onoise.m.xm1.msky130_fd_pr__nfet_01v8_lvt.id
.endc
"}
C {devices/gnd.sym} 610 -130 0 0 {name=l4 lab=GND}
C {devices/ccvs.sym} 780 -190 0 0 {name=Hn vnam=vd value=1}
C {devices/gnd.sym} 780 -130 0 0 {name=l6 lab=GND}
C {devices/lab_wire.sym} 780 -260 0 0 {name=p4 sig_type=std_logic lab=n}
C {devices/launcher.sym} 620 -630 0 0 {name=h27
descr="load noise" 
tclcommand="
xschem raw_read $netlist_dir/[file tail [file rootname [xschem get current_name]]].raw noise; set show_hidden_texts 1 

"
}
