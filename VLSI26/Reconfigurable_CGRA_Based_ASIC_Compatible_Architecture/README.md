# Reconfigurable CGRA-Based ASIC-Compatible Architecture

**IEEE SSCS Open-Source Ecosystem — Code-a-Chip Travel Grant Submission**  
**Symposia on VLSI Technology and Circuits 2026**

---

## Team

| Name | Email |
|------|-------|
| Balachandran Harini | 127004035@sastra.ac.in |
| Rajeswari N | 127004202@sastra.ac.in |
| Deepthi D | 127180016@sastra.ac.in |

**Institution:** SASTRA Deemed University, Thanjavur, India — 3rd Year B.Tech, ECE

**Mentors:**  
Dr. Prabakar T N (prabakarece@sastra.edu)  
Dr. Sriram A (sriramece@sastra.edu)

---

## Project Overview

This project presents a **reconfigurable Coarse-Grained Reconfigurable Array (CGRA)**-inspired verification fabric co-designed for ASIC compatibility. The fabric is a **6×6 heterogeneous compute tile array** interconnected by programmable horizontal and vertical routing channels, switch blocks, and connection boxes — modelled after classical FPGA routing infrastructure but optimized for fixed-function arithmetic verification tiles.

### Key Innovations

**1. CGRA Meets Distributed Online Verification**  
Every compute tile is self-verifying using Vedic digit-sum (casting-out-nines) residue arithmetic. No stored reference model, no test cycles, no SRAM overhead — the verification property is algebraically guaranteed for every input.

**2. Heterogeneous Tile Composition**  
Six tile types are supported: Multiplier (MUL), Adder (ADD), Subtractor (SUB), Divider (DIV), D Flip-Flop (FF), and Comparator (CMP). Coarse-grain word-level operation (4-bit) reduces configuration bits by ~2000× compared to equivalent FPGA implementations.

**3. Parameterised Routing Infrastructure**  
All routing modules (connection boxes, switch blocks, IO blocks) are fully parameterised, making the fabric scalable to larger arrays or wider datapaths without RTL changes.

**4. ASIC-Compatible Open-Source Flow**  
Full synthesis via OpenROAD Flow Scripts (ORFS) targeting the SkyWater SKY130HD standard cell library. 58,479 µm² chip area, 10,486 cells, 0 DRC violations.

---

## Fabric Architecture

The verification fabric is a **6-row × 6-column grid** of compute tiles:

```
         Col0    Col1    Col2    Col3    Col4    Col5
Row0:    MUL     ADD     SUB     DIV     FF      MUL
Row1:    ADD     MUL     ADD     FF      MUL     ADD
Row2:    CMP     FF      SUB     MUL     FF      MUL
Row3:    ADD     MUL     ADD     FF      ADD     FF
Row4:    MUL     ADD     FF      ADD     FF      MUL
Row5:    ADD     MUL     SUB     DIV     FF      FF
```
<img width="992" height="845" alt="image" src="https://github.com/user-attachments/assets/826208fc-b340-40a5-bba8-7c42187b0b2a" />


**Routing:** 6 horizontal channels (HC0–HC5) and 6 vertical channels (VC0–VC5), each carrying 16 tracks of 4-bit width (64-bit bus). 25 switch blocks and 80+ connection boxes provide programmable inter-tile connectivity.

### Tile Counts

| Tile Type | Count | Verification Method |
|-----------|-------|---------------------|
| MUL | 10 | DS(a×b) = DS(DS(a)×DS(b)) |
| ADD | 10 | DS(a+b) = DS(DS(a)+DS(b)) |
| FF  | 10 | Registered routing relay |
| SUB | 3  | DS(a−b) = DS(DS(a)−DS(b)) |
| DIV | 2  | DS(d÷a) = DS(DS(d)÷DS(a)) |
| CMP | 1  | DS(actual) == expected_DS |

---

## Vedic Verification Principle

The online verification scheme is based on the **Anurupyena sutra** (casting-out-nines) from Vedic Mathematics:

```
DS(a × b) = DS(DS(a) × DS(b))     [multiplication]
DS(a + b) = DS(DS(a) + DS(b))     [addition]
DS(a − b) = DS(DS(a) − DS(b))     [subtraction]
DS(d ÷ a) = DS(DS(d) ÷ DS(a))     [integer division]
```

