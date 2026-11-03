<Qucs Schematic 25.2.0>
<Properties>
  <View=10,-443,2779,371,0.964396,1378,0>
  <Grid=10,10,1>
  <DataSet=02_preEM_60GHz_MPA_ngspice.dat>
  <DataDisplay=02_preEM_60GHz_MPA_ngspice.dpl>
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
  <Lib npn13G2 1 1810 450 10 64 0 0 "/home/pedersen/.qucs/user_lib/IHP_PDK_nonlinear_components" 0 "npn13G2" 0 "10" 1>
  <IProbe Icollector 1 1810 340 -109 -22 1 3>
  <GND * 1 1810 580 0 0 0 0>
  <GND * 1 1850 450 0 0 0 0>
  <GND * 1 2040 420 0 0 0 0>
  <Vdc V1 1 1500 690 18 -26 0 1 "0.98" 1>
  <GND * 1 1500 720 0 0 0 0>
  <INDQ LQ1 1 1500 630 27 -28 0 3 "83.0907pH" 1 "13" 1 "50e9" 0 "Linear" 0 "26.85" 0>
  <IProbe Iin 1 1310 530 16 -26 0 1>
  <IProbe Iout 1 1970 270 -26 16 0 0>
  <GND * 1 1950 140 0 0 0 0>
  <Vdc V2 1 1950 90 18 -26 0 1 "1.65V" 1>
  <R R2 1 2040 350 15 -26 0 1 "50 Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <IProbe Idc_in 1 1810 80 18 -26 1 3>
  <IProbe Ibase 1 1730 450 -26 16 0 0>
  <GND * 1 1310 720 0 0 0 0>
  <.SP SP1 1 1050 -570 0 56 0 0 "lin" 1 "1 GHz" 1 "200 GHz" 1 "200" 1 "no" 0 "1" 0 "2" 0 "no" 0 "no" 0>
  <GND * 1 2140 420 0 0 0 0>
  <INDQ LQ2 1 1810 180 17 -26 0 1 "2.5nH" 1 "8" 1 "100 MHz" 0 "Linear" 0 "26.85" 0>
  <rhigh R1_dim 0 2360 -340 -26 12 0 0 "rhigh" 0 "X" 0 "5" 1 "12.7" 1 "0" 0 "sub!" 0 "1" 0 "(1.6e-4 / w + 1360.0*((b + 1)*l + (1.081*(w - 0.04e-6) + 0.18e-6)*b) / (w - 0.04e-6)) / m" 1 "_xml_device_name=rhigh" 0>
  <GND * 1 1610 560 0 0 0 0>
  <GND * 1 1610 480 0 0 0 0>
  <Lib cap_rfcmim3 1 1900 270 -38 54 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "20.0u" 1 "20.0u" 1>
  <GND * 1 1900 300 0 0 0 0>
  <GND * 1 1410 480 0 0 0 0>
  <Pac P1 1 1310 630 18 -26 0 1 "1" 1 "50 Ohm" 1 "0 dBm" 1 "60 GHz" 1 "26.85" 0 "true" 0>
  <Pac P2 1 2140 350 18 -26 0 1 "2" 1 "50 Ohm" 1 "0 dBm" 1 "60 GHz" 1 "26.85" 0 "true" 0>
  <Lib rhigh1 1 1610 530 43 -9 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "rhigh" 0 "5u" 1 "12.7u" 1 "1" 1>
  <Lib cap_rfcmim1 1 1410 450 -26 -96 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "4.9u" 1 "4.9u" 1>
  <Lib cap_rfcmim2 1 1610 450 -39 -87 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "6.05u" 1 "8u" 1>
  <NutmegEq NutmegEq1 1 1080 -280 -28 16 0 0 "SP1" 1 "k=(1 - abs(s_1_1)^2 - abs(s_2_2)^2 + abs(s_1_1 * s_2_2 - s_1_2 * s_2_1)^2) / (2 * abs(s_1_2 * s_2_1))" 1 "s11_db=db(s_1_1)" 1 "s12_db=db(s_1_2)" 1 "s21_db=db(s_2_1)" 1 "s22_db=db(s_2_2)" 1>
  <INCLSCR INCLSCR1 1 1110 -410 -64 18 0 0 "\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerHBT.lib hbt_typ\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerRES.lib res_typ\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/ngspice/models/cornerCAP.lib cap_typ" 1 "" 0 "" 0>
  <rfcmim cap_rfcmim1_dim 0 2360 -170 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "4.9" 1 "4.9" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <rfcmim cap_rfcmim3_dim 0 2730 -170 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "20" 1 "20" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <rfcmim cap_rfcmim2_dim 0 2560 -170 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "6.05" 1 "8" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
