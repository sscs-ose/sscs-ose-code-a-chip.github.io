v {xschem version=3.4.6 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {Testbench for simple POR} 350 40 0 0 0.6 0.6 {}
N 420 340 690 340 { lab=GND}
N 160 280 160 340 { lab=GND}
N 370 280 370 340 { lab=GND}
N 370 180 370 220 { lab=vdd3v3}
N 370 170 370 180 { lab=vdd3v3}
N 490 170 660 170 { lab=vdd3v3}
N 660 170 660 180 { lab=vdd3v3}
N 160 150 160 220 { lab=vdd1v8}
N 420 150 720 150 { lab=vdd1v8}
N 720 150 720 180 { lab=vdd1v8}
N 840 230 880 230 { lab=porb_h}
N 840 260 880 260 { lab=porb_l}
N 840 290 880 290 { lab=por_l}
N 360 170 370 170 { lab=vdd3v3}
N 200 150 210 150 { lab=vdd1v8}
N 160 150 200 150 { lab=vdd1v8}
N 140 150 160 150 { lab=vdd1v8}
N 160 340 210 340 { lab=GND}
N 210 150 420 150 { lab=vdd1v8}
N 210 340 370 340 { lab=GND}
N 370 340 420 340 { lab=GND}
N 370 170 490 170 { lab=vdd3v3}
N 690 340 720 340 {lab=GND}
C {sky130_ef_ip__simple_por.sym} 690 260 0 0 {name=x1}
C {devices/gnd.sym} 600 340 0 0 {name=l1 lab=GND}
C {devices/vsource.sym} 370 250 0 0 {name=V1 value="PWL(0.0 0 100u 0 5m CACE\{avdd\})"}
C {devices/vsource.sym} 160 250 0 0 {name=V2 value="PWL(0.0 0 300u 0 5.3m CACE\{dvdd\})"}
C {devices/opin.sym} 360 170 0 1 {name=p1 lab=vdd3v3}
C {devices/opin.sym} 140 150 0 1 {name=p2 lab=vdd1v8}
C {devices/opin.sym} 880 230 0 0 {name=p3 lab=porb_h}
C {devices/opin.sym} 880 260 0 0 {name=p4 lab=porb_l}
C {devices/opin.sym} 880 290 0 0 {name=p5 lab=por_l}
C {devices/code_shown.sym} 1000 90 0 0 {name=control only_toplevel=false value="
.control
  tran 1u CACE\{Tmax\}
  set wr_singlescale
  wrdata CACE\{simpath\}/CACE\{filename\}_CACE\{N\}.data V(porb_h) V(porb_l) V(por_l)
.endc"}
C {devices/code_shown.sym} 1000 240 0 0 {name=SETUP
simulator=ngspice
only_toplevel=false
value="
.lib CACE\{PDK_ROOT\}/CACE\{PDK\}/libs.tech/combined/sky130.lib.spice CACE\{corner\}
.include CACE\{PDK_ROOT\}/CACE\{PDK\}/libs.ref/sky130_fd_sc_hvl/spice/sky130_fd_sc_hvl.spice

.include CACE\{DUT_path\}

.temp CACE\{temperature\}

.option SEED=CACE[CACE\{seed=12345\} + CACE\{iterations=0\}]

* Flag unsafe operating conditions (exceeds models' specified limits)
.option warn=1
"}
