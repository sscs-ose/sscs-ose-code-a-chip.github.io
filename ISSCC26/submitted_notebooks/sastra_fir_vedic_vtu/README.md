# 3-Tap FIR Filter with Vedic Multiplier, Han-Carlson Adder & Online Verification Test Units

**IEEE SSCS Open-Source Ecosystem — Code-a-Chip Travel Grant Submission**  
**Symposia on VLSI Technology and Circuits 2026**

---

## Team

| Name | Email | Role |
|------|-------|------|
| Balachandran Harini | 127004035@sastra.ac.in | RTL Design, Synthesis, Physical Design |
| Rajeswari N | 127004202@sastra.ac.in | Verification, Simulation |
| Deepthi D | 127180016@sastra.ac.in | Notebook, Documentation |

**Institution:** SASTRA Deemed University, Thanjavur, India — 3rd Year B.Tech

**Mentors:**  
Dr. Prabakar T N (prabakarece@sastra.edu)  
Dr. Sriram A (sriramece@sastra.edu)

---

## Project Overview

This project presents a complete **RTL-to-GDSII implementation** of a 3-tap FIR digital filter:

$$y[n] = a \cdot x[n] + b \cdot x[n-1] + c \cdot x[n-2]$$

Three architectural innovations are combined:

- **Vedic 4×4 Multiplier** — based on the Urdhva-Tiryakbhyam sutra, all 16 partial products are computed in parallel, reducing critical-path depth compared to conventional multipliers.
- **Han-Carlson Parallel Prefix Adder** — logarithmic carry-propagation (O(log₂ n) depth) for 8-bit and 9-bit accumulation stages.
- **Online Verification Test Units (VTU)** — 5 concurrent VTUs using digit-sum (casting-out-nines) arithmetic verify all multiply-accumulate results in real time without a reference model.

---

## Repository Contents

| File | Description |
|------|-------------|
| `fir_filter_SSCS_CodeAChip.ipynb` | Main Jupyter notebook — full design walkthrough |
| `fir_filter.v` | RTL source (synthesisable Verilog IEEE 1364-2001) |
| `fir_filter_netlist.v` | Gate-level netlist after synthesis |
| `tb_fir_fil.v` | Testbench for functional simulation |
| `input_constraint.sdc` | Input SDC timing constraints |
| `gate_output_constraint.sdc` | Output SDC constraints |
| `genus.log` | Cadence Genus synthesis log |
| `innovus.log` | Cadence Innovus place-and-route log |
| `fir_filter.gds` | Final GDSII layout stream file |

---

## Tools & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Cadence Genus | 21.14-s082_1 | Logic synthesis |
| Cadence Innovus | 20.14 | Place and route |
| GSMC 90nm PDK | — | Standard cell library |
| Python | 3.x | Notebook simulation |
| Jupyter Notebook | — | Interactive presentation |

---

## Key Results

| Metric | Value |
|--------|-------|
| Technology | GSMC 90 nm CMOS |
| Clock target | 100 MHz (10 ns) |
| Library corner | Slow (worst-case) |
| Total instances | 1717 (887 logic + 830 filler) |
| DRC violations | 0 |
| Total wire length | 10,567 µm |
| VTU coverage | 5 signals (all MAC outputs) |

---

## How to Run the Notebook

1. Install dependencies:
```bash
pip install jupyter numpy matplotlib
```

2. Launch Jupyter:
```bash
jupyter notebook fir_filter_SSCS_CodeAChip.ipynb
```

3. Run all cells: **Kernel → Restart & Run All**

No proprietary tools are needed to run the Python simulation and view all waveforms and results. The synthesis and PnR sections show results extracted from logs.

---

## License

This project is licensed under the **Apache 2.0 License** — see the LICENSE file in the root of this repository for details.

---

## Acknowledgements

We thank the IEEE Solid-State Circuits Society Open-Source Ecosystem (SSCS OSE) for providing this platform to showcase student open-source chip design work.
