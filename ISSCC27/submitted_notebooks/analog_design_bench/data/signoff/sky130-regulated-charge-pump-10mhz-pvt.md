A regulated charge pump clocked at 10 MHz whose output must stay within 5% of 1.3 × VDD with at most 5 mVpp ripple,
driving 1 nF and load currents of 1 to 50 µA. It is checked at eight enabled operating points covering five process
corners, 1.62 to 1.98 V and −10 to 125 °C, plus five power-down points.

<div align="center">

| | Spec | Human | GPT-6 Astra | Claude Opus 5.5 |
|---|---|---|---|---|
| Output voltage, ff, 1.62 V, 125 °C | 1.3 × VDD ± 5% | 2.11 V | 2.11 V | 2.11 V |
| Output ripple | ≤ 5 mVpp | **0.09 mVpp** | 0.51 mVpp | 1.28 mVpp |
| Supply current, enabled | ≤ 200 µA | 123 µA | 168 µA | **113 µA** |
| Supply current, powered down | ≤ 100 nA | 14.9 nA | **0.241 nA** | 1.89 nA |
| Transistors | | 29 | **27** | 43 |

</div>
