.subckt cm_ota vdd out inp inn itail vss  w1_2=1 w3_4=1 w5_6=1 w7_8=1 w9_10=1 beta=2 nf1_2=2 nf3_4=2 nf5_6=2 nf7_8=2 nf9_10=2
*.iopin inn
*.iopin inp
*.iopin out
*.iopin vss
*.iopin vdd
*.iopin itail
XM1 ds1_3 inn source source sky130_fd_pr__nfet_01v8 L=0.500 W=w1_2 nf=nf1_2 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
xM3 ds1_3 ds1_3 vdd vdd sky130_fd_pr__pfet_01v8 L=0.500 W=w3_4 nf=nf3_4 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
XM2 ds2_4 inp source source sky130_fd_pr__nfet_01v8 L=0.500 W=w1_2 nf=nf1_2 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
xM4 ds2_4 ds2_4 vdd vdd sky130_fd_pr__pfet_01v8 L=0.500 W=w3_4 nf=nf3_4 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
xM7 ds5_7 ds1_3 vdd vdd sky130_fd_pr__pfet_01v8 L=0.500 W=w7_8 nf=nf7_8 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
XM5 ds5_7 ds5_7 vss vss sky130_fd_pr__nfet_01v8 L=0.500 W=w5_6 nf=nf5_6 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
XM6 out ds5_7 vss vss sky130_fd_pr__nfet_01v8 L=0.500 W=w5_6 nf=nf5_6 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
xM8 out ds2_4 vdd vdd sky130_fd_pr__pfet_01v8 L=0.500 W=w7_8 nf=nf7_8 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
XM9 source itail vss vss sky130_fd_pr__nfet_01v8 L=0.500 W=w9_10 nf=nf9_10 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
XM10 itail itail vss vss sky130_fd_pr__nfet_01v8 L=0.500 W=w9_10 nf=nf1_2 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29'
+ pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1
.ends