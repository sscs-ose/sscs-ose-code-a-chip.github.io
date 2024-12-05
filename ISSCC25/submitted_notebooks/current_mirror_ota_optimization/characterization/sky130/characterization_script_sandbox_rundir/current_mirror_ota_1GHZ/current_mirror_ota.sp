.subckt current_mirror_ota vss vdd vout vinn vinp id
M10 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=14
M9 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=14
M1 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=14
M2 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=14
M3 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=32
M8 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=50
M4 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=32
M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=10.5e-7 nf=50
M5 net9 net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=22
M6 vout net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=10.5e-7 nf=22
.ends current_mirror_ota



//.subckt current_mirror_ota vss vdd vout vinn vinp id
//M5 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=4
//M4 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=4
//M3 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=8
//M0 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=8
//M2 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=6
//M6 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=12
//M1 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=6
//M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=12
//M8 net9 net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=16
//M9 vout net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 stack=2 w=10.5e-7 nf=16
//.ends current_mirror_ota
