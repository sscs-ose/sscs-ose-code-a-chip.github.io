# 4-bit SAR ADC - generated report

**Spec:** 4 bit, 10 MS/s, Vref = 1.8 V, LSB = 112.50 mV, SKY130 tt, 27.0 C

## Sizing
| block | rule | numbers | result |
|---|---|---|---|
| spec | LSB = Vref / 2^N | 1.8 V / 16 | **112.50 mV** |
| timing | Tclk = 1 / ((N + 2) * fs) | fs = 10 MS/s, 6 cycles | **16.67 ns (60.0 MHz)** |
| CDAC | sigma_DNL(mid-code) = sqrt(2^N - 1) * sigma_u <= DNL_3sigma / 3 | sigma_u <= 4.303 %, A_C = 2.8 %um | **side >= 0.65 um (matching)** |
| CDAC | kT/C: sqrt(kT / C_total) <= noise_lsb * LSB | C_total >= 0.0327 fF | **negligible at this resolution** |
| CDAC | Cu = Ca * s^2 + Cp * 4s (characterized MIM) | s = 2.00 um, limited by min. size | **Cu = 9.32 fF, C_total = 149.1 fF** |
| comparator | offset only shifts the transfer curve here (no DNL/INL): spec = offset error | 3 sigma_os <= 1.0 LSB | **sigma_os <= 37.50 mV** |
| comparator | sigma_os ~ A_VT / sqrt(W L) <= offset_3sigma * LSB / 3 | A_VT = 7.38 mVum, target 37.50 mV | **W L >= 0.039 um^2 -> W/L = 2.0/0.3 (est. 9.52 mV)** |
| comparator | pre-amplifier needed if W L > 20 um^2 (input cap / kick-back) | W L = 0.04 um^2 | **no - StrongARM alone** |
| comparator | tail = 1.5 W_in, latch = W_in / 2, reset / inverters fixed |  | **tail 3.0, nlatch 1.0, platch 1.0 um** |
| sampling | TG device flavour = lowest worst-case R_on W (ss/-40C, ss/125C, tt/-10% supply) | std: 434.9 kOhm um, lvt: 7.4 kOhm um, mix: 13.3 kOhm um, mixp: 112.4 kOhm um, mixl: 262.7 kOhm um, lvtp5: 12.7 kOhm um, lvtp7: 17.9 kOhm um, lvtp10: 23.9 kOhm um | **lvt transistors** |
| sampling | tau = T_track / ln(2^N / settle_lsb); 1/4 bit switch, 3/4 top switch | T_track = 14.17 ns, tau <= 3406 ps | **R_unit <= 91.4 kOhm, R_top <= 17136 Ohm** |
| sampling | W_n = (R_on W)_TG,worst / R  (Wp = 2 Wn), bit-i switch = 2^i units | worst (R_on W) = 7.45 kOhm um (ss -40C 1.80V) | **unit TG 0.45/0.90 um** |
| sampling | top-plate switch: sized at Vcm; least hot-leakage flavour among those <= 4x the narrowest (plate droop per conversion, ff 125C, fs 125C, plate Vref/2^(k+1) from Vcm while bit k is tried; budget 0.25 LSB) | std: 5.3 um, 0.53 LSB, lvt: 0.5 um, 0.97 LSB, mix: 0.8 um, 1.6 LSB, mixp: 0.5 um, 0.05 LSB, mixl: 0.7 um, 9.3e-05 LSB, lvtp5: 0.5 um, 0.17 LSB, lvtp7: 0.5 um, 0.05 LSB, lvtp10: 0.5 um, 0.021 LSB | **mixl: top TG 0.65/1.30 um (10.38 kOhm um at Vcm, 0.000 LSB)** |
| DAC driver | tau = 0.45 Tclk / ln(2^N / settle_lsb), per unit cap (binary scaled) | tau <= 1803 ps, R_unit <= 96.8 kOhm | **unit NMOS 0.45 um, unit PMOS 0.45 um** |

## Results (transistor level, pre-layout)
| metric | value |
|---|---|
| ENOB (FFT, 1.016 MHz) | **3.97 bit** (ideal quantizer: 3.97) |
| SNDR / SFDR / THD | 25.68 dB / 35.7 dB / -32.3 dB |
| max DNL / INL (histogram) | 0.095 / 0.085 LSB |
| max DNL / INL (transition levels) | 0.096 / 0.092 LSB |
| missing codes | 0 |
| offset / gain error | -0.155 / -0.021 LSB |
| comparator offset sigma (MC, n=192) | 8.64 mV (0.077 LSB) |
| power (comparator + CDAC + switches + SAR logic cells) | 13.88 uW |
| energy / conversion | 1.388 pJ |
| Walden FoM | 88.4 fJ/conv-step |
| MC (1000 runs) 99th-pct DNL / INL | 0.130 / 0.083 LSB |
| MC yield (max DNL < 0.5 LSB) | 100.0 % |

Runtime: 381 s
