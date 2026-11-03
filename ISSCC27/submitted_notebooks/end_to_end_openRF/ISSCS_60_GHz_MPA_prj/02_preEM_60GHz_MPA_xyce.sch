<Qucs Schematic 25.2.0>
<Properties>
  <View=848,-491,2921,801,0.986643,130,498>
  <Grid=10,10,1>
  <DataSet=02_preEM_60GHz_MPA_xyce.dat>
  <DataDisplay=02_preEM_60GHz_MPA_xyce.dpl>
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
  <Lib npn13G2 1 1680 450 10 64 0 0 "/home/pedersen/.qucs/user_lib/IHP_PDK_nonlinear_components" 0 "npn13G2" 0 "10" 1>
  <IProbe Icollector 1 1680 340 -83 -46 1 3>
  <GND * 1 1680 580 0 0 0 0>
  <GND * 1 1910 420 0 0 0 0>
  <Vdc V1 1 1260 730 18 -26 0 1 "0.98" 1>
  <GND * 1 1260 760 0 0 0 0>
  <INDQ LQ1 1 1260 630 40 -27 0 3 "83.0907pH" 1 "13" 1 "50e9" 0 "Linear" 0 "26.85" 0>
  <IProbe Iin 1 1070 530 16 -26 0 1>
  <IProbe Iout 1 1840 270 -26 16 0 0>
  <GND * 1 1820 160 0 0 0 0>
  <Vdc V2 1 1820 110 18 -26 0 1 "1.65V" 1>
  <R R2 1 1910 340 15 -26 0 1 "50 Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "US" 0>
  <R R3 1 1130 620 15 -26 0 1 "50 Ohm" 1 "26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "european" 0>
  <GND * 1 1070 760 0 0 0 0>
  <IProbe Idc_in 1 1680 100 18 -26 1 3>
  <IProbe Ibase 1 1600 450 -26 16 0 0>
  <SpicePar SpicePar1 1 1130 710 -28 16 0 0 "Irf_in=0.02" 1>
  <INDQ LQ2 1 1680 200 17 -26 0 1 "2.5 nH" 1 "8" 1 "100 MHz" 0 "Linear" 0 "26.85" 0>
  <Lib cap_rfcmim3 1 1770 270 -38 54 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "20.0u" 1 "20.0u" 1>
  <GND * 1 1770 300 0 0 0 0>
  <GND * 1 1370 560 0 0 0 0>
  <Lib rhigh1 1 1370 530 50 -6 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "rhigh" 0 "5u" 1 "12.7u" 1 "1" 1>
  <GND * 1 1370 480 0 0 0 0>
  <VProbe Vbase 1 1560 340 -74 -31 1 2>
  <GND * 1 1550 360 0 0 0 0>
  <VProbe Vcollector 1 1760 410 -18 26 0 3>
  <GND * 1 1740 420 0 0 0 3>
  <INCLSCR INCLSCR1 1 2130 40 -64 18 0 0 "\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/xyce/models/cornerHBT.lib hbt_typ\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/xyce/models/cornerRES.lib res_typ\n.LIB /home/matthi/IHP_PDK/IHP-Open-PDK/ihp-sg13g2/libs.tech/xyce/models/cornerCAP.lib cap_typ" 1 "" 0 "" 0>
  <rsil R9 0 2500 -390 -26 12 0 0 "rsil" 0 "X" 0 "0.5" 1 "0.5" 1 "0" 0 "sub!" 0 "1" 0 "(9.0e-6 / w + 7.0 * ((b + 1)*l + (1.081*(w + 1.0e-8) + 0.18e-6)*b) / (w + 1.0e-8)) / m" 1 "_xml_device_name=rsil" 0>
  <cmim C1 0 2130 -220 -26 15 0 0 "cap_cmim" 0 "X" 0 "7.0" 1 "7.0" 1 "1" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "_xml_device_name=cap_cmim" 0>
  <rppd R10 0 2130 -390 -26 12 0 0 "rppd" 0 "X" 0 "10" 1 "0.5" 1 "0" 0 "sub!" 0 "1" 0 "(70.0e-6 / w + 260.0 * ((b + 1)*l + (1.081*(w + 6.0e-9) + 0.18e-6)*b) / (w + 6.0e-9)) / m" 1 "_xml_device_name=rppd" 0>
  <rhigh R1_dim1 0 2300 -390 -26 12 0 0 "rhigh" 0 "X" 0 "5" 1 "12.7" 1 "0" 0 "sub!" 0 "1" 0 "(1.6e-4 / w + 1360.0*((b + 1)*l + (1.081*(w - 0.04e-6) + 0.18e-6)*b) / (w - 0.04e-6)) / m" 1 "_xml_device_name=rhigh" 0>
  <rfcmim cap_rfcmim1_dim1 0 2500 -220 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "5" 1 "10.0" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <rfcmim cap_rfcmim2_dim1 0 2700 -220 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "20" 1 "20" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <rfcmim cap_rfcmim3_dim1 0 2300 -220 -26 24 0 0 "cap_rfcmim" 0 "X" 0 "5" 1 "7" 1 "sub!" 0 "3.0" 1 "m*((w*l*1.e-3) + 2*(w+l)*40e-12)" 1 "1" 0 "_xml_device_name=cap_rfcmim" 0>
  <Lib cap_rfcmim1 1 1170 450 -26 -96 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "4.9u" 1 "4.9u" 1>
  <GND * 1 1170 480 0 0 0 0>
  <GND * 1 1690 450 0 0 0 1>
  <Lib cap_rfcmim2 1 1370 450 -45 -87 0 1 "/home/matthi/QucsWorkspace/user_lib/IHP_PDK_basic_components" 0 "cap_rfcmim" 0 "6.05u" 1 "8.0u" 1>
  <.XYCESCR XYCESCR1 1 2070 190 0 34 0 0 "\n* --- Analysis type definition ---\n.HB 60G\n\n\n* --- HB solver options ---\n.options hbint; This is a comment\n+ numfreq=10\n+ STARTUPPERIODS=2 ; default: 2\n+ numtpts=100 ; default: numfreq\n\n\n* --- DCOP nonlinear solver options ---\n.options nonlin \n+ abstol=1e-9 ; default: 1e-9\n+ reltol=1e-4 ; default: 1e-4\n\n* --- HB nonlinear solver options ---\n\n\n* --- HB linear solver options ---\n\n\n* --- Parameter sweep ---\n.STEP LIN Irf_in 0.1e-3 35e-3 3.98e-4\n\n\n* --- Print output ---\n.PRINT HB\n+ FORMAT=TECPLOT\n+ FILE=/home/matthi/QucsWorkspace/ISSCS_60_GHz_MPA_prj/02_preEM_60GHz_MPA_xyce.txt\n+ I(VIin) I(VIbase) I(VIout) V(Vin) V(Vbase) V(Vout) V(Vcc) I(VIdc_in) I(VIcollector) V(Vcollector)\n" 1 "" 0 "ac.txt" 0>
  <Iac I1 1 1040 620 20 -26 0 1 "Irf_in" 1 "60e9" 1 "0" 0 "0" 0 "0" 0 "0" 0>
