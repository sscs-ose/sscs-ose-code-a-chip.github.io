v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 630 -360 630 -340 {
lab=d}
N 510 -190 510 -160 {
lab=GND}
N 820 -190 820 -160 {
lab=GND}
N 730 -190 730 -160 {
lab=GND}
N 630 -280 630 -250 {
lab=GND}
N 730 -310 730 -250 {
lab=b}
N 510 -310 510 -250 {
lab=g}
N 510 -310 590 -310 {
lab=g}
N 630 -310 730 -310 {
lab=b}
N 630 -360 820 -360 {
lab=d}
N 820 -360 820 -250 {
lab=d}
N 630 -250 630 -160 {
lab=GND}
N 900 -190 900 -160 {
lab=GND}
N 900 -290 900 -250 {
lab=n}
C {devices/gnd.sym} 630 -160 0 0 {name=l1 lab=GND}
C {devices/vsource.sym} 510 -220 0 0 {name=vg value="DC 0.9 AC 1" savecurrent=false}
C {devices/gnd.sym} 510 -160 0 0 {name=l3 lab=GND}
C {devices/vsource.sym} 820 -220 0 0 {name=vd value=0.9 savecurrent=false}
C {devices/gnd.sym} 820 -160 0 0 {name=l2 lab=GND}
C {devices/vsource.sym} 730 -220 0 1 {name=vb value=0 savecurrent=false}
C {devices/lab_wire.sym} 560 -310 0 0 {name=p1 sig_type=std_logic lab=g}
C {devices/lab_wire.sym} 730 -360 0 0 {name=p2 sig_type=std_logic lab=d}
C {devices/lab_wire.sym} 730 -310 0 0 {name=p3 sig_type=std_logic lab=b}
C {devices/code_shown.sym} 0 -880 0 0 {name=COMMANDS1 only_toplevel=false
value="
.param wx=5 lx=0.15
.noise v(n) vg lin 1 1 1 1

.control
option numdgt = 3
set wr_singlescale
set wr_vecnames

compose l_vec  values 0.15 0.16 0.17 0.18 0.19
+ 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1 2 3
compose vg_vec start= 0 stop=1.8  step=25m
compose vd_vec start= 0 stop=1.8  step=25m
compose vb_vec start= 0 stop=-0.4 step=-0.2

foreach var1 $&l_vec
  alterparam lx=$var1
  reset
  foreach var2 $&vg_vec
    alter vg $var2
    foreach var3 $&vd_vec
      alter vd $var3
      foreach var4 $&vb_vec
        alter vb $var4
        run
        wrdata techsweep_nfet_01v8.txt noise1.all
        destroy all
        set appendwrite
        unset set wr_vecnames  
      end
    end 
  end
end
unset appendwrite

alterparam lx=0.15
reset
op
show
write techsweep_nfet_01v8.raw
.endc
"}
C {sky130_fd_pr/corner.sym} 1060 -750 0 0 {name=CORNER only_toplevel=true corner=tt}
C {devices/title.sym} 160 -40 0 0 {name=l5 author="Boris Murmann"}
C {devices/ngspice_get_value.sym} 1010 -290 0 0 {name=r1 node=v(@m.xm1.msky130_fd_pr__nfet_01v8[vth])
descr="Vt="}
C {devices/launcher.sym} 940 -410 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/techsweep_nfet_01v8.raw; set show_hidden_texts 1; xschem annotate_op"}
C {devices/launcher.sym} 940 -450 0 0 {name=h3
descr="save, netlist & simulate"
tclcommand="xschem save; xschem netlist; xschem simulate"}
C {devices/ngspice_get_value.sym} 1010 -250 0 0 {name=r2 node=@m.xm1.msky130_fd_pr__nfet_01v8[cgg]
descr="cgg="}
C {devices/ngspice_get_expr.sym} 1120 -210 0 0 {name=r4 
node="[format %.4g [expr [ngspice::get_node \{@m.xm1.msky130_fd_pr__nfet_01v8[gm]\}] / [ngspice::get_node \{@m.xm1.msky130_fd_pr__nfet_01v8[gds]\}]]]"
descr="gm/gds="}
C {devices/ngspice_get_value.sym} 1010 -210 0 0 {name=r3 node=@m.xm1.msky130_fd_pr__nfet_01v8[capbd]
descr="capdb="}
C {devices/ngspice_get_value.sym} 1010 -170 0 0 {name=r5 node=@m.xm1.msky130_fd_pr__nfet_01v8[capbs]
descr="capbs="}
C {devices/ngspice_get_expr.sym} 1120 -250 0 0 {name=r6 
node="[format %.4g [expr [ngspice::get_node \{@m.xm1.msky130_fd_pr__nfet_01v8[gm]\}] / [ngspice::get_node \{@m.xm1.msky130_fd_pr__nfet_01v8[cgg]\}] / 6.283]]"
descr="fT="}
C {devices/ngspice_get_expr.sym} 1120 -290 0 0 {name=r7 
node="[format %.4g [expr [ngspice::get_node \{@m.xm1.msky130_fd_pr__nfet_01v8[gm]\}] / [ngspice::get_node \{i(@m.xm1.msky130_fd_pr__nfet_01v8[id])\}]]]"
descr="gm/ID="}
C {devices/code_shown.sym} 530 -880 0 0 {name=COMMANDS2 only_toplevel=false
value="
.save @m.xm1.msky130_fd_pr__nfet_01v8[capbd]
.save @m.xm1.msky130_fd_pr__nfet_01v8[capbs]
.save @m.xm1.msky130_fd_pr__nfet_01v8[cdd]
.save @m.xm1.msky130_fd_pr__nfet_01v8[cgb]
.save @m.xm1.msky130_fd_pr__nfet_01v8[cgd]
.save @m.xm1.msky130_fd_pr__nfet_01v8[cgg]
.save @m.xm1.msky130_fd_pr__nfet_01v8[cgs]
.save @m.xm1.msky130_fd_pr__nfet_01v8[css]
.save @m.xm1.msky130_fd_pr__nfet_01v8[gds] 
.save @m.xm1.msky130_fd_pr__nfet_01v8[gm] 
.save @m.xm1.msky130_fd_pr__nfet_01v8[gmbs] 
.save @m.xm1.msky130_fd_pr__nfet_01v8[id]
.save @m.xm1.msky130_fd_pr__nfet_01v8[l]
.save @m.xm1.msky130_fd_pr__nfet_01v8[vbs]
.save @m.xm1.msky130_fd_pr__nfet_01v8[vds]
.save @m.xm1.msky130_fd_pr__nfet_01v8[vgs]
.save @m.xm1.msky130_fd_pr__nfet_01v8[vth]
.save onoise.m.xm1.msky130_fd_pr__nfet_01v8.id
.save onoise.m.xm1.msky130_fd_pr__nfet_01v8.1overf
.save g d b n
"}
C {devices/gnd.sym} 730 -160 0 0 {name=l4 lab=GND}
C {devices/ccvs.sym} 900 -220 0 0 {name=Hn vnam=vd value=1}
C {devices/gnd.sym} 900 -160 0 0 {name=l6 lab=GND}
C {devices/lab_wire.sym} 900 -290 0 0 {name=p4 sig_type=std_logic lab=n}
C {sky130_fd_pr/nfet_01v8.sym} 610 -310 0 0 {name=M1
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
model=nfet_01v8
spiceprefix=X
}
