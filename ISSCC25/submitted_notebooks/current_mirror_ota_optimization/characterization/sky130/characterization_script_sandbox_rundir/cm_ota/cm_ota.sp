//.subckt cm_ota itail inn inp avdd_1v8 avss out
//M1 net1 inn itail avss sky130_fd_pr__nfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1 
//M3 net1 net1 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//M2 net2 inp itail avss sky130_fd_pr__nfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//M4 net2 net2 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//M7 net3 net1 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//M5 net3 net3 avss avss sky130_fd_pr__nfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//M6 out net3 avss avss sky130_fd_pr__nfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//M8 out net2 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 stack=2 W=10e-7 nf=1
//.ends cm_ota

.subckt current_mirror_ota vss vdd vout vinn vinp id
M5 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=4
M4 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=4
M3 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=8
M0 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=8
M2 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=6
M6 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=12
M1 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=6
M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=12
M8 net9 net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=16
M9 vout net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=16
.ends current_mirror_ota
