# Current Mirror Synthesis, Optimization and Design - Code A Chip Challenge 2025

This repository contains the code, jupyter notebook, and support scripts for a N-Input 8 transistor beta multiplier OTA. 

## Repository File Structure
.
|
├───current_mirror_ota_optimization.ipynb - Top Level Notebook to be run for submission
│
├───AnalyticalOptimization-OTA.pdf - Detailed Analytical Analysis of Optimization - In Review for DAC 2025
│   
├── characterization - Contains Characterization LUTs and LUT Generation Characterization Scripts Used in current_mirror_ota_optimization.ipynb
│           ├── char_template.cir - ngspice netlist template for LUT generation
│           └── sky130 - directory to hold Skywater130A LUTs and Process Specific Data
│               ├── LUTs_SKY130 - directory to hold Skywater130A LUTs - each subdirectory represents LUTs for 1 device i.e. 
│               │           ├── n_01v8 - example device
│               │           │           ├── LUT_N_1000 lookup table 
│               │           │           │           ├── nfetff-25.csv
│               │           │           │           ├── nfetff27.csv
│               │           │           │           ├── nfetff75.csv
│               └── schematics - 
│                   ├── cid_characterization.sch
│                   ├── cm_ota.sch
│                   ├── cm_ota.sym
│                   ├── tb_cm_ota_dcop.sch
│                   └── tb_cm_ota.sch


├───current_mirror_ota_optimization.ipynb - Top Level Notebook to be run for submission
│   ├───magic
│   └───open_pdks
├───current_mirror_ota_optimization.ipynb - Top Level Notebook to be run for submission
│   ├───magic
│   └───open_pdks
├───current_mirror_ota_optimization.ipynb - Top Level Notebook to be run for submission
│   ├───magic
│   └───open_pdks
current_mirror_ota_optimization.ipynb is the submission or code a chip 2025
