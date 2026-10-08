# RV32I RISC-V SoC with AXI4-Lite Interconnect & VGA Subsystem on SkyWater 130nm

**IEEE SSCS Open-Source Ecosystem Code-a-Chip Travel Grant Submission for ISSCC 2027**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/HSGHamza/RV32I-VGA-SOC/blob/main/ISSCC27/submitted_notebooks/rv32i_vga_soc/rv32i_vga_soc.ipynb)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Process: SkyWater 130nm](https://img.shields.io/badge/PDK-SkyWater%20130nm-orange.svg)](https://github.com/google/skywater-pdk)
[![Toolchain: OpenLane / OpenROAD](https://img.shields.io/badge/EDA-OpenLane%20%2F%20OpenROAD-purple.svg)](https://github.com/The-OpenROAD-Project/OpenLane)

---

## 1. Project Abstract & Highlights

This submission introduces an end-to-end, open-source 32-bit RISC-V (RV32I Base Integer ISA) System-on-Chip (SoC) integrating:
1. **Microprocessor Core:** Custom single-cycle RV32I core equipped with synchronous bus stalling logic.
2. **On-Chip Interconnect:** Industry-standard AXI4-Lite bus crossbar with memory-mapped peripherals and automatic error slave trapping (`SLVERR`).
3. **VGA Graphics Subsystem:** Custom rasterizer supporting standard 640x480 @ 60 Hz video with an internal **160x120 dual-port framebuffer** and **4x hardware pixel scaling**, reducing on-chip RAM footprint by **93.75%**.
4. **Interactive Bare-Metal Demo:** Complete bare-metal Ping Pong game (`pong.s`) featuring 2D ball physics, hardware paddle input, and an autonomous AI opponent.
5. **ASIC Physical Design (SkyWater 130nm):** Hardened down to silicon layout (`soc_top.gds`) via OpenLane / OpenROAD with **0 DRC errors, 0 LVS errors**, clean 9-corner Static Timing Analysis sign-off (+0.545 ns worst setup slack), and 1.01 mW total power consumption.
6. **FPGA Hardware Deployment:** Synthesized onto the Digilent Zybo Z7-10 (Xilinx Zynq-7000) using the open-source **F4PGA / SymbiFlow** flow.
7. **Industrial-Grade Verification:** SystemVerilog UVM 1.2 testbench achieving **>93% functional coverage** with automated scoreboard checking.

All results are packaged into a reproducible, interactive Jupyter Notebook ([`rv32i_vga_soc.ipynb`](rv32i_vga_soc.ipynb)) executable on Google Colab or local Jupyter environments.

---

## 2. Submission Details & Author Information

* **Notebook Title:** RV32I Processor Core with AXI4-Lite Interconnect & 4x Scaled VGA Subsystem on SkyWater 130nm
* **Designated Representative (Primary Applicant):** Hamza Shahid
* **Team Members:** Hamza Shahid, Alishba Khan
* **Affiliation:** *(Your University / Institution / Organization)*
* **Applicant Category:** *(e.g., Undergraduate student / Graduate student)*
* **Eligible Conference:** IEEE International Solid-State Circuits Conference (ISSCC) 2027, San Francisco, CA

---

## 3. Directory Layout

```
ISSCC27/submitted_notebooks/rv32i_vga_soc/
├── rv32i_vga_soc.ipynb      # Main interactive and reproducible Jupyter notebook
├── README.md                # Submission summary & reproduction instructions
├── LICENSE                  # Apache 2.0 open-source license
├── requirements.txt         # Python package dependencies
├── assets/
│   ├── gds/
│   │   └── soc_top.gds      # Tapeout-ready GDSII silicon layout (1.6 MB)
│   ├── metrics.json         # Automated OpenLane physical design & STA sign-off metrics
│   └── screenshots/         # Layout renders, 9-corner STA tables, UVM waveforms
├── hex/
│   ├── instructions_pong.hex # Assembled bare-metal Pong game ROM image
│   └── pong.s               # RISC-V assembly source for interactive Pong game
└── rtl/                     # Synthesizable Verilog RTL source files
    ├── soc_top.v            # Top-level SoC integrating CPU, AXI, and VGA
    ├── bus/                 # AXI4-Lite bridge, decoder, and data memory
    ├── rv32i/               # RV32I ALU, Register File, Control, Datapath
    └── vga/                 # Framebuffer, timing generator, 4x pixel scaler
```

---

## 4. Quickstart & Reproducibility

### Option A: Run in Google Colab (One-Click)
Click the badge above or navigate to:
[https://colab.research.google.com/github/HSGHamza/RV32I-VGA-SOC/blob/main/ISSCC27/submitted_notebooks/rv32i_vga_soc/rv32i_vga_soc.ipynb](https://colab.research.google.com/github/HSGHamza/RV32I-VGA-SOC/blob/main/ISSCC27/submitted_notebooks/rv32i_vga_soc/rv32i_vga_soc.ipynb)

Select **Runtime -> Run all**. The notebook automatically configures its environment, downloads dependencies, emulates the Pong framebuffer, inspects the GDSII silicon geometry, and plots the 9-corner STA sign-off dashboard.

### Option B: Local Execution
Clone the repository and install requirements:
```bash
cd ISSCC27/submitted_notebooks/rv32i_vga_soc
pip install -r requirements.txt
jupyter notebook rv32i_vga_soc.ipynb
```

---

## 5. Physical Sign-Off Metrics (SkyWater 130nm)

| Metric | OpenLane Sign-off Value | Status |
| :--- | :---: | :---: |
| **Process Node** | SkyWater 130nm (`sky130_fd_sc_hd`) | Verified |
| **Die Dimensions** | 112.92 µm x 123.64 µm | Clean |
| **Die Footprint** | 13,960.2 µm² (0.014 mm²) | Passed |
| **Core Utilization** | 79.97% | Optimal |
| **Total Standard Cells** | 1,614 instances (925 logic, 111 sequential) | Clean |
| **Detailed Routing** | 13,464 µm wirelength (iter 22) | Completed |
| **DRC Violations** | 0 errors | **PASSED** |
| **LVS Violations** | 0 errors | **PASSED** |
| **Antenna Violations** | 0 nets / 0 pins | **PASSED** |
| **Worst-Case Setup Slack** | **+0.545 ns** across all 9 PVT corners | **PASSED** |
| **Worst-Case Hold Slack** | **+0.256 ns** across all 9 PVT corners | **PASSED** |
| **Total Power** | **1.01 mW** (0.788 mW internal, 0.224 mW switching) | Passed |
| **Power Grid Integrity** | 13.4 µV average IR drop (83.6 µV worst-case) | Verified |

---

## 6. Open-Source License

This project is released under the **Apache License 2.0**. See [`LICENSE`](LICENSE) for full legal text.
