<Qucs Schematic 25.2.0>
<Properties>
  <View=-1,-909,3483,1329,1.14671,1252,1133>
  <Grid=10,10,1>
  <DataSet=03_postEM_60GHz_MPA_ngspice.dat>
  <DataDisplay=03_postEM_60GHz_MPA_ngspice.dpl>
  <OpenDisplay=0>
  <Script=harmonic_balance.m>
  <RunScript=0>
  <showFrame=0>
  <FrameText0=Title>
  <FrameText1=Drawn By:>
  <FrameText2=Date:>
  <FrameText3=Revision:>
</Properties>
<Symbol>
</Symbol>
<Components>
  <Lib npn13G2 1 1840 580 10 64 0 0 "/home/pedersen/.qucs/user_lib/IHP_PDK_nonlinear_components" 0 "npn13G2" 0 "10" 1>
  <IProbe Icollector 1 1800 370 -107 -18 1 3>
  <GND * 1 1840 710 0 0 0 0>
  <GND * 1 1880 580 0 0 0 0>
  <GND * 1 2030 470 0 0 0 0>
  <Vdc V1 1 1380 690 18 -26 0 1 "0.98" 1>
  <GND * 1 1380 720 0 0 0 0>
  <IProbe Iout 1 1990 320 -26 16 0 0>
  <GND * 1 1940 220 0 0 0 0>
  <Vdc V2 1 1940 170 18 -26 0 1 "1.65V" 1>
  <R R2 1 2030 390 15 -26 0 1 "50 Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <IProbe Idc_in 1 1800 160 18 -26 1 3>
  <IProbe Ibase 1 1720 450 -26 16 0 0>
  <GND * 1 1190 720 0 0 0 0>
  <.SP SP1 1 1190 -540 0 56 0 0 "lin" 1 "1 GHz" 1 "200 GHz" 1 "200" 1 "no" 0 "1" 0 "2" 0 "no" 0 "no" 0>
  <GND * 1 2140 470 0 0 0 0>
  <rsil R6 0 2720 -330 -26 12 0 0 "rsil" 0 "X" 0 "0.5" 1 "0.5" 1 "0" 0 "sub!" 0 "1" 0 "(9.0e-6 / w + 7.0 * ((b + 1)*l + (1.081*(w + 1.0e-8) + 0.18e-6)*b) / (w + 1.0e-8)) / m" 1 "_xml_device_name=rsil" 0>
  <cmim C16 0 2350 -160 -26 15 0 0 "cap_cmim" 0 "X" 0 "7.0" 1 "7.0" 1 "1" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "_xml_device_name=cap_cmim" 0>
  <rppd R4 0 2350 -330 -26 12 0 0 "rppd" 0 "X" 0 "10" 1 "0.5" 1 "0" 0 "sub!" 0 "1" 0 "(70.0e-6 / w + 260.0 * ((b + 1)*l + (1.081*(w + 6.0e-9) + 0.18e-6)*b) / (w + 6.0e-9)) / m" 1 "_xml_device_name=rppd" 0>
  <rhigh R1_dim 0 2520 -330 -26 12 0 0 "rhigh" 0 "X" 0 "5" 1 "12.7" 1 "0" 0 "sub!" 0 "1" 0 "(1.6e-4 / w + 1360.0*((b + 1)*l + (1.081*(w - 0.04e-6) + 0.18e-6)*b) / (w - 0.04e-6)) / m" 1 "_xml_device_name=rhigh" 0>
  <GND * 1 1490 560 0 0 0 0>
  <GND * 1 1490 480 0 0 0 0>
  <rfcmim cap_rfcmim1_dim 0 2720 -160 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "5" 1 "10.0" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <rfcmim cap_rfcmim2_dim 0 2920 -160 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "20" 1 "20" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <Lib cap_rfcmim3 1 1920 320 -38 54 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "10u" 1 "20.0u" 1>
  <GND * 1 1920 350 0 0 0 0>
  <rfcmim cap_rfcmim3_dim 0 2520 -160 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "5" 1 "7" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <GND * 1 1290 480 0 0 0 0>
  <GND * 1 1780 540 0 0 0 0>
  <Pac P1 1 1190 630 18 -26 0 1 "1" 1 "50 Ohm" 1 "0 dBm" 1 "60 GHz" 1 "26.85" 0 "true" 0>
  <Pac P2 1 2140 400 18 -26 0 1 "2" 1 "50 Ohm" 1 "0 dBm" 1 "60 GHz" 1 "26.85" 0 "true" 0>
  <Lib cap_rfcmim2 1 1490 450 -46 -103 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "3.335u" 1 "8u" 1>
  <Lib cap_rfcmim1 1 1290 450 -26 -96 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "3.961u" 1 "4.9u" 1>
  <IProbe Iin 1 1190 530 16 -26 0 1>
  <SPfile X8 1 1780 480 24 -15 0 0 "openEMS/output/run_60_GHz_MPA_BJT_data/run_60_GHz_MPA_noBJT_fstop350GHz.s4p" 0 "rectangular" 0 "linear" 0 "short" 0 "4" 0>
  <GND * 1 1770 230 0 0 0 3>
  <GND * 1 1620 540 0 0 0 0>
  <SPfile X10 1 1620 480 -26 -95 0 0 "openEMS/output/run_interconnect_base_v2_data/run_interconnect_base_v2.s3p" 0 "rectangular" 0 "linear" 0 "shortall" 0 "3" 0>
  <GND * 1 1410 630 0 0 0 1>
  <GND * 1 1410 540 0 0 0 0>
  <R R7 1 1380 550 -92 -26 0 3 "1 mOhm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <Lib rhigh1 1 1490 530 38 27 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "rhigh" 0 "5u" 1 "4.300u" 1 "1" 1>
  <GND * 1 1860 350 0 0 0 0>
  <INCLSCR INCLSCR1 1 1250 -350 -64 18 0 0 "\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerHBT.lib hbt_typ\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerRES.lib res_typ\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerCAP.lib cap_typ" 1 "" 0 "" 0>
  <NutmegEq NutmegEq1 1 1220 -220 -28 16 0 0 "SP1" 1 "k=(1 - abs(s_1_1)^2 - abs(s_2_2)^2 + abs(s_1_1 * s_2_2 - s_1_2 * s_2_1)^2) / (2 * abs(s_1_2 * s_2_1))" 1 "s11_db=db(s_1_1)" 1 "s12_db=db(s_1_2)" 1 "s21_db=db(s_2_1)" 1 "s22_db=db(s_2_2)" 1>
  <SPfile X11 1 1380 630 -42 -8 0 1 "openEMS/output/run_Basebias_inductor_data/run_Basebias_inductor.s2p" 0 "rectangular" 0 "linear" 0 "short" 0 "2" 0>
  <SPfile X12 1 1410 480 -26 -95 0 0 "openEMS/output/run_BiasT_3dports_data/run_BiasT_3dports.s4p" 0 "rectangular" 0 "linear" 0 "shortall" 0 "4" 0>
  <SPICE X13 1 1860 320 -58 -56 0 0 "openEMS/output/run_Tline_coll_out_data/run_Tline_coll_out_le.spice" 1 "_netp1,_netp2" 0 "yes" 0 "none" 0 "" 0>
  <SPfile X9 1 1800 230 22 -12 0 3 "openEMS/output/run_VCC_snake_v6_data/run_VCC_snake_v6.s2p" 0 "rectangular" 0 "linear" 0 "short" 0 "2" 0>