</Components>
<Wires>
  <1820 450 1850 450 "" 0 0 0 "">
  <1810 30 1810 50 "" 0 0 0 "">
  <1500 450 1500 600 "" 0 0 0 "">
  <1440 450 1500 450 "" 0 0 0 "">
  <2000 270 2040 270 "" 0 0 0 "">
  <1950 120 1950 140 "" 0 0 0 "">
  <1950 30 1950 60 "" 0 0 0 "">
  <1810 480 1810 580 "" 0 0 0 "">
  <2040 380 2040 420 "" 0 0 0 "">
  <1310 560 1310 600 "" 0 0 0 "">
  <1310 660 1310 720 "" 0 0 0 "">
  <2140 270 2140 320 "" 0 0 0 "">
  <2040 270 2140 270 "" 0 0 0 "">
  <2040 270 2040 320 "" 0 0 0 "">
  <1930 270 1940 270 "" 0 0 0 "">
  <1810 210 1810 270 "" 0 0 0 "">
  <1810 110 1810 150 "" 0 0 0 "">
  <1810 270 1810 310 "" 0 0 0 "">
  <1810 270 1870 270 "" 0 0 0 "">
  <1500 450 1580 450 "" 0 0 0 "">
  <1580 450 1580 530 "" 0 0 0 "">
  <1640 450 1640 530 "" 0 0 0 "">
  <1640 450 1700 450 "" 0 0 0 "">
  <1760 450 1780 450 "" 0 0 0 "">
  <1810 370 1810 420 "" 0 0 0 "">
  <1310 450 1310 500 "" 0 0 0 "">
  <1310 450 1380 450 "" 0 0 0 "">
  <2140 380 2140 420 "" 0 0 0 "">
  <1810 30 1810 30 "Vcc" 1840 0 0 "">
  <2040 270 2040 270 "Vout" 2070 240 0 "">
  <1950 30 1950 30 "Vcc" 1980 0 0 "">
  <1310 450 1310 450 "Vin" 1290 410 0 "">
</Wires>
<Diagrams>
  <Tab 2950 1295 807 1270 3 #c0c0c0 1 00 1 0 1 1 1 0 1 1 1 0 1 200 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s11_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.s12_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.s21_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.s22_db" #0000ff 0 3 1 0 0>
	<"ngspice/ac.k" #0000ff 0 3 1 0 0>
  </Tab>
  <Rect 2330 730 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 0 1 5 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.k" #ff0000 0 3 0 0 0>
  </Rect>
  <Rect 2350 240 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 -30 5 10 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s11_db" #1a5fb4 1 3 0 0 0>
	  <Mkr 6e+10 89 -53 3 0 0>
  </Rect>
  <Rect 2650 240 240 160 3 #c0c0c0 1 00 1 0 5e+10 2e+11 1 nan 50 0 1 -1 1 1 315 0 225 1 1 0 "" "" "">
	<"ngspice/ac.s12_db" #1a5fb4 0 3 0 0 0>
	  <Mkr 6e+10 88 -54 3 0 0>
  </Rect>
  <Rect 2350 470 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 -50 10 30 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s21_db" #1a5fb4 0 3 0 0 0>
	  <Mkr 6e+10 86 -52 3 0 0>
  </Rect>
  <Rect 2650 470 240 160 3 #c0c0c0 1 00 0 0 5e+10 2e+11 0 -50 10 10 1 -1 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.s22_db" #1a5fb4 0 3 0 0 0>
	  <Mkr 6e+10 87 -50 3 0 0>
  </Rect>
  <Smith 2659 744 184 184 3 #c0c0c0 1 00 1 0 1 1 1 0 4 1 1 0 1 1 315 0 225 1 0 0 "" "" "">
	<"ngspice/ac.v(s_1_1)" #613583 0 3 0 0 0>
	  <Mkr 6e+10 11 -185 3 0 0>
  </Smith>
</Diagrams>
<Paintings>
  <Text 1060 -620 14 #000000 0 "ngspice simulation setup">
  <Rectangle 1020 -630 900 560 #000000 1 1 #c0c0c0 1 0>
  <Text 2470 -420 14 #000000 0 "component dimensioning">
  <Rectangle 2290 -430 850 440 #000000 1 1 #c0c0c0 1 0>
  <Text 2550 20 14 #000000 0 "S-parameters">
  <Rectangle 2290 20 630 500 #000000 1 1 #c0c0c0 1 0>
  <Text 2410 530 14 #000000 0 "Stability">
  <Rectangle 2290 530 310 250 #000000 1 1 #c0c0c0 1 0>
  <Text 2690 530 14 #000000 0 "Input matching">
  <Rectangle 2610 530 310 250 #000000 1 1 #c0c0c0 1 0>
</Paintings>
