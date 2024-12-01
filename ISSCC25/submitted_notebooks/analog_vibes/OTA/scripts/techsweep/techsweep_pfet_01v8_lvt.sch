v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 880 -220 880 -190 {
lab=n}
N 620 -250 620 -230 {
lab=GND}
N 620 -170 620 -140 {
lab=d}
N 500 -200 580 -200 {
lab=g}
N 500 -240 500 -200 {
lab=g}
N 500 -320 500 -300 {
lab=GND}
N 500 -320 620 -320 {
lab=GND}
N 620 -320 620 -250 {
lab=GND}
N 620 -320 710 -320 {
lab=GND}
N 710 -320 710 -300 {
lab=GND}
N 710 -240 710 -200 {
lab=b}
N 620 -200 710 -200 {
lab=b}
N 710 -320 800 -320 {
lab=GND}
N 800 -320 800 -300 {
lab=GND}
N 800 -240 800 -140 {
lab=d}
N 620 -140 800 -140 {
lab=d}
N 500 -340 500 -320 {
lab=GND}
N 800 -320 880 -320 {
lab=GND}
N 880 -320 880 -300 {
lab=GND}
N 880 -300 880 -280 {
lab=GND}
C {devices/code_shown.sym} 0 -880 0 0 {name=COMMANDS1 only_toplevel=false
value="
.param wx=5 lx=0.35
.noise v(n) vg lin 1 1 1 1

.control
option numdgt = 3
set wr_singlescale
set wr_vecnames

compose l_vec  values 0.35 0.36 0.37 0.38 0.39
+ 0.4 0.5 0.6 0.7 0.8 0.9 1 2 3
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
        wrdata techsweep_pfet_01v8_lvt.txt noise1.all
        destroy all
        set appendwrite
        unset set wr_vecnames  
      end
    end 
  end
end
unset appendwrite

alterparam lx=0.35
reset
op
show
write techsweep_pfet_01v8_lvt.raw
.endc
"}
C {sky130_fd_pr/corner.sym} 1060 -750 0 0 {name=CORNER only_toplevel=true corner=tt}
C {devices/title.sym} 160 -40 0 0 {name=l5 author="Boris Murmann"}
C {devices/ngspice_get_value.sym} 1010 -290 0 0 {name=r1 node=v(@m.xm1.msky130_fd_pr__pfet_01v8_lvt[vth])
descr="Vt="}
C {devices/launcher.sym} 940 -410 0 0 {name=h1
descr="load op & annotate" 
tclcommand="xschem raw_read $netlist_dir/techsweep_pfet_01v8_lvt.raw; set show_hidden_texts 1; xschem annotate_op"}
C {devices/launcher.sym} 940 -450 0 0 {name=h3
descr="save, netlist & simulate"
tclcommand="xschem save; xschem netlist; xschem simulate"}
C {devices/ngspice_get_value.sym} 1010 -250 0 0 {name=r2 node=@m.xm1.msky130_fd_pr__pfet_01v8_lvt[cgg]
descr="cgg="}
C {devices/ngspice_get_expr.sym} 1120 -210 0 0 {name=r4 
node="[format %.4g [expr [ngspice::get_node \{@m.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]\}] / [ngspice::get_node \{@m.xm1.msky130_fd_pr__pfet_01v8_lvt[gds]\}]]]"
descr="gm/gds="}
C {devices/ngspice_get_value.sym} 1010 -210 0 0 {name=r3 node=@m.xm1.msky130_fd_pr__pfet_01v8_lvt[capbd]
descr="capdb="}
C {devices/ngspice_get_value.sym} 1010 -170 0 0 {name=r5 node=@m.xm1.msky130_fd_pr__pfet_01v8_lvt[capbs]
descr="capbs="}
C {devices/ngspice_get_expr.sym} 1120 -250 0 0 {name=r6 
node="[format %.4g [expr [ngspice::get_node \{@m.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]\}] / [ngspice::get_node \{@m.xm1.msky130_fd_pr__pfet_01v8_lvt[cgg]\}] / 6.283]]"
descr="fT="}
C {devices/ngspice_get_expr.sym} 1120 -290 0 0 {name=r7 
node="[format %.4g [expr [ngspice::get_node \{@m.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]\}] / [ngspice::get_node \{i(@m.xm1.msky130_fd_pr__pfet_01v8_lvt[id])\}]]]"
descr="gm/ID="}
C {devices/code_shown.sym} 530 -880 0 0 {name=COMMANDS2 only_toplevel=false
value="
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[capbd]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[capbs]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[cdd]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[cgb]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[cgd]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[cgg]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[cgs]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[css]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[gds] 
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[gm] 
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[gmbs] 
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[id]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[l]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[vbs]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[vds]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[vgs]
.save @m.xm1.msky130_fd_pr__pfet_01v8_lvt[vth]
.save onoise.m.xm1.msky130_fd_pr__pfet_01v8_lvt.id
.save onoise.m.xm1.msky130_fd_pr__pfet_01v8_lvt.1overf
.save g d b n
"}
C {devices/ccvs.sym} 880 -250 0 0 {name=Hn vnam=vd value=1}
C {devices/lab_wire.sym} 880 -190 0 0 {name=p4 sig_type=std_logic lab=n}
C {devices/vsource.sym} 500 -270 0 0 {name=vg value="DC 0.9 AC 1" savecurrent=false}
C {devices/gnd.sym} 500 -340 2 0 {name=l3 lab=GND}
C {devices/vsource.sym} 800 -270 0 0 {name=vd value=0.9 savecurrent=false}
C {devices/lab_wire.sym} 710 -200 0 0 {name=p2 sig_type=std_logic lab=b}
C {devices/lab_wire.sym} 710 -140 0 0 {name=p3 sig_type=std_logic lab=d}
C {devices/lab_wire.sym} 530 -200 0 0 {name=p1 sig_type=std_logic lab=g}
C {sky130_fd_pr/pfet_01v8_lvt.sym} 600 -200 0 0 {name=M1
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
model=pfet_01v8_lvt
spiceprefix=X
}
C {devices/vsource.sym} 710 -270 0 0 {name=vb value="0" savecurrent=false}
