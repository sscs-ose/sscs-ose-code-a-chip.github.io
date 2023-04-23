v {xschem version=3.1.0 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/code_shown.sym} 80 60 0 0 {name=Transient
only_toplevel=true 
spice_ignore=false

value="
.option savecurrents
.param R3val='22.187k'
.param alpha='1'
.param R2R3ratio='5.6555038*alpha'
.param R2val='R3val*R2R3ratio'
.param R4R2ratio='0.79694273'
.param R4val='R2val*R4R2ratio
.param VDD=1.8
.control
save all
+ @m.x1.xm1.msky130_fd_pr__pfet_01v8_lvt[gm]
+ @m.x1.xm2.msky130_fd_pr__pfet_01v8_lvt[gm]
+ @m.x1.xm3.msky130_fd_pr__pfet_01v8_lvt[gm]
+ @m.x1.xm4.msky130_fd_pr__pfet_01v8_lvt[gm]
+ @m.x1.xm5.msky130_fd_pr__nfet_01v8_lvt[gm]
+ @m.x1.xm6.msky130_fd_pr__nfet_01v8_lvt[gm]
+ @m.x1.xm7.msky130_fd_pr__nfet_01v8_lvt[gm]
+ @m.x1.xm8.msky130_fd_pr__pfet_01v8_lvt[gm]
+ @m.x1.xm9.msky130_fd_pr__nfet_01v8_lvt[gm]
+ @m.x1.xm13.msky130_fd_pr__pfet_01v8_lvt[gm]

option temp=27
tran 0.1n 20u
option temp=0
tran 0.1n 20u
option temp=70
tran 0.1n 20u
write tsmc_bandgap_real_70degc_vbg.raw vbg i(v1)
setplot tran2
write tsmc_bandgap_real_0degc_vbg.raw vbg i(v1)
setplot tran1
write tsmc_bandgap_real_27degc_vbg.raw vbg i(v1)
.endc
"}
C {devices/gnd.sym} 230 -120 0 0 {name=l1 lab=GND}
C {devices/lab_pin.sym} 300 -170 0 1 {name=l3 lab=vbg}
C {devices/lab_pin.sym} 170 -170 0 0 {name=l15 lab=porst}
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
C {devices/vdd.sym} 230 -200 0 0 {name=l2 lab=VDD}
C {bandgap_1v_v01.sym} 230 -160 0 0 {name=x1}
C {devices/launcher.sym} -200 350 0 0 {name=h1
descr=Annotate 
tclcommand="ngspice::annotate"}
C {devices/launcher.sym} -200 310 0 0 {name=h2
descr="View Raw file" 
tclcommand="textwindow $netlist_dir/[file tail [file rootname [ xschem get schname 0 ] ] ].raw"
}
C {devices/launcher.sym} -200 240 0 0 {name=h3
descr=Backannotate 
tclcommand="xschem annotate_op"}
C {devices/vsource.sym} -210 -250 0 0 {name=V1 net_name=true value="'VDD' pwl 0us 0 5us 'VDD'"}
C {devices/vdd.sym} -210 -280 0 0 {name=l8 lab=VDD}
C {devices/gnd.sym} -210 -220 0 0 {name=l9 lab=GND}
C {devices/vsource.sym} -210 -110 0 0 {name=V2 net_name=true value="0 pulse(0V 1.8V 10us 0us 0us 5us)"}
C {devices/gnd.sym} -210 -80 0 0 {name=l16 lab=GND}
C {devices/lab_pin.sym} -210 -140 0 0 {name=l19 lab=porst}
