.subckt five_transistor_ota vss vdd vout vinn vinp id
M5 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-9 w=10.5e-7 nf=10 stack=3
M4 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-9 w=10.5e-7 nf=10 stack=3
M3 vout vinn source vss sky130_fd_pr__nfet_01v8 L=150e-9 w=10.5e-7 nf=20 stack=3
M0 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-9 w=10.5e-7 nf=20 stack=3
M2 vout net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-9 w=10.5e-7 nf=20 stack=3
M1 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-9 w=10.5e-7 nf=20 stack=3
.ends five_transistor_ota