</Components>
<Wires>
  <1850 580 1880 580 "" 0 0 0 "">
  <1800 110 1800 130 "" 0 0 0 "">
  <1190 450 1260 450 "" 0 0 0 "">
  <2020 320 2030 320 "" 0 0 0 "">
  <1940 200 1940 220 "" 0 0 0 "">
  <1940 110 1940 140 "" 0 0 0 "">
  <1840 610 1840 710 "" 0 0 0 "">
  <2030 420 2030 470 "" 0 0 0 "">
  <1190 660 1190 720 "" 0 0 0 "">
  <2140 320 2140 370 "" 0 0 0 "">
  <2030 320 2140 320 "" 0 0 0 "">
  <2030 320 2030 360 "" 0 0 0 "">
  <1950 320 1960 320 "" 0 0 0 "">
  <1800 190 1800 200 "" 0 0 0 "">
  <1810 510 1840 510 "" 0 0 0 "">
  <1840 510 1840 550 "" 0 0 0 "">
  <1710 510 1750 510 "" 0 0 0 "">
  <1710 510 1710 580 "" 0 0 0 "">
  <1710 580 1810 580 "" 0 0 0 "">
  <1810 450 1830 450 "" 0 0 0 "">
  <1830 400 1830 450 "" 0 0 0 "">
  <1800 400 1830 400 "" 0 0 0 "">
  <1190 560 1190 600 "" 0 0 0 "">
  <1190 450 1190 500 "" 0 0 0 "">
  <2140 430 2140 470 "" 0 0 0 "">
  <1520 530 1550 530 "" 0 0 0 "">
  <1550 510 1550 530 "" 0 0 0 "">
  <1550 510 1590 510 "" 0 0 0 "">
  <1520 450 1590 450 "" 0 0 0 "">
  <1650 450 1690 450 "" 0 0 0 "">
  <1380 510 1380 520 "" 0 0 0 "">
  <1320 450 1380 450 "" 0 0 0 "">
  <1440 450 1460 450 "" 0 0 0 "">
  <1440 510 1450 510 "" 0 0 0 "">
  <1450 510 1450 530 "" 0 0 0 "">
  <1450 530 1460 530 "" 0 0 0 "">
  <1380 580 1380 600 "" 0 0 0 "">
  <1800 320 1830 320 "" 0 0 0 "">
  <1800 260 1800 320 "" 0 0 0 "">
  <1800 320 1800 340 "" 0 0 0 "">
  <1800 110 1800 110 "Vcc" 1830 80 0 "">
  <1190 450 1190 450 "Vin" 1170 410 0 "">
  <2030 320 2030 320 "Vout" 2060 290 0 "">
  <1940 110 1940 110 "Vcc" 1970 80 0 "">
