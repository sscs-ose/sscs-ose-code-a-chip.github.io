v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/code_shown.sym} -280 -160 0 0 {name=NGSPICE
only_toplevel=true
value="
.control
save all
save @m.xmn.msky130_fd_pr__pfet_01v8[gm]
save @m.xmn.msky130_fd_pr__pfet_01v8[id]
save @m.xmn.msky130_fd_pr__pfet_01v8[vgs]
**save @m.xmn.msky130_fd_pr__pfet_01v8[cgs]
save @m.xmn.msky130_fd_pr__pfet_01v8[vds]
save @m.xmn.msky130_fd_pr__pfet_01v8[vdsat]
save @m.xmp.msky130_fd_pr__nfet_01v8[gm]
save @m.xmp.msky130_fd_pr__nfet_01v8[id]
save @m.xmp.msky130_fd_pr__nfet_01v8[vgs]
save @m.xmp.msky130_fd_pr__nfet_01v8[vds]
**save @m.xmp.msky130_fd_pr__nfet_01v8[cgs]
save @m.xmp.msky130_fd_pr__nfet_01v8[vdsat]
dc I0 1u 10u 1u
op
write Sim_inv.raw
.endc
"}
