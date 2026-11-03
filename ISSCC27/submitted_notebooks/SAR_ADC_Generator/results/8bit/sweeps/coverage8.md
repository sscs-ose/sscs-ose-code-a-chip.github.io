| input frequency | ENOB | SNDR [dB] | SFDR [dB] |
|---|---|---|---|
| 0.023 fs (0.23 MHz) | 8.03 | 50.1 | 60.6 |
| 0.102 fs (1.02 MHz) | 7.98 | 49.8 | 60.6 |
| 0.242 fs (2.42 MHz) | 7.99 | 49.8 | 59.1 |
| 0.367 fs (3.67 MHz) | 7.94 | 49.5 | 61.8 |
| 0.461 fs (4.61 MHz) | 7.91 | 49.4 | 61.2 |
| 0.492 fs (4.92 MHz) | 7.85 | 49.0 | 58.5 |

| PVT point | ENOB | DNL [LSB] | INL [LSB] | offset [LSB] | gain [LSB] | power [uW] |
|---|---|---|---|---|---|---|
| ss -40C 1.80V | 7.86 | 0.247 | 0.209 | -1.12 | -0.51 | 186 |
| ff +125C 1.80V | 6.52 | 1.000 | 2.885 | -1.50 | +0.87 | 312 |
| fs +125C 1.80V | 5.78 | 1.008 | 6.020 | -1.50 | +0.87 | 431 |
| sf -40C 1.80V | 7.68 | 0.247 | 0.401 | -1.37 | -1.02 | 177 |
| tt +27C 1.62V | 8.00 | 0.255 | 0.213 | -0.87 | -0.26 | 150 |

Schematic, fixed 8-bit design at 10 MS/s; PVT points use 4 hits per code (DNL/INL/offset/gain resolved to 1/4 LSB), FFT 128 points.
