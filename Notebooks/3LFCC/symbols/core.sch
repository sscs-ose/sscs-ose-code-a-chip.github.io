v {xschem version=3.0.0 file_version=1.2 
}
G {}
K {}
V {}
S {}
E {}
N 320 -40 650 -40 {
lab=#net1}
N 320 -140 480 -140 {
lab=#net2}
N 480 -140 480 -100 {
lab=#net2}
N 480 -100 650 -100 {
lab=#net2}
N 320 -240 520 -240 {
lab=#net3}
N 520 -240 520 -160 {
lab=#net3}
N 520 -160 650 -160 {
lab=#net3}
N 320 -340 570 -340 {
lab=#net4}
N 570 -340 570 -220 {
lab=#net4}
N 570 -220 650 -220 {
lab=#net4}
N 1060 -60 1120 -60 {
lab=VN}
N 1060 -130 1120 -130 {
lab=out}
N 1060 -200 1120 -200 {
lab=VP}
N 320 -380 360 -380 {
lab=VH}
N 320 -280 360 -280 {
lab=VH}
N 320 -180 360 -180 {
lab=VH}
N 320 -80 360 -80 {
lab=VH}
N -100 -360 20 -360 {
lab=D1}
N -100 -260 20 -260 {
lab=D2}
N -100 -160 20 -160 {
lab=D3}
N -100 -60 20 -60 {
lab=D4}
N -40 -380 -40 -80 {
lab=VDD}
N -40 -380 20 -380 {
lab=VDD}
N -40 -280 20 -280 {
lab=VDD}
N -40 -180 20 -180 {
lab=VDD}
N -40 -80 20 -80 {
lab=VDD}
N -0 -340 20 -340 {
lab=VN}
N 0 -340 -0 20 {
lab=VN}
N 0 -240 20 -240 {
lab=VN}
N 0 -140 20 -140 {
lab=VN}
N -0 -40 20 -40 {
lab=VN}
N 0 120 1100 120 {
lab=VN}
N 1100 -60 1100 20 {
lab=VN}
N 360 -380 360 -80 {
lab=VH}
N 810 20 810 50 {
lab=fc1}
N 900 20 900 50 {
lab=fc2}
N 1100 20 1100 120 {
lab=VN}
N 0 20 0 120 {
lab=VN}
N 360 -380 380 -380 {
lab=VH}
C {converter.sym} 610 60 0 0 {name=X1}
C {level_shifter.sym} 170 -60 0 0 {name=x1}
C {level_shifter.sym} 170 -160 0 0 {name=x2}
C {level_shifter.sym} 170 -260 0 0 {name=x3}
C {level_shifter.sym} 170 -360 0 0 {name=x4}
C {devices/opin.sym} 1120 -130 0 0 {name=p5 lab=out}
C {devices/iopin.sym} 1120 -200 0 0 {name=p6 lab=VP}
C {devices/ipin.sym} -100 -360 0 0 {name=p1 lab=D1}
C {devices/ipin.sym} -100 -260 0 0 {name=p2 lab=D2}
C {devices/ipin.sym} -100 -160 0 0 {name=p8 lab=D3}
C {devices/ipin.sym} -100 -60 0 0 {name=p9 lab=D4}
C {devices/iopin.sym} -40 -380 2 0 {name=p10 lab=VDD}
C {devices/iopin.sym} 1120 -60 0 0 {name=p3 lab=VN}
C {devices/iopin.sym} 380 -380 0 0 {name=p10 lab=VH}
C {devices/iopin.sym} 810 50 1 0 {name=p3 lab=fc1}
C {devices/iopin.sym} 900 50 1 0 {name=p3 lab=fc2}