</Wires>
<Diagrams>
  <Tab 2940 1295 807 1270 3 #c0c0c0 1 00 1 0 1 1 1 0 1 1 1 0 1 200 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s11_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.s12_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.s21_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.s22_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.k" #0000ff 0 3 1 0 0>
  </Tab>
  <Rect 2320 730 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 0 1 5 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.k" #ff0000 0 3 0 0 0>
  </Rect>
  <Rect 2340 240 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 -30 5 10 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s11_db" #1a5fb4 1 3 0 0 0>
	  <Mkr 6e+10 89 -53 3 0 0>
  </Rect>
  <Rect 2640 240 240 160 3 #c0c0c0 1 00 1 0 5e+10 2e+11 1 nan 50 0 1 -1 1 1 315 0 225 1 1 0 "" "" "">
	<"ngspice/ac.s12_db" #1a5fb4 0 3 0 0 0>
	  <Mkr 6e+10 88 -54 3 0 0>
  </Rect>
  <Rect 2340 470 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 -50 10 30 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s21_db" #1a5fb4 0 3 0 0 0>
	  <Mkr 6e+10 86 -52 3 0 0>
  </Rect>
  <Rect 2640 470 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 -50 10 10 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s22_db" #1a5fb4 0 3 0 0 0>
	  <Mkr 6e+10 87 -50 3 0 0>
  </Rect>
  <Smith 2649 744 184 184 3 #c0c0c0 1 00 1 0 1 1 1 0 4 1 1 0 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.v(s_1_1)" #613583 0 3 0 0 0>
	  <Mkr 6e+10 11 -185 3 0 0>
  </Smith>
</Diagrams>
<Paintings>
  <Text 1440 -590 14 #000000 0 "ngspice simulation setup">
  <Rectangle 1160 -600 900 560 #000000 1 1 #c0c0c0 1 0>
  <Text 2460 -420 14 #000000 0 "component dimensioning">
  <Rectangle 2280 -430 850 440 #000000 1 1 #c0c0c0 1 0>
  <Text 2540 20 14 #000000 0 "S-parameters">
  <Rectangle 2280 20 630 500 #000000 1 1 #c0c0c0 1 0>
  <Text 2400 530 14 #000000 0 "Stability">
  <Rectangle 2280 530 310 250 #000000 1 1 #c0c0c0 1 0>
  <Text 2680 530 14 #000000 0 "Input matching">
  <Rectangle 2600 530 310 250 #000000 1 1 #c0c0c0 1 0>
</Paintings>
