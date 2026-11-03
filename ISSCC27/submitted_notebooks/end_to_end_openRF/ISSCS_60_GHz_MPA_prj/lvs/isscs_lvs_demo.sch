<Qucs Schematic 25.2.0>
<Properties>
  <View=1456,401,1811,680,4.42478,0,230>
  <Grid=10,10,1>
  <DataSet=isscs_lvs_demo.dat>
  <DataDisplay=isscs_lvs_demo.dpl>
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
  <.PortSym 40 20 1 0 P1>
  <.PortSym 40 60 2 0 P2>
</Symbol>
<Components>
  <Port P1 1 1530 530 -23 12 0 0 "1" 1 "analog" 0>
  <Port P2 1 1690 530 10 12 0 2 "2" 1 "analog" 0>
  <rhigh R1 1 1610 530 -26 12 0 0 "rhigh" 0 "X" 0 "5" 1 "4.3" 1 "0" 0 "sub!" 0 "1" 0 "(1.6e-4 / w + 1360.0*((b + 1)*l + (1.081*(w - 0.04e-6) + 0.18e-6)*b) / (w - 0.04e-6)) / m" 1 "_xml_device_name=rhigh" 0>
</Components>
<Wires>
  <1530 530 1580 530 "" 0 0 0 "">
  <1640 530 1690 530 "" 0 0 0 "">
</Wires>
<Diagrams>
</Diagrams>
<Paintings>
</Paintings>
