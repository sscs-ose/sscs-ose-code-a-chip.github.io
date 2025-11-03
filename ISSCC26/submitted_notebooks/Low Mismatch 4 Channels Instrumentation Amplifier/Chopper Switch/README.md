# Chopper Switch
The chopper switch network was also realized using the inverter primitive from gLayout to control the switching transistors.
## Schematic Design

<p align="center">
  <img src="../Images/CSchematic.jpg" alt="SwitchSchem" width="800"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 1. Chopper Switch Schematic</h4>


## Simulation

<p align="center">
  <img src="../Images/CSA_Tb.jpg" alt="SwitchSchem" width="600"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 2. Chopper Switch A Simulation</h4>

<p align="center">
  <img src="../Images/CSB_TB.jpg" alt="SwitchFull" width="600"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 3. Chopper Switch B Simulation</h4>

<p align="center">
  <img src="../Images/CSC_Schematic.jpg" alt="SwitchTb" width="600"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 4. Chopper Switch C Schematic</h4>

<p align="center">
  <img src="../Images/CSC_Tb.jpg" alt="SwitchTb" width="400"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 5. Chopper Switch C Testbench</h4>

<p align="center">
  <img src="../Images/CSC_Tb_Res1.jpg" alt="SwitchTb" width="600"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 6. Chopper Switch C Simulation 1</h4>

<p align="center">
  <img src="../Images/CSC_Tb_Res2.jpg" alt="SwitchTb" width="450"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 7. Chopper Switch C Simulation 2</h4>

<p align="center">
  <img src="../Images/CS_Spec.jpg" alt="SwitchTb" width="800"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 8. Chopper Switch Specification</h4>

## Performance of Designed Chopper Switch 

<div align="center">

| **Parameter**                        | **Value / Target** | **Unit** |
|-------------------------------------|--------------------|----------|
| Stage 1 : Chopper A Operating Frequency       | 4              | kHz       |
| Stage 2 : Chopper B Operating Frequency       | 2            | kHz       |
| Stage 3 : Chopper C Operating Frequency       | 1               | kHz       |
| R<sub>on</sub>                                 | 894 (3 ways)                | kΩ       |
| Delay Time Between stages | +/-500              | ns       |
| Off Leakage Current | +/- 4 | pA
| Clock divider (to _Clk and Clk) delay | 0.000101512 | s

## Layout
<p align="center">
  <img src="../Images/CS_Layout.jpg" alt="SwitchTb" width="800"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 9. Chopper Switch Layout</h4>

## Post-PEX
<p align="center">
  <img src="../Images/CS_Post-Pex.jpg" alt="SwitchTb" width="800"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 10. Chopper Switch Post-Pex</h4>
</div>
