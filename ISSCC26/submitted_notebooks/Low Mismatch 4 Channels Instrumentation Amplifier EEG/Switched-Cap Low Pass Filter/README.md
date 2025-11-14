# Switched-Cap Low Pass Filter
For the low-pass filter (LPF) design, the MIMCAP B version was used. This component is not included by default in the gLayout library but was added as an extended version developed by one of the Chipathon participants. The updated MIMCAP B cell can be accessed from the [Mimcap B Repository](https://github.com/ReaLLMASIC/gLayout/pull/54)
## Schematic Design

<p align="center">
  <img src="../Images/LPF_Rev.jpg" alt="LPF_Rev" width="1000"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 1(a). LPF Schematic Inside Chip</h4>

<p align="center">
  <img src="../Images/LPF_EXT_REV.jpg" alt="LPF_EXT_REV" width="1000"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 1(b). LPF Schematic With External Ceramic Capacitor and Inductor</h4>

## Simulation

<p align="center">
  <img src="../Images/TB_LPF1.jpg" alt="TB_LPF1" width="1000"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 2. Switched-Cap Low Pass Filter Testbench</h4>

<p align="center">
  <img src="../Images/TB_LPF2.jpg" alt="TB_LPF2" width="1000"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 3. Noise Analysis (1) Result</h4>

<p align="center">
  <img src="../Images/TB_LPF3.jpg" alt="TB_LPF3" width="400"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 4. Noise Analysis (2) Result</h4>

<p align="center">
  <img src="../Images/TB_LPF4.jpg" alt="TB_LPF4" width="400"/>
</p>
<h4 align="center" style="font-size:16px;">Figure 5. Noise Analysis (3) Result</h4>

## Performance of Designed Switched-Cap Low Pass Filter

<div align="center">

| **Parameter**           | **Value**      | **Unit**   |
|-------------------------|-------------|--------|
| Cutoff Frequency (f<sub>c</sub>)  | <250     | Hz     |
| Clock Frequency (f<sub>clk</sub>) | 4        | kHz     |

Note* : Capacitors have the size of 1u x 1u (m = 3)

</div>
