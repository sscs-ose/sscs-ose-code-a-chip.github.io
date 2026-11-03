| block | rule | numbers | result |
|---|---|---|---|
| spec | LSB = Vref / 2^N | 1.8 V / 256 | **7.03 mV** |
| timing | Tclk = 1 / ((N + 2) * fs) | fs = 10 MS/s, 10 cycles | **10.00 ns (100.0 MHz)** |
| CDAC | sigma_DNL(mid-code) = sqrt(2^N - 1) * sigma_u <= DNL_3sigma / 3 | sigma_u <= 1.044 %, A_C = 2.8 %um | **side >= 2.68 um (matching)** |
| CDAC | kT/C: sqrt(kT / C_total) <= noise_lsb * LSB | C_total >= 8.38 fF | **side >= 0.04 um (noise)** |
| CDAC | Cu = Ca * s^2 + Cp * 4s (characterized MIM) | s = 2.70 um, limited by matching | **Cu = 16.36 fF, C_total = 4188.0 fF** |
| comparator | offset only shifts the transfer curve here (no DNL/INL): spec = offset error | 3 sigma_os <= 1.0 LSB | **sigma_os <= 2.34 mV** |
| comparator | sigma_os ~ A_VT / sqrt(W L) <= offset_3sigma * LSB / 3 | A_VT = 7.38 mVum, target 2.34 mV | **W L >= 9.909 um^2 -> W/L = 33.1/0.3 (est. 2.34 mV)** |
| comparator | pre-amplifier needed if W L > 20 um^2 (input cap / kick-back) | W L = 9.91 um^2 | **no - StrongARM alone** |
| comparator | tail = 1.5 W_in, latch = W_in / 2, reset / inverters fixed |  | **tail 49.7, nlatch 16.6, platch 16.6 um** |
| sampling | TG device flavour = lowest worst-case R_on W (ss/-40C, ss/125C, tt/-10% supply) | std: 434.9 kOhm um, lvt: 7.4 kOhm um, mix: 13.3 kOhm um, mixp: 112.4 kOhm um, mixl: 262.7 kOhm um, lvtp5: 12.7 kOhm um, lvtp7: 17.9 kOhm um, lvtp10: 23.9 kOhm um | **lvt transistors** |
| sampling | tau = T_track / ln(2^N / settle_lsb); 1/4 bit switch, 3/4 top switch | T_track = 8.50 ns, tau <= 1226 ps | **R_unit <= 18.7 kOhm, R_top <= 220 Ohm** |
| sampling | W_n = (R_on W)_TG,worst / R  (Wp = 2 Wn), bit-i switch = 2^i units | worst (R_on W) = 7.45 kOhm um (ss -40C 1.80V) | **unit TG 0.45/0.90 um** |
| sampling | top-plate switch: sized at Vcm; least hot-leakage flavour among those <= 4x the narrowest (plate droop per conversion, ff 125C, fs 125C, plate Vref/2^(k+1) from Vcm while bit k is tried; budget 0.25 LSB) | std: 409.7 um, 14 LSB, lvt: 24.6 um, 18 LSB, mix: 57.9 um, 42 LSB, mixp: 38.7 um, 1.3 LSB, mixl: 47.3 um, 0.0027 LSB, lvtp5: 31.6 um, 4.2 LSB, lvtp7: 34.2 um, 1.3 LSB, lvtp10: 35.6 um, 0.51 LSB | **mixl: top TG 47.30/94.60 um (10.38 kOhm um at Vcm, 0.003 LSB)** |
| DAC driver | tau = 0.45 Tclk / ln(2^N / settle_lsb), per unit cap (binary scaled) | tau <= 649 ps, R_unit <= 19.8 kOhm | **unit NMOS 0.45 um, unit PMOS 0.45 um** |