where `DS(n)` is the iterative decimal digit sum (≡ n mod 9, with 9 → 9). This property is algebraically guaranteed for all inputs — no lookup table, ROM, or test vector is needed.

---

## Synthesis Results

Synthesised using **OpenROAD Flow Scripts (ORFS)** targeting **SkyWater SKY130HD**:

| Metric | Value |
|--------|-------|
| Technology | SkyWater SKY130HD (open-source PDK) |
| Module | `verification_fabric_top` |
| Number of cells | 10,486 |
| Chip area | 58,479.836800 µm² |
| Number of wires | 11,170 |
| Number of wire bits | 16,268 |
| Number of ports | 22 |
| Number of port bits | 5,120 |
| DRC violations | 0 |
| GDS | In progress |

---

## Repository Contents

| File | Description |
|------|-------------|
| `cgra_notebook.ipynb` | Main Jupyter notebook — full design walkthrough, runnable with Icarus Verilog |
| `rtl/cgra_fabric.v` | Complete RTL source (12 modules, synthesisable Verilog 2005) |
| `tb/tb_cgra.v` | Icarus Verilog testbench (tile-level VTU verification) |
| `synth/synth_stat.txt` | OpenROAD synthesis statistics |
| `synth/cgra_netlist.v` | Gate-level netlist (SKY130HD) |
| `openroad/config.mk` | ORFS flow configuration |
| `results/final/cgra_fabric.gds` | Final GDSII layout (in progress) |

---

## How to Run the Notebook

### Requirements

- Python 3.x with Jupyter
- Icarus Verilog (`iverilog`) for RTL simulation
- matplotlib (optional, for synthesis plots)

### Install dependencies

```bash
pip install jupyter numpy matplotlib
sudo apt install iverilog        # Ubuntu/Debian
# or: brew install icarus-verilog  (macOS)
```

### Launch

```bash
jupyter notebook cgra_notebook.ipynb
```

Run all cells: **Kernel → Restart & Run All**

The notebook will:
1. Write `cgra_fabric.v` and `tb_cgra.v` to the working directory
2. Compile with `iverilog -g2005`
3. Simulate with `vvp` and print pass/fail results for all tile types
4. Run a Python golden model exhaustively validating the casting-out-nines property
5. Generate synthesis summary plots

---

## RTL Simulation (standalone)

Without Jupyter, compile and run directly:

```bash
iverilog -g2005 -Wall -o tb_cgra rtl/cgra_fabric.v tb/tb_cgra.v
vvp tb_cgra
```

Expected output includes PASS results for all MUL, ADD, SUB, DIV, CMP, FF, and routing infrastructure tests.

---

## Tools and Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Icarus Verilog | 11+ | RTL simulation |
| OpenROAD (ORFS) | OSS CAD Suite | Synthesis, place and route |
| SkyWater SKY130HD | — | Standard cell library |
| Python | 3.x | Notebook simulation and golden model |
| Jupyter Notebook | — | Interactive presentation |

---

## Related Work

This project extends the team's prior IEEE SSCS Code-a-Chip 2025 submission:  
*"Memory-Less Self-Testing FIR Filter Using Vedic Mathematics & Distributed VTU-Based On-Chip Verification"*  
which demonstrated the VTU concept on a 3-tap FIR filter. The CGRA fabric generalises this principle to a fully reconfigurable, heterogeneous arithmetic array.

---

## Future Work

- Complete place-and-route to GDSII (GDS in progress)
- Dual-residue verification (mod-9 + mod-11) to reduce aliasing from ~11% to ~1%
- 8-bit tile variants using recursive Vedic decomposition
- Python fabric compiler to auto-generate configuration bitstreams from dataflow graphs
- Power analysis using OpenROAD's built-in power estimation

---

## Acknowledgements

We thank the IEEE Solid-State Circuits Society for the Code-a-Chip Open-Source Ecosystem initiative, SkyWater Technology and Google for the open-source SKY130 PDK, and the OpenROAD and OpenLane communities for their invaluable open-source EDA infrastructure.
