.subckt current_mirror_ota avdd_1v8 out inp inn itail avss
M10 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.13e-7 nf=22
M9 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.13e-7 nf=22
M1 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.13e-7 nf=22
M2 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.13e-7 nf=22
M3 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.13e-7 nf=16
M8 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.13e-7 nf=60
M4 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.13e-7 nf=16
M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.13e-7 nf=60
M5 net9 net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.13e-7 nf=54
M6 vout net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.13e-7 nf=54
.ends current_mirror_ota


//.subckt current_mirror_ota vss vdd vout vinn vinp id
//M10 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=22
//M9 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=22
//M1 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=22
//M2 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=22
//M3 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=16
//M8 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=60
//M4 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=16
//M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=60
//M5 net9 net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=54
//M6 vout net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=54
//.ends current_mirror_ota
