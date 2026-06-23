# 🔐 Power Side-Channel Vulnerability in Analog IMC Arrays  
### IEEE SSCS Code-a-Chip — VLSI 2026 Submission

**Authors:** Tanay Das, Udisha Singh  
**Affiliation:** AMD India , IIT Gandhinagar
**License:** Apache 2.0  

---

## 📌 Overview

This project demonstrates a **power side-channel vulnerability** in **analog in-memory computing (IMC) crossbar arrays**, challenging the common assumption that analog systems are inherently secure.

Using **SkyWater SKY130 PDK** and **Ngspice**, we show that:

> The total supply current (**I_DD**) is strongly correlated with the **Hamming weight of the input vector**, enabling **input inference attacks**.

---

## 🚀 Key Contributions

- 🔍 **Side-Channel Attack Demonstration**  
  - Pearson correlation: **ρ ≈ 0.9979**

- 🔊 **Noise Robustness Analysis**  
  - Effective down to **SNR = 3 dB**

- 🛡 **Countermeasure Evaluation**  
  - Passive techniques → **0% effectiveness**

- ⚙️ **Process Corner Validation**  
  - Works across **TT, FF, SS, SF, FS**

- 📈 **Scalability Study**  
  - 8×8 array leakage persists

- 🧠 **Model Extraction Attack**  
  - Weights inferred from current

- 🧱 **Layout (KLayout)**  
  - DRC-clean GDSII

- 🔌 **Post-Layout Validation**  
  - Leakage persists with parasitics

---

## 🧠 Concept

For binary inputs:

I_DD ∝ Σ active rows (Σ conductance)

➡️ Directly maps to **Hamming weight**

---

## 🛠️ Tools & Technologies

- SKY130 PDK  
- Ngspice  
- KLayout  
- Python (NumPy, SciPy, Matplotlib)

---

## 📂 Project Structure

```
.
├── IMC_SideChannel_VLSI2026_v3.ipynb
├── environment.yml
├── spice/
├── layout/
├── results/
└── README.md
```

---

## ⚙️ Setup (Colab)

1. Run initialization cell (runtime restarts)  
2. Install environment using `environment.yml`  
3. Run all cells  

---

## ⚠️ Key Insight

Analog IMC is **not inherently secure**.

Leakage arises from:
- NMOS saturation region behavior  
- Current dependence on gate voltage  

➡️ Passive balancing fails  
➡️ Requires active mitigation  

---

## 📊 Results Summary

| Metric | Value |
|------|------|
| Correlation | 0.9979 |
| Noise Limit | 3 dB |
| Countermeasure | 0% |
| 8×8 Correlation | 0.9976 |

---

## 📎 Citation

Tanay Das, Udisha Singh  
"Power Side-Channel Vulnerability Analysis of Analog IMC Arrays"  
IEEE VLSI 2026  

---

## 📬 Contact

Tanay Das: taanayd@gmail.com
Udisha Singh: udisha.singh@iitgn.ac.in
