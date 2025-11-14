# Current Mode Logic Synthesis, Optimization, and Design

## Code A Chip Challenge 2026

This repository contains the code, jupyter notebook, and support scripts for the design and fully automated synthesis of CML Logic Latches and Dividers.

The optimization is done to minimize power consumption of the CML Logic from a given timing constraint specification using the C/ID analog design methodology.

The top level notebook to be run for the submission is **current_mode_logic_optimization.ipynb**

**The working directory for running this notebook must match the directory where the notebook file is located.**

The flow shown in current_mirror_ota_optimization.ipynb comprises of the following:

1. Install Python Libraries
2. Generate Lookup Tables (LUTs) for C/ID and convert it to CML and SF
3. Derive Objective Function for Latch, Divider, Divider23
4. Size Transistors Using Current Density Lookups
5. Generate SPICE Netlists
6. Run Simulations

## Getting Started

### Tools Needed to Run

This submission runs in google collab out of the box (it installs all the dependencies).

This submission requires the following tools to be installed

- python3.X all required python libraries are installed within cells of the notebook
- python-dev libraries, This is python developer package this needs to be installed with sudo privilege and cannot be run inside the notebook
      - can be installed with command **sudo apt-get install python-dev for Ubuntu** or **sudo yum install python-devel for Redhat/Centos/Rocky**
- magic VLSI (open source layout editor) to be installed with the executable command "magic" accessible from a users $PATH environment variable
- ngspice (open source SPICE simulator) to be installed with the executable command "ngspice" accessible from a users $PATH environment
- Skywater130 open source PDK installed to $PDK_ROOT variable. This PDK is available at https://github.com/RTimothyEdwards/open_pdks with installation instructions

**These tools can also be installed within the notebook itself. The notebook is self checking for the PDK and tools.**

The following commands can be used to install magic, ngspice, and ALIGN using Ubuntu

```bash
sudo apt update

#install ngspice
sudo apt install ngspice

#install magic
git clone https://github.com/RTimothyEdwards/magic.git
cd magic
./configure
make
sudo make install
```

The Skywater130 PDK can be installed with:

```bash
git clone https://github.com/RTimothyEdwards/open_pdks
cd open_pdks
./configure --enable-sky130-pdk
make
sudo make install
make veryclean
```

## Repository File Structure

```txt
./
|
├── current_mode_logic_optimization.ipynb - Top Level Notebook to be run for submission
│
├── images -> Directory to hold images used in notebook
│     │
│     ├── char_tb.png
│     ├── divider_tb.png
│     ├── divider23_tb.png
│     └── latch_tb.svg
│
├── LICENSE - Apache 2.0 License File
|
└── CML-DIV-Synthesis: Current Mode Logic Dividers Synthesis Repository
      |
      ├── characterization - Contains Characterization LUTs and LUT Generation Characterization Scripts Used in notebook
      │      │  
      │      ├── cml_char_template.cir - ngspice netlist template for LUT generation
      │      │  
      │      └── sky130 - directory to hold Skywater130A LUTs and Process Specific Data
      │          │ 
      │          ├── 01v8_lvt_150_tt_25.cir - Skywater130A LUT Testbench netlist
      │          └── 01v8_lvt_150_tt_25.csv - Skywater130A LUT
      │
      ├── schematics -> contains xschem schematics for LUT characterization, Divider schematic & symbol art, and testbenches
      │
      ├── latch -> Directory To Hold Latch Testbench and Circuits
      │      │
      │      ├── latch_params.cir - Latch Parameters
      │      ├── latch.cir - Latch Subcircuit
      │      └── tb_latch.cir - Latch Testbench
      │
      ├── divider -> Directory To Hold Divider Testbench and Circuits
      │      │
      │      ├── divider_params.cir - Divider Parameters
      │      ├── divider.cir - Divider Subcircuit
      │      └── tb_divider.cir - Divider Testbench
      │
      ├── divider23 -> Directory To Hold Divider2/3 Testbench and Circuits
      │      │
      │      ├── divider23_params.cir - Divider2/3 Parameters
      │      ├── divider23.cir - Divider2/3 Subcircuit
      │      └── tb_divider23.cir - Divider2/3 Testbench
      │
      ├── latch.pkl -> Latch table holding optimization space
      │
      └── divider.pkl -> Divider table holding sensitivity curves
```

## License

This project is licensed under the Apache 2.0 License. See LICENSE for more details.
