v {xschem version=3.1.0 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/vsource.sym} -240 -280 0 0 {name=V1 net_name=true value="'VDD' pwl 0us 0 5us 'VDD'"}
C {devices/vdd.sym} -240 -310 0 0 {name=l8 lab=VDD}
C {devices/gnd.sym} -240 -250 0 0 {name=l9 lab=GND}
C {devices/gnd.sym} 220 -150 0 0 {name=l1 lab=GND}
C {devices/lab_pin.sym} 290 -200 0 1 {name=l3 lab=vbg}
C {devices/code_shown.sym} 90 90 0 0 {name="DC Op"
only_toplevel=false 
spice_ignore=false

value="
.option savecurrents
.param R3val='22.187k'
.param alpha='1'
.param R2R3ratio='5.6555038*alpha'
.param R2val='R3val*R2R3ratio'
.param R4R2ratio='0.79694273'
.param R4val='R2val*R4R2ratio
.nodeset v(x1.vgate)=1.4
.param VDD=1.8
.control
save all
+ @m.x1.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]


op

let id1=@m.x1.xm1.msky130_fd_pr__pfet_01v8_lvt[id]
let wm1=@m.x1.xm1.msky130_fd_pr__pfet_01v8_lvt[w]
let mm1=@m.x1.xm1.msky130_fd_pr__pfet_01v8_lvt[m]
let weff1=wm1*mm1
let jd1=id1/weff1

let gm1=@m.x1.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]
*let vdsat1=2/(gm1/v.x1.vm1)


write 
print VDD vbg 
*print vdsat1 
unset askquit
quit
.endc
"}
C {devices/launcher.sym} -200 370 0 0 {name=h1
descr=Annotate 
tclcommand="ngspice::annotate"}
C {devices/launcher.sym} -200 330 0 0 {name=h2
descr="View Raw file" 
tclcommand="textwindow $netlist_dir/[file tail [file rootname [ xschem get schname 0 ] ] ].raw"
}
C {devices/lab_pin.sym} 160 -200 0 0 {name=l15 lab=porst}
C {devices/vsource.sym} -240 -140 0 0 {name=V2 net_name=true value="0 pulse(0V 1.8V 10us 0us 0us 5us)"}
C {devices/gnd.sym} -240 -110 0 0 {name=l16 lab=GND}
C {devices/lab_pin.sym} -240 -170 0 0 {name=l19 lab=porst}
C {devices/code.sym} -280 50 0 0 {name=NGSPICE1
only_toplevel=true
spice_ignore=true
value=".option seed=13

* this experimental option enables mos model bin 
* selection based on W/NF instead of W
.param ABSVAR=0.03
.param VDDGAUSS=agauss(1.8, 'ABSVAR', 1)
.param VDD=VCCGAUSS
** variation parameters:
.param sky130_fd_pr__nfet_01v8_lvt__vth0_slope_spectre='agauss(0, ABSVAR, 3)/sky130_fd_pr__nfet_01v8_lvt__vth0_slope'
.param sky130_fd_pr__pfet_01v8_lvt__vth0_slope_spectre='agauss(0, ABSVAR, 3)/sky130_fd_pr__pfet_01v8_lvt__vth0_slope'
.param sky130_fd_pr__nfet_01v8__vth0_slope_spectre='agauss(0, ABSVAR, 3)/sky130_fd_pr__nfet_01v8__vth0_slope'
.param sky130_fd_pr__pfet_01v8__vth0_slope_spectre='agauss(0, ABSVAR, 3)/sky130_fd_pr__pfet_01v8__vth0_slope'

.param sky130_fd_pr__pfet_01v8__toxe_slope_spectre='agauss(0, ABSVAR*2, 3)/sky130_fd_pr__pfet_01v8__toxe_slope'
.param sky130_fd_pr__nfet_01v8__toxe_slope_spectre='agauss(0, ABSVAR*2, 3)/sky130_fd_pr__nfet_01v8__toxe_slope'
.param sky130_fd_pr__pfet_01v8_lvt__toxe_slope_spectre='agauss(0, ABSVAR*2, 3)/sky130_fd_pr__pfet_01v8_lvt__toxe_slope'
.param sky130_fd_pr__nfet_01v8_lvt__toxe_slope_spectre='agauss(0, ABSVAR*2, 3)/sky130_fd_pr__nfet_01v8_lvt__toxe_slope'

.param sky130_fd_pr__res_high_po__var_mult=agauss(0, 'ABSVAR*8', 1)

* .options savecurrents
.control
  let run=1
  dowhile run <= 40
    if run > 1
      reset
      set appendwrite
    end
    save all
    if run % 3 = 0
      set temp=0
    end
    if run % 3 = 1
      set temp=27
    end
    if run % 3 = 2
      set temp=70
    end
    tran 0.05u 150u
    write tsmc_bandgap_real_variation.raw
    let run = run + 1
  end
  set nolegend
  plot all.vbg
.endc
" }
C {devices/code.sym} -140 50 0 0 {name=TT_MODELS
only_toplevel=true
format="tcleval( @value )"
value="
** opencircuitdesign pdks install
.lib $::SKYWATER_MODELS/sky130.lib.spice tt

"
spice_ignore=false}
C {devices/launcher.sym} -200 260 0 0 {name=h3
descr=Backannotate 
tclcommand="xschem annotate_op"}
C {devices/vdd.sym} 220 -230 0 0 {name=l2 lab=VDD}
C {bandgap_1v_v01.sym} 220 -190 0 0 {name=x1}
