# Current Mirror OTA Synthesis, Optimization, and Design
## Code A Chip Challenge 2025

This repository contains the code, jupyter notebook, and support scripts for the design and fully automated synthesis of an N-Input 8 transistor beta multiplier OTA.

The optimization is done to minimize power consumption of the current mirror OTA from a given stability, gain, and bandwidth specification using the C/ID analog design methodology. 

A detailed analysis for the analytical optimization can be found in the PDF file AnalyticalOptimization-OTA.pdf. 

This manuscript is under review for DAC 2025 and any potential conflict of interests in the review process should be stated upon review of this submission.

The top level notebook to be run for the submission is **current_mirror_ota_optimization.ipynb**

**The working directory for running this notebook must match the directory where the notebook file is located.**

The flow shown in current_mirror_ota_optimization.ipynb comprises of the following:
1. Install Python Libraries
2. Generate Lookup Tables (LUTs) for C/ID
3. Derive Objective Function and Solution Space for OTA
4. Choose Design Point Based on Optimization and PVT Convergence
5. Size Transistors Using Current Density Lookups
6. Generate SPICE and ALIGN Netlists
7. Run ALIGN Layout Generator with Netlists
8. Extract Layout Using Magic VLSI
9. Run and Compare Ideal and Post Layout Simulations 

# Getting Started

## Tools Needed to Run 
This submission requires the following tools to be installed
  - python3.X all required python libraries are installed within cells of the notebook
  - magic VLSI (open source layout editor) to be installed with the executable command "magic" accessible from a users $PATH environment variable
  - ngspice (open source SPICE simulator) to be installed with the executable command "ngspice" accessible from a users $PATH environment
  - Skywater130 open source PDK installed to $PDK_ROOT variable. This PDK is available at https://github.com/RTimothyEdwards/open_pdks with installation instructions
  - ALIGN layout generator available at https://github.com/ALIGN-analoglayout/ALIGN-public with installation instructions. The executable command "schematic2layout.py" must be accessible from a users $PATH environmental variable
  		- This script also contains a cell to install this, although it takes about 45 minutes to run the cell

The following commands can be used to install magic, ngspice, and ALIGN using Ubuntu

```
sudo apt update
sudo apt install ngspice
git clone https://github.com/RTimothyEdwards/magic.git
cd magic
./configure
make
sudo make install
git clone https://github.com/ALIGN-analoglayout/ALIGN-public
pip install -v ./ALIGN-public
```

The Skywater130 PDK can be installed with 
```
git clone https://github.com/RTimothyEdwards/open_pdks
cd open_pdks
./configure --enable-sky130-pdk --enable-sram-sky130
make
sudo make install
make veryclean
```


