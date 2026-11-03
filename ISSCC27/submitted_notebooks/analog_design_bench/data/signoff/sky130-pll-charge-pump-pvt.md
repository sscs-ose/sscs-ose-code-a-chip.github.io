A PLL charge pump biased from a 25 µA reference that sources and sinks 50 µA, within 5% over a 0.45 to 1.15 V output
range with at most 2% UP/DN mismatch. DC current and matching are checked at 27 PVT points (tt, ss, ff; 1.62 to
1.98 V; −40 to 125 °C) and in 20 local-mismatch seeds; pulses, switching and power at three of those points.

<div align="center">

| | Spec | Human | GPT-6 Astra | Claude Opus 5.5 |
|---|---|---|---|---|
| UP/DN mismatch, 27 PVT points | ≤ 2% | passes | 0.686% | 0.111% |
| UP/DN mismatch, 20 mismatch seeds | ≤ 2% | 1.14% | 1.09% | **0.655%** |
| Output current, 20 mismatch seeds | 50 µA ± 5% | 50.6 to 51.6 µA | 49.7 to 50.2 µA | 49.8 to 50.2 µA |
| Current flatness over output range | ≤ 1% | passes | 0.288% | 0.0707% |
| Leakage, both controls off | ≤ 1 nA | passes | 0.176 nA | 0.0285 nA |
| Charge error, 10 ns pulse | ≤ 5% | passes | 2.91% | 0.487% |
| Charge error, 1 ns pulse | ≤ 25% | passes | 17.5% | 4.43% |
| Net charge, simultaneous overlap | ≤ 20 fC | passes | 7.49 fC | 4.66 fC |
| Turn-on time to 90% | ≤ 0.5 ns | passes | 0.202 ns | 0.196 ns |
| Power | ≤ 500 µW | passes | 338 µW | 369 µW |
| Transistors | | 25 | **24** | 35 |

</div>
