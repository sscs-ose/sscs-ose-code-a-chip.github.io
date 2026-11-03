Top-plate switch candidates for the 6-bit design: R_top <= 2410 Ohm, C_total 0.60 pF, hold 88 ns, LSB 28.12 mV.

| NMOS | PMOS | R_on*Wn, cold worst [kOhm um] | plate leakage per um Wn, hot worst [nA/um] | Wn needed [um] | droop per conversion [LSB] |
|---|---|---|---|---|---|
| LVT N, L 0.3 | SVT P, L 0.3 | 10.38 | 0.126 | 4.3 | 0.003 |
| LVT N, L 0.5 | SVT P, L 0.3 | 13.47 | 0.131 | 5.6 | 0.004 |
| LVT N, L 0.15 | SVT P, L 0.3 | 8.50 | 0.627 | 3.5 | 0.012 |
| SVT N, L 0.3 | SVT P, L 0.3 | 94.30 | 0.0911 | 39.1 | 0.019 |
| SVT N, L 0.15 | SVT P, L 0.3 | 91.43 | 0.149 | 37.9 | 0.029 |
| LVT N, L 0.15 | LVT P, L 0.7 | 7.52 | 91.5 | 3.1 | 1.489 |
| LVT N, L 0.3 | LVT P, L 0.7 | 7.85 | 91.5 | 3.3 | 1.555 |
| LVT N, L 0.15 | SVT P, L 0.15 | 8.49 | 84.7 | 3.5 | 1.556 |
| LVT N, L 0.3 | SVT P, L 0.15 | 9.45 | 84.7 | 3.9 | 1.733 |
| LVT N, L 0.5 | LVT P, L 0.7 | 9.40 | 91.5 | 3.9 | 1.862 |
| LVT N, L 0.5 | SVT P, L 0.15 | 11.95 | 84.7 | 5.0 | 2.190 |
| LVT N, L 0.15 | LVT P, L 0.5 | 6.93 | 332 | 2.9 | 4.985 |
| LVT N, L 0.3 | LVT P, L 0.5 | 7.21 | 332 | 3.0 | 5.187 |
| LVT N, L 0.5 | LVT P, L 0.5 | 8.11 | 332 | 3.4 | 5.832 |
| SVT N, L 0.15 | LVT P, L 0.7 | 37.95 | 91.5 | 15.7 | 7.514 |
| SVT N, L 0.3 | LVT P, L 0.7 | 38.43 | 91.5 | 15.9 | 7.610 |
| SVT N, L 0.15 | SVT P, L 0.15 | 89.97 | 84.7 | 37.3 | 16.488 |
| SVT N, L 0.3 | SVT P, L 0.15 | 92.74 | 84.7 | 38.5 | 16.997 |
| SVT N, L 0.15 | LVT P, L 0.5 | 26.56 | 332 | 11.0 | 19.103 |
| SVT N, L 0.3 | LVT P, L 0.5 | 26.79 | 332 | 11.1 | 19.273 |
| LVT N, L 0.15 | LVT P, L 0.35 | 5.39 | 1.92e+03 | 2.2 | 22.432 |
| LVT N, L 0.3 | LVT P, L 0.35 | 5.56 | 1.92e+03 | 2.3 | 23.134 |
| LVT N, L 0.5 | LVT P, L 0.35 | 6.08 | 1.92e+03 | 2.5 | 25.292 |
| SVT N, L 0.15 | LVT P, L 0.35 | 12.70 | 1.92e+03 | 5.3 | 52.825 |
| SVT N, L 0.3 | LVT P, L 0.35 | 12.76 | 1.92e+03 | 5.3 | 53.049 |

Cold: ss -40 C x1.0, ss +125 C x1.0, tt +27 C x0.9; hot: ff +125 C, fs +125 C, sf +125 C; off-state with the plate 0.89 V above or below Vcm (worst sign).