## Repository File Structure
```
./
|
├── current_mirror_ota_optimization.ipynb - Top Level Notebook to be run for submission
│
├── AnalyticalOptimization-OTA.pdf - Detailed Analytical Analysis of Optimization - In Review for DAC 2025
│   
├── characterization - Contains Characterization LUTs and LUT Generation Characterization Scripts Used in notebook
│			│  
│           ├── char_template.cir - ngspice netlist template for LUT generation
│           │  
│           └── sky130 - directory to hold Skywater130A LUTs and Process Specific Data
│               │ 
│               ├── LUTs_SKY130 - directory to hold Skywater130A LUTs - each subdirectory represents LUTs for 1 device i.e. n_01v8
│               │           ├── n_01v8 - example device
│               │           │           ├── LUT_N_1000 -> direcotrylookup table 
│               │           │           │           ├── nfetff-25.csv
│               │           │           │           ├── nfetff27.csv
│               │           │           │           ├── nfetff75.csv
│               │    		.			.			.
│               │    		.			.			.
│               └── schematics -> contains xschem schematics for LUT characterization, OTA schematic & symbol art, and testbenches
│                   ├── cid_characterization.sch - LUT generation schematic
│                   ├── cm_ota.sch - Current Mirror OTA schematic
│                   ├── cm_ota.sym - Current Mirror OTA symbol
│                   ├── tb_cm_ota_dcop.sch - OTA DC operating point testbench
│                   └── tb_cm_ota.sch - OTA general testbench
│
├── design --> Directory To Hold Generated Design Data Such As GDS files, Extracted Netlists and Simulation Data
│			│  - This directory also holds the ALIGN generator netlist template 
│ 			│  - The subdirectories 
│           │
│           ├── align_netlist_template.txt - ALIGN Netlist Template for Layout Generation 
│           ├── gds_-25c -> contains layout and GDS data for -25C optimization
│           │           ├── clean - script to remove generated data such as extracted netlists and GDS
│           │           ├── cm_ota_align - directory to hold ALIGN input data and ALIGN generated data
│           │           │           ├── align_input - input directory for ALIGN generator
│           │           │           │           ├── current_mirror_ota.const.json - constraint file given as input to ALIGN
│           │           │           │           └── current_mirror_ota.sp - ALIGN netlist for layout generation
│           │           │           ├── clean - script to remove ALIGN generated data such as GDS files for subcells
│           │           │           └── create_gds.csh - script to generate GDS using ALIGN
│           │           │ 
│           │           ├── extract_current_mirror_ota.tcl - TCL Magic script to extract a post layout SPICE netlist for simulation
│           │           │       						   
│           │           │ 
│           │           └── run_extraction.csh - cshell script to extract a post layout SPICE netlist for simulation using magic
│           │  
│			.
│ 			.
│           └── simulation
│               ├── cm_ota_params_template.sp
│               ├── golden_sims -> Golden standard simulations
│               │           ├──────25──── simulations for 25 C
│               │           │           ├── ac_output_ext.txt - post layout AC spice simulation data
│               │           │           └── ac_output.txt - ideal schematic AC spice simulation data
│               │           ├──────75────
│               │           │           ├── ac_output_ext.txt - post layout AC spice simulation data
│               │           │           └── ac_output.txt - post layout AC spice simulation data
│               │           └────neg_25──
│               │              			├── ac_output_ext.txt - post layout AC spice simulation data
│               │               		└── ac_output.txt - post layout AC spice simulation data
│               │
│               ├── spice -> directory to run spice simulations 
│               │           ├── clean - script to remove generated spice data
│               │           ├── cm_ota_extracted.sp - spice file to hold extracted netlist
│               │           ├── cm_ota_params.sp - spice file to hold ideal spice ota parameters (device widths and lengths)
│               │           ├── cm_ota_schematic.sp - spice netlist for the ota
│               │           ├── run_tb.csh - cshell script to run spice testench
│               │           ├── tb_cm_ota_preprocessed.sp - spice netlist for testbench with $PDK_ROOT declared
│               │           └── tb_cm_ota.sp - post processed spice netlist testbench with $PDK_ROOT replaced with users $PDK_ROOT
│
│
├─── eda -> Directory for process specific EDA files 
│           ├── ALIGN-pdk-sky130 -> Directory to hold Skywater130 specific files for ALIGN
│           │           ├── LICENSE - ALIGN Skywater130 PDK License
│           │           ├── README.md - ALIGN Skywater130 PDK README file
│           │           └── SKY130_PDK - ALIGN Skywater130 PDK files
│           │               ├── Align_primitives.py
│           │               ├── cap.py
│           │               ├── fabric_Cap.py
│           │               ├── fabric_Res.py
│           │               ├── fabric_ring.py
│           │               ├── gen_param.py
│           │               ├── guard_ring.py
│           │               ├── __init__.py
│           │               ├── layers.json
│           │               ├── models.sp
│           │               ├── mos.py
│           │               ├── __pycache__
│           │               │           ├── canvas.cpython-38.pyc
│           │               │           ├── cap.cpython-310.pyc
│           │               │           ├── cap.cpython-38.pyc
│           │               │           ├── gen_param.cpython-310.pyc
│           │               │           ├── guard_ring.cpython-310.pyc
│           │               │           ├── guard_ring.cpython-38.pyc
│           │               │           ├── __init__.cpython-310.pyc
│           │               │           ├── __init__.cpython-38.pyc
│           │               │           ├── mos.cpython-310.pyc
│           │               │           ├── mos.cpython-38.pyc
│           │               │           ├── res.cpython-310.pyc
│           │               │           ├── res.cpython-38.pyc
│           │               │           └── via.cpython-38.pyc
│           │               └── res.py
│           ├── sky130.magicrc - startup file for magic layout tool - used when extracting layouts
│
├── images -> Directory to hold images used in notebook
│           │
│           ├── ac_simulation_plot.png
│           ├── ac_simulation_plot.svg
│           ├── analysis_page1.png
│           ├── analysis_page2.png
│           ├── analysis_page3.png
│           ├── analysis_page4.png
│           ├── cid_tb.png
│           ├── fig_bode_plot.png
│           ├── fig_cm_ota_all_gds.png
│           ├── fig_design_space.png
│           ├── fig_flowchart_dac.png
│           └── fig_ota_schematic.png
│
├── LICENSE - GPL 3.0 License File
│ 
├───src───
│         ├── cid.py - python object for storing lookup tables and performing lookups
│         └── fonts - directory containing fonts for graphing
│             └── ArialNarrow
│                 ├── arialnarrow_bolditalic.ttf
│                 ├── arialnarrow_bold.ttf
│                 ├── arialnarrow_italic.ttf
│                 ├── arialnarrow.ttf
│                 ├── ArialNarrow.zip
│                 └── COPYRIGHT.txt
```
##  License
This project is licensed under the GPL 3.0 License. See LICENSE for more details.