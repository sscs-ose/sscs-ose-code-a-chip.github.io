.subckt current_mirror_ota vss vdd vout vinn vinp id
M10 id id vss vss sky130_fd_pr__nfet_01v8 L=500e-09 w=4.2e-7 nf=2
M9 source id vss vss sky130_fd_pr__nfet_01v8 L=500e-09 w=4.2e-7 nf=2
M1 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=500e-09 w=4.2e-7 nf=2
M2 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=500e-09 w=4.2e-7 nf=2
M3 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-09 w=4.2e-7 nf=10
M8 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-09 w=4.2e-7 nf=52
M4 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-09 w=4.2e-7 nf=10
M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=500e-09 w=4.2e-7 nf=52
M5 net9 net9 vss vss sky130_fd_pr__nfet_01v8 L=500e-09 w=4.2e-7 nf=16
M6 vout net9 vss vss sky130_fd_pr__nfet_01v8 L=500e-09 w=4.2e-7 nf=16
.ends current_mirror_ota

//.subckt current_mirror_ota vss vdd vout vinn vinp id
//M10 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=8.4e-7 nf=8
//M9 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=8.4e-7 nf=8
//M1 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=8.4e-7 nf=8
//M2 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=8.4e-7 nf=8
//M3 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=8.4e-7 nf=12
//M8 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=8.4e-7 nf=42
//M4 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=8.4e-7 nf=12
//M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=8.4e-7 nf=42
//M5 net9 net9 vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=8.4e-7 nf=24
//M6 vout net9 vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=8.4e-7 nf=24
//.ends current_mirror_ota


//.subckt current_mirror_ota vdd out inp inn itail vss
//M10 itail itail vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=14
//M9 itail source vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=14
//M1 ds1_3 inn source source sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=14
//M2 ds2_4 inp source source sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=14
//M3 ds1_3 ds1_3 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=24
//M8 out ds2_4 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=84
//M4 ds2_4 ds2_4 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=24
//M7 ds5_7 ds1_3 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=84
//M5 ds5_7 ds5_7 vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=46
//M6 out ds5_7 vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=46
//.ends current_mirror_ota

//.subckt current_mirror_ota vdd out inp inn itail vss
//M10 avss avss avss avss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M9 avss avss avss avss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M1 ds1_3 inn itail itail sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M2 ds2_4 inp itail itail sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M3 ds1_3 ds1_3 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=2
//M4 ds2_4 ds2_4 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=2
//M5 ds5_7 ds5_7 avss avss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=46
//M6 out ds5_7 avss avss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=46
//M7 ds5_7 ds1_3 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=16
//M8 out ds2_4 avdd_1v8 avdd_1v8 sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=16
//.ends current_mirror_ota
//


//.subckt current_mirror_ota vss vdd vout vinn vinp id
//M10 id id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M9 source id vss vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M1 net7 vinn source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M2 net8 vinp source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=4
//M3 net7 net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=2
//M4 net8 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=2
//M5 net9 net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=46
//M6 vout net9 source vss sky130_fd_pr__nfet_01v8 L=150e-09 w=4.2e-7 nf=46
//M7 net9 net8 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=16
//M8 vout net7 vdd vdd sky130_fd_pr__pfet_01v8 L=150e-09 w=4.2e-7 nf=16
//.ends current_mirror_ota


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
