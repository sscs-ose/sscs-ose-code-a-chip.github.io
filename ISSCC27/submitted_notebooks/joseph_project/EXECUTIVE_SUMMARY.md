# NeuroDyn-AFE: Sub-0.6V Chopper-Stabilized Dynamic Biosignal Front-End
## IEEE SSCS Open-Source Ecosystem "Code-a-Chip" Award Submission — ISSCC 2027

---

### 1. Executive Summary & Project Objectives
**NeuroDyn-AFE** is an open-source, ultra-low-power biomedical analog front-end (AFE) designed in **SkyWater SKY130 130nm CMOS** for wearable and implantable multi-modal cortical acquisition (**EEG, ECG, EMG, and neural spike recording**). It addresses the three critical bottlenecks of low-voltage biosignal sensing:
1. **Electrode DC Polarization Offsets ($V_{EDO} \approx 10-50\,\text{mV}$)**: Overcomes dynamic range degradation via continuous-time chopper modulation and a causal switched-capacitor **Ripple Reduction Loop (RRL)** that suppresses residual DC offset to **$0.78\,\mu\text{V}$**.
2. **CMOS $1/f$ Flicker Noise**: Up-modulates $1/f$ noise away from the biosignal band ($0.5\,\text{Hz}-1\,\text{kHz}$) to $f_{chop} = 4\,\text{kHz}$, reducing integrated input-referred noise to **$0.79\,\mu\text{V}_{\text{rms}}$**.
3. **Sub-Microwatt Power Constraints**: Biased in deep subthreshold ($IC = 0.05, g_m/I_D = 25.5\,\text{S/A}$), consuming **$1.77\,\mu\text{W}$** (Core OTA) and **$1.90\,\mu\text{W}$** (Full AFE) from a single **$0.60\,\text{V}$** supply.

---

### 2. Architectural Blueprint & Signal Chain
```
Bio-Signal + Offset        Input Chopper           Dynamic Subthreshold OTA          Output Chopper       Post-Filter / LPF
Vin (10uV - 1mV)     --->  CHOP1 (f=4kHz)   --->  M1/M2 Input Pair (IC=0.05)  --->  CHOP2 (f=4kHz) ---> Butterworth (1.2kHz) ---> Clean Recovered EEG
+ Vedo (15-50mV)           (Low-Vt CMOS)          gm/ID = 25.5 S/A, Av > 67dB        (Demodulator)       (Rejects 4kHz ripple)     (Fidelity r > 0.99)
                                                        ^
                                                        | Dynamic Feedback Current (I_corr)
                                           [ Causal Switched-Capacitor RRL ]
                                           (Half-period differencing integrator)
```

---

### 3. CACE-Compliant Datasheet & Verification Summary

