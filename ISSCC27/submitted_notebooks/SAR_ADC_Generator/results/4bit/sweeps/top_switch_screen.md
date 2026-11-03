Top-plate switch candidates for the 4-bit design: R_top <= 17136 Ohm, C_total 0.15 pF, hold 83 ns, LSB 112.50 mV.

| NMOS | PMOS | R_on*Wn, cold worst [kOhm um] | plate leakage per um Wn, hot worst [nA/um] | Wn needed [um] | droop per conversion [LSB] |
|---|---|---|---|---|---|
| LVT N, L 0.3 | SVT P, L 0.3 | 10.38 | 0.126 | 0.6 | 0.000 |
| LVT N, L 0.5 | SVT P, L 0.3 | 13.47 | 0.131 | 0.8 | 0.001 |
| LVT N, L 0.15 | SVT P, L 0.3 | 8.50 | 0.627 | 0.5 | 0.002 |
| SVT N, L 0.3 | SVT P, L 0.3 | 94.30 | 0.0911 | 5.5 | 0.002 |
| SVT N, L 0.15 | SVT P, L 0.3 | 91.43 | 0.149 | 5.3 | 0.004 |
| LVT N, L 0.15 | LVT P, L 0.7 | 7.52 | 91.5 | 0.4 | 0.199 |
| LVT N, L 0.3 | LVT P, L 0.7 | 7.85 | 91.5 | 0.5 | 0.208 |
| LVT N, L 0.15 | SVT P, L 0.15 | 8.49 | 84.7 | 0.5 | 0.208 |
| LVT N, L 0.3 | SVT P, L 0.15 | 9.45 | 84.7 | 0.6 | 0.232 |
| LVT N, L 0.5 | LVT P, L 0.7 | 9.40 | 91.5 | 0.5 | 0.249 |
| LVT N, L 0.5 | SVT P, L 0.15 | 11.95 | 84.7 | 0.7 | 0.293 |
| LVT N, L 0.15 | LVT P, L 0.5 | 6.93 | 332 | 0.4 | 0.693 |
| LVT N, L 0.3 | LVT P, L 0.5 | 7.21 | 332 | 0.4 | 0.695 |
| LVT N, L 0.5 | LVT P, L 0.5 | 8.11 | 332 | 0.5 | 0.781 |
| SVT N, L 0.15 | LVT P, L 0.7 | 37.95 | 91.5 | 2.2 | 1.006 |
| SVT N, L 0.3 | LVT P, L 0.7 | 38.43 | 91.5 | 2.2 | 1.019 |
| SVT N, L 0.15 | SVT P, L 0.15 | 89.97 | 84.7 | 5.3 | 2.208 |
| SVT N, L 0.3 | SVT P, L 0.15 | 92.74 | 84.7 | 5.4 | 2.277 |
| SVT N, L 0.15 | LVT P, L 0.5 | 26.56 | 332 | 1.5 | 2.559 |
| SVT N, L 0.3 | LVT P, L 0.5 | 26.79 | 332 | 1.6 | 2.582 |
| LVT N, L 0.15 | LVT P, L 0.35 | 5.39 | 1.92e+03 | 0.4 | 4.009 |
| LVT N, L 0.3 | LVT P, L 0.35 | 5.56 | 1.92e+03 | 0.4 | 4.009 |
| LVT N, L 0.5 | LVT P, L 0.35 | 6.08 | 1.92e+03 | 0.4 | 4.009 |
| SVT N, L 0.15 | LVT P, L 0.35 | 12.70 | 1.92e+03 | 0.7 | 7.076 |
| SVT N, L 0.3 | LVT P, L 0.35 | 12.76 | 1.92e+03 | 0.7 | 7.106 |

Cold: ss -40 C x1.0, ss +125 C x1.0, tt +27 C x0.9; hot: ff +125 C, fs +125 C, sf +125 C; off-state with the plate 0.89 V above or below Vcm (worst sign).
