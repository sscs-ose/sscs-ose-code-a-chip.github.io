.subckt cm_ota itail inn inp avdd_1v8 avss out
XM1 net1 inn itail avss sky130_fd_pr__nfet_01v8 L=150e-9 W=10e-7 nf=1 
XM3 net1 net1 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 W=10e-7 nf=1
XM2 net2 inp itail avss sky130_fd_pr__nfet_01v8 L=150e-9 W=10e-7 nf=1
XM4 net2 net2 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 W=10e-7 nf=1
XM7 net3 net1 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 W=10e-7 nf=1
XM5 net3 net3 avss avss sky130_fd_pr__nfet_01v8 L=150e-9 W=10e-7 nf=1
XM6 out net3 avss avss sky130_fd_pr__nfet_01v8 L=150e-9 W=10e-7 nf=1
XM8 out net2 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-9 W=10e-7 nf=1
.ends cm_ota