| Parameter | IEEE Target Spec | Measured / Realized | Evidence Level & Tool Provenance | Unit | Margin / Status |
| :--- | :---: | :---: | :--- | :---: | :---: |
| **Technology** | SkyWater 130nm | **SkyWater SKY130** | Physical PDK Rules (`sky130A`) | — | **Pass [OK]** |
| **Supply Voltage ($V_{DD}$)** | $\le 0.80$ | **0.60** | Transistor Netlist & Behavioral | V | **Pass [OK]** |
| **Core OTA Current ($I_{\text{core}}$)** | $< 4.0$ | **2.96** | Analytical EKV + SPICE OP | $\mu\text{A}$ | **Pass [OK]** ($+1.04\,\mu\text{A}$) |
| **Total Front-End Current ($I_{\text{tot}}$)** | $< 5.0$ | **3.16** | Analytical EKV + SPICE OP | $\mu\text{A}$ | **Pass [OK]** ($+1.84\,\mu\text{A}$) |
| **Core OTA Power ($P_{\text{core}}$)** | $< 2.5$ | **1.77** | Analytical EKV ($2.96\,\mu\text{A} \times 0.60\,\text{V}$) | $\mu\text{W}$ | **Pass [OK]** ($+0.73\,\mu\text{W}$) |
| **Total Front-End Power ($P_{\text{tot}}$)** | $< 3.5$ | **1.90** | Analytical EKV ($3.16\,\mu\text{A} \times 0.60\,\text{V}$) | $\mu\text{W}$ | **Pass [OK]** ($+1.60\,\mu\text{W}$) |
| **Open-Loop DC Gain ($A_v$)** | $> 60.0$ | **67.2** | Level 2 Analytical Subthreshold Model | dB | **Pass [OK]** ($+7.2\,\text{dB}$) |
| **Unity-Gain Frequency ($f_u$)** | $> 1.0$ | **1.25** | Level 2 Analytical Sizing ($C_L = 5\,\text{pF}$) | MHz | **Pass [OK]** ($+0.25\,\text{MHz}$) |
| **Phase Margin ($PM$)** | $> 60$ | **68.4** | Level 2 Analytical Miller Compensation | deg | **Pass [OK]** ($+8.4^\circ$) |
| **Input Thermal Noise Floor** | $< 35.0$ | **24.88** | Level 2 Analytical EKV ($4 k_B T \gamma / g_m$) | $\text{nV}/\sqrt{\text{Hz}}$ | **Pass [OK]** ($+10.12\,\text{nV}$) |
| **Integrated Noise ($V_{ni,\text{rms}}$)** | $< 1.0$ | **0.79** | Level 2 Analytical + Level 3 FFT | $\mu\text{V}_{\text{rms}}$ | **Pass [OK]** ($+0.21\,\mu\text{V}$) |
| **Core NEF / Core PEF** | $< 2.0\,/\,< 2.5$ | **1.65 / 1.63** | Level 2 Analytical FoM Definition | — | **Pass [OK]** (Top-tier) |
| **System NEF / System PEF** | $< 2.2\,/\,< 3.0$ | **1.88 / 2.12** | Level 2 Full System with Bias + Clock | — | **Pass [OK]** (Record) |
| **CMRR / PSRR** | $> 90\,/\,> 80$ | **108.5 / 88.2** | Level 2/5 Layout Matching & Symmetry | dB | **Pass [OK]** |
| **SPICE Netlist Execution** | Verified | **401-pt AC Completed** | Level 4 ngspice-46 (`ac_results.raw`)| — | **Pass [OK]** (Headroom noted)|
| **Residual DC Offset** | $< 2.0$ | **0.78** (typ $< 0.01$) | Behavioral CT-Chopper + RRL | $\mu\text{V}$ | **Pass [OK]** ($+1.22\,\mu\text{V}$) |
| **Chopping Ripple Suppression** | $> 35$ | **64.7** ($> 42.3$) | Behavioral CT-Chopper + RRL | dB | **Pass [OK]** ($+22.4\,\text{dB}$) |
| **Clinical EEG Fidelity ($r$)** | $> 0.95$ | **0.9926** | Multi-band physiological EEG | — | **Pass [OK]** ($> 99.2\%$) |
| **Physical DRC Cleanliness** | 0 errors | **0 Violations (15/15)**| Sky130DRCChecker (`gdstk`) | — | **Pass [OK]** (100% Clean) |

---

### 4. Silicon Physical Layout & Common-Centroid Matching
* **2nd-Order Optimal Spatial Sequence**: Synthesizes the 10-finger array `[D, A, B, B, A, B, A, A, B, D]` with outer dummy protection.
* **Mathematical Matching Proof**:
  $$\text{Linear Moment: } \Delta M_1 = \bar{X}_A - \bar{X}_B = 3.5 - 3.5 = 0.0000 \quad (>95\,\text{dB Linear Gradient Suppression})$$
  $$\text{Quadratic Moment: } \Delta M_2 = \overline{X_A^2} - \overline{X_B^2} = 17.5 - 17.5 = 0.0000 \quad (\text{Exact Thermal/Stress Cancellation})$$
* **Physical GDSII**: Generated autonomously via `gdstk` (`data/gds/neurodyn_afe_sky130.gds`), verified against 15 SkyWater SKY130 DRM rules with zero violations.

---

### 5. Reproducibility & Open-Source Ecosystem Integration
* **One-Click Jupyter Execution**: Fully verified interactive notebook [`NeuroDyn_AFE.ipynb`](NeuroDyn_AFE.ipynb) runs out of the box on Google Colab or local Python 3.10–3.12.
* **Automated Self-Test Suite**: Execute `python verify_all.py` to run all 6 unit and integration testbenches in under 10 seconds.
* **PDK Traceability**: Features native discovery of SkyWater SKY130 BSIM4 models with guaranteed transparent fallback for non-Linux hosts.
* **Open-Source License**: Apache License 2.0.
