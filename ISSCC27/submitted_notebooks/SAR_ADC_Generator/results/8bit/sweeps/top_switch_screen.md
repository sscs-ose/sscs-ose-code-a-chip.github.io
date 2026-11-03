Top-plate switch candidates for the 8-bit design: R_top <= 220 Ohm, C_total 4.19 pF, hold 90 ns, LSB 7.03 mV.

| NMOS | PMOS | R_on*Wn, cold worst [kOhm um] | plate leakage per um Wn, hot worst [nA/um] | Wn needed [um] | droop per conversion [LSB] |
|---|---|---|---|---|---|
| LVT N, L 0.3 | SVT P, L 0.3 | 10.38 | 0.126 | 47.2 | 0.018 |
| LVT N, L 0.5 | SVT P, L 0.3 | 13.47 | 0.131 | 61.2 | 0.025 |
| LVT N, L 0.15 | SVT P, L 0.3 | 8.50 | 0.627 | 38.7 | 0.074 |
| SVT N, L 0.3 | SVT P, L 0.3 | 94.30 | 0.0911 | 428.6 | 0.119 |
| SVT N, L 0.15 | SVT P, L 0.3 | 91.43 | 0.149 | 415.6 | 0.189 |
| LVT N, L 0.15 | LVT P, L 0.7 | 7.52 | 91.5 | 34.2 | 9.554 |
| LVT N, L 0.3 | LVT P, L 0.7 | 7.85 | 91.5 | 35.7 | 9.977 |
| LVT N, L 0.15 | SVT P, L 0.15 | 8.49 | 84.7 | 38.6 | 9.987 |
| LVT N, L 0.3 | SVT P, L 0.15 | 9.45 | 84.7 | 43.0 | 11.120 |
| LVT N, L 0.5 | LVT P, L 0.7 | 9.40 | 91.5 | 42.7 | 11.951 |
| LVT N, L 0.5 | SVT P, L 0.15 | 11.95 | 84.7 | 54.3 | 14.057 |
| LVT N, L 0.15 | LVT P, L 0.5 | 6.93 | 332 | 31.5 | 31.992 |
| LVT N, L 0.3 | LVT P, L 0.5 | 7.21 | 332 | 32.8 | 33.290 |
| LVT N, L 0.5 | LVT P, L 0.5 | 8.11 | 332 | 36.9 | 37.428 |
| SVT N, L 0.15 | LVT P, L 0.7 | 37.95 | 91.5 | 172.5 | 48.220 |
| SVT N, L 0.3 | LVT P, L 0.7 | 38.43 | 91.5 | 174.7 | 48.837 |
| SVT N, L 0.15 | SVT P, L 0.15 | 89.97 | 84.7 | 408.9 | 105.816 |
| SVT N, L 0.3 | SVT P, L 0.15 | 92.74 | 84.7 | 421.6 | 109.082 |
| SVT N, L 0.15 | LVT P, L 0.5 | 26.56 | 332 | 120.7 | 122.599 |
| SVT N, L 0.3 | LVT P, L 0.5 | 26.79 | 332 | 121.8 | 123.692 |
| LVT N, L 0.15 | LVT P, L 0.35 | 5.39 | 1.92e+03 | 24.5 | 143.963 |
| LVT N, L 0.3 | LVT P, L 0.35 | 5.56 | 1.92e+03 | 25.3 | 148.472 |
| LVT N, L 0.5 | LVT P, L 0.35 | 6.08 | 1.92e+03 | 27.6 | 162.319 |
| SVT N, L 0.15 | LVT P, L 0.35 | 12.70 | 1.92e+03 | 57.7 | 339.021 |
| SVT N, L 0.3 | LVT P, L 0.35 | 12.76 | 1.92e+03 | 58.0 | 340.460 |

Cold: ss -40 C x1.0, ss +125 C x1.0, tt +27 C x0.9; hot: ff +125 C, fs +125 C, sf +125 C; off-state with the plate 0.89 V above or below Vcm (worst sign).
