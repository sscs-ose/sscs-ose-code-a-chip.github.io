v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 440 180 440 220 {lab=vdd}
N 590 180 680 180 {lab=vdd}
N 680 180 680 220 {lab=vdd}
N 340 400 340 550 {lab=#net1}
N 340 550 460 550 {lab=#net1}
N 460 400 460 550 {lab=#net1}
N 660 400 660 550 {lab=#net2}
N 780 400 780 550 {lab=#net2}
N 660 550 780 550 {lab=#net2}
N 460 340 530 340 {lab=vdd}
N 530 180 530 340 {lab=vdd}
N 440 180 530 180 {lab=vdd}
N 590 340 660 340 {lab=vdd}
N 590 180 590 340 {lab=vdd}
N 400 280 440 280 {lab=#net3}
N 780 280 780 340 {lab=v_out}
N 560 610 660 610 {lab=#net4}
N 560 610 560 650 {lab=#net4}
N 460 610 560 610 {lab=#net4}
N 560 370 620 370 {lab=vctrl_n}
N 880 280 990 280 {lab=v_out}
N 820 370 820 510 {lab=vctrl_p}
N 300 510 820 510 {lab=vctrl_p}
N 300 440 300 510 {lab=vctrl_p}
N 400 250 400 280 {lab=#net3}
N 340 280 400 280 {lab=#net3}
N 680 280 780 280 {lab=v_out}
N 720 250 750 250 {lab=#net3}
N 340 280 340 340 {lab=#net3}
N 750 20 750 250 {lab=#net3}
N 340 20 750 20 {lab=#net3}
N 340 20 340 280 {lab=#net3}
N 560 180 590 180 {lab=vdd}
N 130 280 130 410 {lab=#net3}
N 130 280 340 280 {lab=#net3}
N 90 440 90 680 {lab=iref}
N 460 680 520 680 {lab=iref}
N 990 280 990 410 {lab=v_out}
N 1030 440 1030 770 {lab=iref}
N 520 770 1030 770 {lab=iref}
N 280 680 460 680 {lab=iref}
N 880 280 880 330 {lab=v_out}
N 780 280 880 280 {lab=v_out}
N 560 370 560 410 {lab=vctrl_n}
N 500 370 560 370 {lab=vctrl_n}
N 260 440 300 440 {lab=vctrl_p}
N 300 370 300 440 {lab=vctrl_p}
N 370 580 420 580 {lab=vin_p}
N 700 580 760 580 {lab=vin_n}
N 520 680 520 770 {lab=iref}
N 460 680 460 700 {lab=iref}
N 320 770 520 770 {lab=iref}
N 280 680 280 740 {lab=iref}
N 90 680 280 680 {lab=iref}
N 560 710 560 740 {lab=gnd}
N 990 470 990 500 {lab=gnd}
N 130 470 130 500 {lab=gnd}
N 560 130 560 180 {lab=vdd}
N 530 180 560 180 {lab=vdd}
N 280 800 280 830 {lab=gnd}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/pfet3_01v8.sym} 420 250 0 0 {name=M1
W=640
L=0.5
body=VDD
nf=128
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 440 580 0 0 {name=M2
W=640
L=8
body=GND
nf=128
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 680 580 0 1 {name=M3
W=640
L=8
body=GND
nf=128
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/pfet3_01v8.sym} 700 250 0 1 {name=M4
W=640
L=0.5
body=VDD
nf=128
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 540 680 0 0 {name=M5
W=40
L=8
body=GND
nf=8
mult=14
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 320 370 0 0 {name=M6
W=20
L=2
body=GND
nf=4
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 480 370 0 1 {name=M7
W=20
L=2
body=GND
nf=4
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 640 370 0 0 {name=M8
W=20
L=2
body=GND
nf=4
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 800 370 0 1 {name=M9
W=20
L=2
body=GND
nf=4
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 110 440 0 0 {name=M10
W=40
L=8
body=GND
nf=8
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 1010 440 0 1 {name=M11
W=40
L=8
body=GND
nf=8
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {/foss/pdks/sky130A/libs.tech/xschem/sky130_fd_pr/nfet3_01v8.sym} 300 770 0 1 {name=M12
W=40
L=8
body=GND
nf=8
mult=1
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {iopin.sym} 560 130 2 1 {name=p8 lab=vdd}
C {iopin.sym} 760 580 0 0 {name=p9 lab=vin_n}
C {iopin.sym} 460 700 1 0 {name=p10 lab=iref}
C {iopin.sym} 560 410 0 0 {name=p11 lab=vctrl_n}
C {iopin.sym} 560 740 0 0 {name=p13 lab=gnd}
C {iopin.sym} 990 500 0 1 {name=p14 lab=gnd}
C {iopin.sym} 260 440 0 1 {name=p16 lab=vctrl_p}
C {iopin.sym} 370 580 0 1 {name=p17 lab=vin_p}
C {iopin.sym} 880 330 1 0 {name=p18 lab=v_out}
C {iopin.sym} 130 500 0 0 {name=p20 lab=gnd}
C {iopin.sym} 280 830 0 0 {name=p1 lab=gnd}
