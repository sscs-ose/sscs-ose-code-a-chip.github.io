v {xschem version=3.1.0 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/code_shown.sym} 20 50 0 0 {name=NGSPICE
only_toplevel=true
spice_ignore=false
value="
.option savecurrents
.option warn=1
.param VDD=1.8
.param R3val='22.187k'
.param alpha='1'
.param R2R3ratio='5.6555038*alpha'
.param R2val='R3val*R2R3ratio' 
.param R4R2ratio=0.79694273
.param R4val='R2val*R4R2ratio'
.nodeset v(x1.vgate)=1.3


.dc temp -10 80 10m
.option temp=27
.control
save all
run
save vbg deriv(vbg)

let indx27 = 3700
let indx0 = 1000
let indx70 = 8000
*indx is the index of temperature sweep for 27degC
echo 'Vbg @ 27degC'
let vbg0c = vbg[indx0]
let vbg27c = vbg[indx27]
let vbg70c = vbg[indx70]
print vbg0c
print vbg27c
print vbg70c
echo 'dVbe/degC & ppm @ 27degC'
print deriv(vbg)[indx27] deriv(vbg)[indx27]/vbg27c
echo 'ppm real'
print (vbg[indx70]-vbg[indx0])/vbg[indx27]/(70-0)*1e6
save deriv(vbg)/vbg27c

write
unset askquit
quit
.endc

"}
C {devices/gnd.sym} 260 -180 0 0 {name=l1 lab=GND}
C {devices/lab_pin.sym} 330 -230 0 1 {name=l3 lab=vbg}
C {devices/lab_pin.sym} 200 -230 0 0 {name=l15 lab=porst}
C {devices/vdd.sym} 260 -260 0 0 {name=l2 lab=VDD}
C {bandgap_1v_v01.sym} 260 -220 0 0 {name=x1}
C {devices/code.sym} -310 90 0 0 {name=NGSPICE1
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
C {devices/launcher.sym} -230 390 0 0 {name=h1
descr=Annotate 
tclcommand="ngspice::annotate"}
C {devices/launcher.sym} -230 350 0 0 {name=h2
descr="View Raw file" 
tclcommand="textwindow $netlist_dir/[file tail [file rootname [ xschem get schname 0 ] ] ].raw"
}
C {devices/launcher.sym} -230 280 0 0 {name=h3
descr=Backannotate 
tclcommand="xschem annotate_op"}
C {devices/vsource.sym} -240 -210 0 0 {name=V1 net_name=true value="'VDD' pwl 0us 0 5us 'VDD'"}
C {devices/vdd.sym} -240 -240 0 0 {name=l8 lab=VDD}
C {devices/gnd.sym} -240 -180 0 0 {name=l9 lab=GND}
C {devices/vsource.sym} -240 -70 0 0 {name=V2 net_name=true value="0 pulse(0V 1.8V 10us 0us 0us 5us)"}
C {devices/gnd.sym} -240 -40 0 0 {name=l16 lab=GND}
C {devices/lab_pin.sym} -240 -100 0 0 {name=l19 lab=porst}
C {sky130_fd_pr/corner.sym} -630 240 0 0 {name=CORNER only_toplevel=true corner=tt}
