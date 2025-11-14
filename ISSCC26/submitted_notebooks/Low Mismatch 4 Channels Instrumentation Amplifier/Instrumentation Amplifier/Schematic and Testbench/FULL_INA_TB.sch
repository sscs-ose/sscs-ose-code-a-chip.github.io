v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 710 -1200 750 -1200 {lab=ch1_in-}
N 910 -1240 940 -1240 {lab=ch1_out+}
N 910 -1200 940 -1200 {lab=ch1_out-}
N 700 -1240 750 -1240 {lab=ch1_in+}
N 700 -1200 710 -1200 {lab=ch1_in-}
N 820 -1320 820 -1300 {lab=VBIAS}
N 840 -1320 840 -1300 {lab=VDD}
N 770 -1320 820 -1320 {lab=VBIAS}
N 840 -1320 880 -1320 {lab=VDD}
N 840 -1130 880 -1130 {lab=VSS}
N 840 -1140 840 -1130 {lab=VSS}
N 790 -1130 820 -1130 {lab=VCM}
N 820 -1140 820 -1130 {lab=VCM}
N 710 -980 750 -980 {lab=ch2_in-}
N 910 -1020 940 -1020 {lab=ch2_out+}
N 910 -980 940 -980 {lab=ch2_out-}
N 700 -1020 750 -1020 {lab=ch2_in+}
N 700 -980 710 -980 {lab=ch2_in-}
N 820 -1100 820 -1080 {lab=VBIAS}
N 840 -1100 840 -1080 {lab=VDD}
N 770 -1100 820 -1100 {lab=VBIAS}
N 840 -1100 880 -1100 {lab=VDD}
N 840 -910 880 -910 {lab=VSS}
N 840 -920 840 -910 {lab=VSS}
N 790 -910 820 -910 {lab=VCM}
N 820 -920 820 -910 {lab=VCM}
N 710 -760 750 -760 {lab=ch3_in-}
N 910 -800 940 -800 {lab=ch3_out+}
N 910 -760 940 -760 {lab=ch3_out-}
N 700 -800 750 -800 {lab=ch3_in+}
N 700 -760 710 -760 {lab=ch3_in-}
N 820 -880 820 -860 {lab=VBIAS}
N 840 -880 840 -860 {lab=VDD}
N 770 -880 820 -880 {lab=VBIAS}
N 840 -880 880 -880 {lab=VDD}
N 840 -690 880 -690 {lab=VSS}
N 840 -700 840 -690 {lab=VSS}
N 790 -690 820 -690 {lab=VCM}
N 820 -700 820 -690 {lab=VCM}
N 700 -540 740 -540 {lab=ch4_in-}
N 900 -580 930 -580 {lab=ch4_out+}
N 900 -540 930 -540 {lab=ch4_out-}
N 690 -580 740 -580 {lab=ch4_in+}
N 690 -540 700 -540 {lab=ch4_in-}
N 810 -660 810 -640 {lab=VBIAS}
N 830 -660 830 -640 {lab=VDD}
N 760 -660 810 -660 {lab=VBIAS}
N 830 -660 870 -660 {lab=VDD}
N 830 -470 870 -470 {lab=VSS}
N 830 -480 830 -470 {lab=VSS}
N 780 -470 810 -470 {lab=VCM}
N 810 -480 810 -470 {lab=VCM}
C {devices/code_shown.sym} 1140 -710 0 0 {name=MODELS only_toplevel=true
format="tcleval( @value )"
value="
.include $::180MCU_MODELS/design.ngspice
.lib $::180MCU_MODELS/sm141064.ngspice typical
.lib $::180MCU_MODELS/smbb000149.ngspice typical
.lib $::180MCU_MODELS/sm141064.ngspice cap_mim
.lib $::180MCU_MODELS/sm141064.ngspice moscap_typical
.lib $::180MCU_MODELS/sm141064.ngspice mimcap_typical
"}
C {devices/code_shown.sym} 1140 -1200 0 0 {name=NGSPICE only_toplevel=true
value="
	* -- AC ANALYSIS ---
	.ac dec 100 1 1e12
	* -- TRANSIENT --
	*.tran 500u 0.5m
.control
	* Ac sweep
	ac
	set gnuplot = 1
	setplot ac1
	display
	
	* Eksekusi transien
	reset
	run

	* Plot transient
	*plot V(ch3_in+)-V(ch3_in-)
	*plot V(ch3_out+)-V(ch3_out-)
	*plot V(ch2_in+)-V(ch2_in-)
	*plot V(ch2_out+)-V(ch2_out-)
	*plot db(V(out1)-V(out2))
	*plot ph(V(ch1_out+)-V(ch1_out-))
	plot db(V(ch1_out+)-V(ch1_out-))
	*plot ph(V(ch2_out+)-V(ch2_out-))

save all

.endc
"}
C {opin.sym} 940 -1200 0 0 {name=p4 sig_type=std_logic lab=ch1_out-}
C {opin.sym} 940 -1240 0 0 {name=p5 sig_type=std_logic lab=ch1_out+}
C {INA_STAGE_FIXED.sym} 720 -1040 0 0 {name=x1}
C {ipin.sym} 700 -1240 0 0 {name=p2 sig_type=std_logic lab=ch1_in+}
C {ipin.sym} 700 -1200 0 0 {name=p3 sig_type=std_logic lab=ch1_in-}
C {iopin.sym} 790 -1130 2 0 {name=p6 sig_type=std_logic lab=VCM}
C {iopin.sym} 770 -1320 2 0 {name=p7 sig_type=std_logic lab=VBIAS}
C {iopin.sym} 880 -1320 0 0 {name=p8 sig_type=std_logic lab=VDD}
C {opin.sym} 940 -980 0 0 {name=p9 sig_type=std_logic lab=ch2_out-}
C {INA_STAGE_FIXED.sym} 720 -820 0 0 {name=x2}
C {ipin.sym} 700 -1020 0 0 {name=p19 sig_type=std_logic lab=ch2_in+}
C {ipin.sym} 700 -980 0 0 {name=p20 sig_type=std_logic lab=ch2_in-}
C {lab_wire.sym} 880 -910 0 0 {name=p21 sig_type=std_logic lab=VSS}
C {lab_wire.sym} 770 -1100 2 0 {name=p22 sig_type=std_logic lab=VBIAS}
C {lab_wire.sym} 880 -1100 0 0 {name=p23 sig_type=std_logic lab=VDD}
C {opin.sym} 940 -800 0 0 {name=p25 sig_type=std_logic lab=ch3_out+}
C {INA_STAGE_FIXED.sym} 720 -600 0 0 {name=x3}
C {ipin.sym} 700 -800 0 0 {name=p26 sig_type=std_logic lab=ch3_in+}
C {ipin.sym} 700 -760 0 0 {name=p27 sig_type=std_logic lab=ch3_in-}
C {lab_wire.sym} 790 -690 2 0 {name=p28 sig_type=std_logic lab=VCM}
C {lab_wire.sym} 770 -880 2 0 {name=p29 sig_type=std_logic lab=VBIAS}
C {lab_wire.sym} 880 -880 0 0 {name=p30 sig_type=std_logic lab=VDD}
C {opin.sym} 930 -540 0 0 {name=p31 sig_type=std_logic lab=ch4_out-}
C {opin.sym} 930 -580 0 0 {name=p32 sig_type=std_logic lab=ch4_out+}
C {INA_STAGE_FIXED.sym} 710 -380 0 0 {name=x4}
C {ipin.sym} 690 -580 0 0 {name=p33 sig_type=std_logic lab=ch4_in+}
C {ipin.sym} 690 -540 0 0 {name=p34 sig_type=std_logic lab=ch4_in-}
C {lab_wire.sym} 780 -470 2 0 {name=p35 sig_type=std_logic lab=VCM}
C {lab_wire.sym} 760 -660 2 0 {name=p36 sig_type=std_logic lab=VBIAS}
C {lab_wire.sym} 870 -660 0 0 {name=p37 sig_type=std_logic lab=VDD}
C {iopin.sym} 880 -1130 0 0 {name=p38 sig_type=std_logic lab=VSS}
C {lab_wire.sym} 790 -910 2 0 {name=p39 sig_type=std_logic lab=VCM}
C {lab_wire.sym} 880 -690 0 0 {name=p40 sig_type=std_logic lab=VSS}
C {lab_wire.sym} 870 -470 0 0 {name=p41 sig_type=std_logic lab=VSS}
C {opin.sym} 940 -760 0 0 {name=p45 sig_type=std_logic lab=ch3_out-}
C {opin.sym} 940 -1020 0 0 {name=p24 sig_type=std_logic lab=ch2_out+}
