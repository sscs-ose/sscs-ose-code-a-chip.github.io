# GmTune: AI-Assisted Design of Linearly Tunable Transconductors via Multi-Objective Optimization
This repository contains code for AI-assisted tunable transconductor design and optimization.


##  Table of Content
1. [Structure](#structure)
2. [Getting Started](#getting-started)
3. [Customization](#customization)
4. [Architecture](#architecture)
5. [Results](#results)
6. [Updates](#updates)
7. [License](#license)
8. [Acknowledgement](#acknowledgement)


##  Structure
The following outline the directory structure.
```
./GmTune/
|
├───ckpts
├───figures
├───src
│   ├───spice
│   ├───model.py
│   ├───netlist.py
│   └───visualizing.py
├───.gitignore
├───environment.yaml
├───LICENSE
├───README.md
└───GmTune.ipynb
```


##  Getting Started
### Environment Setup
```
./home/
|
├───EDA_Tools
│   ├───magic
│   └───open_pdks
└───GmTune
```
Suggest to setup following environment under `EDA_Tools`
```
%% install ngspice and other possible configuration files
cd /home/EDA_Tools
sudo pip3 install flake8
sudo pip3 install setuptools-scm
sudo apt update
sudo apt install build-essential tcl8.6 tcl8.6-dev tk8.6 tk8.6-dev libx11-dev libcairo2-dev libxpm-dev
sudo apt update
sudo apt install flex
sudo apt install bison
sudo apt install libcairo2-dev libjpeg-dev
sudo apt install ngspice
sudo apt install gwave
sudo apt-get install xterm
sudo apt-get install vim-gtk
sudo apt-get install build-essential tcl-dev tk-dev libcairo2-dev libncurses-dev libx11-dev
git clone https://github.com/RTimothyEdwards/magic.git
cd magic
./configure
make
sudo make install
```
Open PDK Installation
```
%% download and install open pdk
cd /home/EDA_Tools
git clone https://github.com/RTimothyEdwards/open_pdks
cd open_pdks
./configure --enable-sky130-pdk --enable-sram-sky130
make
sudo make install
make veryclean
```


##  Customization
To redo optimization or modify the models/thresholds, users can do customization on following `args` in `GmTune.ipynb`.
- change initial setting of circuit parameters by providing different `VDD`, `VCM`, `WM1`, `WM3`, and `WM4`.
- modify the objective thresholds for different optimization strategies `Vg_threshold`, `Gm_threshold`, `Pw_threshold`, and `Bw_threshold`.


##  License
This project is licensed under the MIT License. See LICENSE for more details.


##  Acknowledgement
This work was supported by the Agency for Science, Technology and Research (A*STAR), Singapore.