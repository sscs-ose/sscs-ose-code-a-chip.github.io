#  Memory-Less Self-Testing FIR Filter

### Using Vedic Mathematic

### IEEE SSCS Code-a-Chip Submission (ISSCC 2026)

---

##  Overview

Traditional Built-In Self-Test (BIST) techniques rely on centralized verification hardware or large reference memories, resulting in increased area overhead and limited fault localization capability.

This project introduces a **memory-less, distributed self-testing approach** based on **Vedic Mathematics (VTU-based design)** for efficient on-chip verification. The proposed method eliminates the need for external memory while enabling **localized fault detection**, demonstrated using a **3-tap FIR filter architecture**.

---

## Objectives

* Design a **3-tap FIR filter** with reduced hardware complexity
* Implement a **memory-less self-testing mechanism**
* Utilize **Vedic Mathematics (Urdhva Tiryagbhyam)** for efficient computation
* Enable **distributed fault detection** within the filter architecture
* Ensure **reproducibility using open-source tools**

---

##  Key Concepts

###  Memory-Less Design

* Eliminates dependency on external or reference memory
* Reduces area and power consumption

###  Self-Testing Mechanism

* Distributed verification within each computation unit
* Detects faults locally instead of centralized checking

###  Vedic Multiplication (VTU)

* Uses **Urdhva Tiryagbhyam Sutra**
* Enables parallel multiplication → faster and efficient
  
###  Verification Principle (Gunita Samuccaya)

* Core idea behind memory-less verification  
* Multiplication:  
  `digit_sum(a × b) = digit_sum(digit_sum(a) × digit_sum(b))`  
* Addition:  
  `digit_sum(a + b) = digit_sum(digit_sum(a) + digit_sum(b))` 
---

##  Architecture

The system consists of:

*  3-tap FIR filter structure
*  Vedic multipliers for coefficient multiplication
*  Adders for accumulation
*  Distributed self-test logic integrated within datapath
*  Vedic Testing Units (VTUs) - Verify each arithmetic stage using Gunita Samuccaya principle


---

##  Working Principle

The FIR filter output is given by:

[
y[n] = h_0 x[n] + h_1 x[n-1] + h_2 x[n-2]
]

* Inputs are processed through **Vedic multipliers**
* Outputs are accumulated using adders
* Self-test logic verifies correctness at intermediate stages

  <img width="1079" height="564" alt="Screenshot 2026-03-30 181908" src="https://github.com/user-attachments/assets/02e7ab7f-c251-4011-a352-df8dc12fe7ae" />


---

##  Self-Testing Approach

* No external reference memory required
* Test patterns are implicitly generated within computation
* Faults such as:

  * Stuck-at faults
  * Computation errors
    are detected locally

This improves:

* Reliability
* Scalability
* Area efficiency

---

## Simulation & Results

The notebook demonstrates:

*  Input vs Output waveform
*  FIR filter response

  <img width="1046" height="764" alt="Screenshot 2026-03-31 022618" src="https://github.com/user-attachments/assets/932165f9-46ff-4f58-be48-d512f329bc9c" />

  
  <img width="1436" height="724" alt="Screenshot 2026-03-31 023016" src="https://github.com/user-attachments/assets/30f575b4-15dc-483e-8500-42ec1fda99aa" />




---

##  Open-Source Tools Used

This project strictly uses open-source tools to ensure reproducibility:


* Icarus Verilog
* GTK Wave
* OpenRoad
* Magic
* Netgen 

---



## ▶️ How to Run

1. Clone the repository
2. Install dependencies:

```id="cbb6k1"
pip install -r requirements.txt
```

3. Open the notebook:

```id="gdxh3f"
jupyter notebook fir_self_test.ipynb
```

4. Run all cells

---

##  Advantages

* ✔ Reduced area (no memory blocks)
* ✔ Faster computation using Vedic math
* ✔ Localized fault detection
* ✔ Scalable architecture
* ✔ Fully reproducible

---

##  Future Work

* Extension to higher-order FIR filters
* Integration into DSP and AI accelerator pipelines
* Power and delay optimization

---



## 🙌 Acknowledgment

Submitted to the **IEEE Solid-State Circuits Society (SSCS) Code-a-Chip Initiative**, promoting open-source and reproducible chip design.



---