</Components>
<Wires>
  <1680 50 1680 70 "" 0 0 0 "">
  <1400 450 1570 450 "" 0 0 0 "">
  <1400 450 1400 530 "" 0 0 0 "">
  <1340 450 1340 530 "" 0 0 0 "">
  <1260 450 1340 450 "" 0 0 0 "">
  <1260 660 1260 700 "" 0 0 0 "">
  <1260 450 1260 600 "" 0 0 0 "">
  <1200 450 1260 450 "" 0 0 0 "">
  <1870 270 1910 270 "" 0 0 0 "">
  <1820 140 1820 160 "" 0 0 0 "">
  <1820 50 1820 80 "" 0 0 0 "">
  <1680 480 1680 580 "" 0 0 0 "">
  <1910 370 1910 420 "" 0 0 0 "">
  <1910 270 1910 310 "" 0 0 0 "">
  <1680 270 1680 310 "" 0 0 0 "">
  <1800 270 1810 270 "" 0 0 0 "">
  <1680 230 1680 270 "" 0 0 0 "">
  <1680 270 1740 270 "" 0 0 0 "">
  <1680 130 1680 170 "" 0 0 0 "">
  <1680 370 1680 400 "" 0 0 0 "">
  <1070 560 1070 570 "" 0 0 0 "">
  <1070 670 1070 760 "" 0 0 0 "">
  <1040 570 1040 590 "" 0 0 0 "">
  <1070 570 1130 570 "" 0 0 0 "">
  <1040 570 1070 570 "" 0 0 0 "">
  <1040 670 1070 670 "" 0 0 0 "">
  <1070 670 1130 670 "" 0 0 0 "">
  <1130 570 1130 590 "" 0 0 0 "">
  <1070 450 1070 500 "" 0 0 0 "">
  <1070 450 1140 450 "" 0 0 0 "">
  <1040 650 1040 670 "" 0 0 0 "">
  <1130 650 1130 670 "" 0 0 0 "">
  <1570 360 1570 450 "" 0 0 0 "">
  <1680 400 1740 400 "" 0 0 0 "">
  <1630 450 1650 450 "" 0 0 0 "">
  <1680 400 1680 420 "" 0 0 0 "">
  <1680 50 1680 50 "Vcc" 1710 20 0 "">
  <1910 270 1910 270 "Vout" 1930 230 0 "">
  <1820 50 1820 50 "Vcc" 1850 20 0 "">
  <1070 450 1070 450 "Vin" 1070 410 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
  <Text 2320 0 14 #000000 0 "Xyce simulation setup">
  <Rectangle 2050 -10 870 810 #000000 1 1 #c0c0c0 1 0>
  <Text 2240 -480 14 #000000 0 "Component dimensioning">
  <Rectangle 2060 -490 850 440 #000000 1 1 #c0c0c0 1 0>
</Paintings>
