# 16‑bit Vedic Multiplier MAC with Security Key

**Author:** Kamalesh E  
**License:** Apache 2.0  
**Submission:** IEEE SSCS Code‑a‑Chip VLSI'26 Travel Grant Award

---

##  About the Author

Kamalesh E is an **IEEE Undergraduate Student Member** at **Government College of Technology, Coimbatore**, India. His interests lie in **digital VLSI design**, **computer architecture**, and **open‑source EDA tools**. This project was developed as part of his exploration into reproducible ASIC design flows and hardware security.

---

##  Overview

This repository contains a **fully reproducible Jupyter notebook** that implements a 16‑bit multiplier‑accumulator (MAC) based on the **Vedic mathematics algorithm *Urdhva Tiryagbhyam***. The design includes a hardware security key feature and is taped‑out using **OpenLane 2** with the **SkyWater 130 nm open PDK**.

###  What’s Inside

| File | Description |
|------|-------------|
| `16bit_Vedic_MAC_with_Security_Key.ipynb` | Main Jupyter notebook with RTL, simulation, synthesis, place & route, GDS generation, DRC/LVS, and metric extraction. |
| `pin_order.cfg` (optional) | Custom pin placement file (not required for default flow). |

###  Quick Run (Google Colab)

1. Go to [Google Colab](https://colab.research.google.com/).
2. Click **File → Upload notebook** and select the `.ipynb` file.
3. Run all cells from top to bottom.

>  The free Colab tier may run out of memory during detailed routing. If this occurs, you can run the flow locally (Linux recommended) and embed a GDS screenshot – the competition FAQ explicitly allows this.

### 🖥️ Running Locally (Linux)

1. Install **Nix** with flakes enabled (see [OpenLane docs](https://openlane2.readthedocs.io/en/stable/getting_started/common/nix_installation/index.html)).
2. Launch Jupyter and open the notebook – all dependencies will be installed automatically.

###  Key Results

- **Functional simulation:**  All tests pass (Icarus Verilog)
- **DRC/LVS:**  Clean (Magic & Netgen)

###  License

This work is licensed under the **Apache License 2.0**. See the notebook’s final cell for the full license text.

---

*For questions or collaboration, feel free to open an issue or contact the author.*
