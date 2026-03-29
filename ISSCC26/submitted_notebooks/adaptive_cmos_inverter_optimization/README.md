# 🚀 Adaptive CMOS Inverter Optimization using Open-Source Tools

## 👤 Author  
Varkala Shashidhar  
Methodist College of Engineering and Technology, Abids Hyderabadad, India 
Email: vshashidhar69@gmail.com  

---

##  Overview  
This project presents a **reproducible, data-driven exploration of CMOS inverter design** using open-source tools.  
The work focuses on analyzing the **power–delay tradeoff** at transistor level and identifying optimal design configurations using **Power-Delay Product (PDP)** as the key Figure of Merit.

Unlike conventional manual tuning, this approach leverages **automated simulation + data analysis** to enable scalable and intelligent circuit optimization.

---

##  Objectives  
- Design and simulate a CMOS inverter at transistor level  
- Perform automated parameter sweep across:
  - Supply voltage (VDD)
  - Transistor sizing (W/L)
  - Load capacitance (CL)  
- Extract performance metrics:
  - Propagation delay  
  - Power consumption  
- Optimize circuit using **Power-Delay Product (PDP)**  
- Identify optimal design point balancing speed and energy  

---

##  Methodology  

### 1. Circuit Design  
A CMOS inverter is modeled using NMOS and PMOS transistors in a SPICE netlist.

### 2. Simulation  
- Simulations performed using **ngspice**  
- Transient analysis used to extract delay  
- Power measured from supply current  

### 3. Automation  
- Python used to perform **multi-parameter sweep**  
- Hundreds of design configurations evaluated  

### 4. Optimization  
- PDP computed for each configuration  
- Optimal design selected based on minimum PDP  

### 5. Visualization  
- Power vs Delay tradeoff plots  
- PDP heatmap  
- 3D design space exploration  

---

##  Design Comparison  

| Parameter | Low Power Design | High Speed Design | Optimal (PDP) Design |
|----------|----------------|------------------|---------------------|
| VDD      | Low            | High             | Moderate            |
| W/L      | Small          | Large            | Balanced            |
| Delay    | High           | Low              | Balanced            |
| Power    | Low            | High             | Moderate            |
| PDP      | Moderate       | High             | **Minimum**         |

---

##  Key Results  

- Clear tradeoff observed between power and delay  
- Increasing VDD reduces delay but increases power  
- Larger transistor sizes improve speed at cost of energy  
- Optimal design identified using PDP minimization  
- Data-driven analysis enables **efficient design space exploration**  

---

##  Design Insights  

- Power–delay tradeoff is fundamental in digital circuit design  
- PDP provides a balanced metric for optimization  
- Automated sweeps outperform manual tuning  
- Load capacitance significantly impacts delay behavior  
- Optimal region exists rather than a single extreme point  

---

##  Limitations & Future Work  

### Limitations  
- Uses simplified transistor models (Level-1 MOS)  
- No layout parasitics considered  
- Ideal simulation environment  

### Future Work  
- Use **Sky130 PDK** for realistic modeling  
- Extend to complex circuits (e.g., amplifiers, SRAM, oscillators)  
- Integrate **machine learning-based optimization**  
- Include layout-level analysis (OpenROAD)  

---

##  Tools & Technologies  

- **ngspice** — Circuit simulation  
- **Python** — Automation & analysis  
- **NumPy / Pandas** — Data processing  
- **Matplotlib** — Visualization  
- **Jupyter Notebook** — Reproducible workflow  

---

##  Reproducibility  

All simulations are fully automated and reproducible using the provided Jupyter Notebook.  
The workflow enables scalable exploration of circuit design spaces using open-source tools.

---

##  Key Contribution  

This project demonstrates how **open-source EDA tools combined with data-centric methodologies** can transform traditional circuit design into a **scalable, reproducible, and optimization-driven process**.

It highlights a shift from manual design intuition to **systematic and intelligent exploration of VLSI design tradeoffs**.

---

##  References  

- CMOS inverter fundamentals  
- ngspice documentation  
- Open-source EDA resources  

---

##  Conclusion  

This work successfully demonstrates a structured and reproducible approach to CMOS inverter optimization.  
By combining circuit simulation with data-driven analysis, it enables efficient identification of optimal design configurations and provides meaningful insights into power–performance tradeoffs.

---
