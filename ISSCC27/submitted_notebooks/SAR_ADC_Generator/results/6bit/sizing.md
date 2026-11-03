| block | rule | numbers | result |
|---|---|---|---|
| spec | LSB = Vref / 2^N | 1.8 V / 64 | **28.12 mV** |
| timing | Tclk = 1 / ((N + 2) * fs) | fs = 10 MS/s, 8 cycles | **12.50 ns (80.0 MHz)** |
| CDAC | sigma_DNL(mid-code) = sqrt(2^N - 1) * sigma_u <= DNL_3sigma / 3 | sigma_u <= 2.100 %, A_C = 2.8 %um | **side >= 1.33 um (matching)** |
| CDAC | kT/C: sqrt(kT / C_total) <= noise_lsb * LSB | C_total >= 0.524 fF | **side >= 0.01 um (noise)** |
| CDAC | Cu = Ca * s^2 + Cp * 4s (characterized MIM) | s = 2.00 um, limited by min. size | **Cu = 9.32 fF, C_total = 596.3 fF** |
| comparator | offset only shifts the transfer curve here (no DNL/INL): spec = offset error | 3 sigma_os <= 1.0 LSB | **sigma_os <= 9.38 mV** |
| comparator | sigma_os ~ A_VT / sqrt(W L) <= offset_3sigma * LSB / 3 | A_VT = 7.38 mVum, target 9.38 mV | **W L >= 0.619 um^2 -> W/L = 2.1/0.3 (est. 9.29 mV)** |
| comparator | pre-amplifier needed if W L > 20 um^2 (input cap / kick-back) | W L = 0.62 um^2 | **no - StrongARM alone** |
| comparator | tail = 1.5 W_in, latch = W_in / 2, reset / inverters fixed |  | **tail 3.2, nlatch 1.1, platch 1.1 um** |
| sampling | TG device flavour = lowest worst-case R_on W (ss/-40C, ss/125C, tt/-10% supply) | std: 434.9 kOhm um, lvt: 7.4 kOhm um, mix: 13.3 kOhm um, mixp: 112.4 kOhm um, mixl: 262.7 kOhm um, lvtp5: 12.7 kOhm um, lvtp7: 17.9 kOhm um, lvtp10: 23.9 kOhm um | **lvt transistors** |
| sampling | tau = T_track / ln(2^N / settle_lsb); 1/4 bit switch, 3/4 top switch | T_track = 10.62 ns, tau <= 1916 ps | **R_unit <= 51.4 kOhm, R_top <= 2410 Ohm** |
| sampling | W_n = (R_on W)_TG,worst / R  (Wp = 2 Wn), bit-i switch = 2^i units | worst (R_on W) = 7.45 kOhm um (ss -40C 1.80V) | **unit TG 0.45/0.90 um** |
| sampling | top-plate switch: sized at Vcm; least hot-leakage flavour among those <= 4x the narrowest (plate droop per conversion, ff 125C, fs 125C, plate Vref/2^(k+1) from Vcm while bit k is tried; budget 0.25 LSB) | std: 37.4 um, 2.8 LSB, lvt: 2.2 um, 3.6 LSB, mix: 5.3 um, 8.5 LSB, mixp: 3.5 um, 0.26 LSB, mixl: 4.3 um, 0.0005 LSB, lvtp5: 2.9 um, 0.85 LSB, lvtp7: 3.1 um, 0.26 LSB, lvtp10: 3.2 um, 0.1 LSB | **mixl: top TG 4.35/8.70 um (10.38 kOhm um at Vcm, 0.001 LSB)** |
| DAC driver | tau = 0.45 Tclk / ln(2^N / settle_lsb), per unit cap (binary scaled) | tau <= 1014 ps, R_unit <= 54.4 kOhm | **unit NMOS 0.45 um, unit PMOS 0.45 um** |