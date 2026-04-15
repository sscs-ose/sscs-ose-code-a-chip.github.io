#   CABAgent: A <ins>C</ins>omprehensive Layout-Aware <ins>A</ins>nalog <ins>B</ins>enchmark Generation Framework Driven by Self-Evolving LLM <ins>Agent</ins>s for Analog Circuit Design Automation

The lack of comprehensive, layout-verified benchmarks remains a major bottleneck for AI-powered analog circuit design automation. Existing studies often focus on schematic-level circuit generation or optimization under simplified device assumptions, without foundry PDK integration, physical verification, or post-layout evaluation, thereby limiting reproducibility and practical relevance. This paper presents CABAgent, a comprehensive layout-aware analog benchmark generation framework driven by self-evolving LLM agents. Starting from natural-language circuit descriptions, interface constraints, and PDK information, CABAgent first generates validated SKY130-compatible SPICE netlists through a training-free multi-agent loop that couples circuit generation, static netlist checking, Ngspice-based validation, reflection, and knowledge curation. It then expands each validated seed into standardized benchmark packages by automatically exploring device sizing, bias conditions, and layout constraints, followed by pre-layout simulation, automatic layout generation, DRC/LVS verification, parasitic extraction, and post-layout evaluation. Using Gemini, the front end achieves 98.3% Pass@1 and 100% Pass@5 on analog circuit generation tasks. In its current implementation, CABAgent generates 20 circuit topologies and 1,000 benchmark packages within 10 hours. By producing reproducible multi-view artifacts that pair circuit intent, physical implementation, verification evidence, and pre-/post-layout performance labels, CABAgent provides a practical foundation for reproducible evaluation and future learning-based analog design research.


##  Table of Content
1. [Structure](#structure)
2. [Getting Started](#getting-started)
3. [License](#license)
4. [Acknowledgement](#acknowledgement)


##  Structure
While it is possible to have a stand-alone notebook, we have decided to split up the code into modules to improve readability and documentation. The following outline the directory structure.
```
./CABAgent/
|
├───.conda
├───.vscode
├───designs
│   ├───OTA_5T
│   |   └───SKY130
|   │       ├───inputs
|   │       ├───runs
|   │       └───results
|   │           ├───Pkg0
|   │           ├───Pkg1
|   │           ├───...
|   │           └───benchmark.json
|   └───...
├───Layout-ALIGN (submodule)
├───logs
├───src
│   ├───analogagent
│   |   ├───__init__.py
|   |   ├───agents.py
|   |   ├───curator.py
|   |   ├───main_run.py
|   |   ├───playbook.py
|   |   └───postprocess.py
│   ├───cabgen
│   |   ├───__init__.py
│   |   ├───bench_gen.py
│   |   ├───dconfig.py
│   |   ├───eda_tools.py
│   |   ├───log_manager.py
│   |   ├───netlist.py
│   |   ├───spec_manager.py
│   |   ├───visualizing.py
|   |   └───workspace.py
│   ├───dconfigs
│   |   ├───OTA_5T.yaml
|   |   └───...
│   └───design_pipeline.py
├───.env
├───.gitignore
├───.gitmodules
├───LICENSE
├───README.md
└───CABAgent.ipynb
```


##  Getting Started

### Environment Setup
```
./home/
|
├───EDA_Tools
│   ├───magic
│   ├───netgen
│   └───open_pdks
└───CABAgent
```

Suggest to setup following environment under `EDA_Tools`
```
%% install dependent packages
$ cd /home/EDA_Tools
$ sudo pip3 install flake8 setuptools-scm
$ sudo apt update
$ sudo apt install build-essential tcl-dev tk-dev libx11-dev libcairo2-dev
$ sudo apt install flex bison 

%% install magic
$ git clone https://github.com/RTimothyEdwards/magic.git
$ cd magic
$ ./configure
$ make
$ sudo make install

%% install netgen
$ cd /home/EDA_Tools
$ git clone git://opencircuitdesign.com/netgen
$ cd netgen
$ ./configure
$ make
$ sudo make install

%% install open pdk
cd /home/EDA_Tools
git clone https://github.com/RTimothyEdwards/open_pdks
cd open_pdks
./configure --enable-sky130-pdk --enable-sram-sky130
make
sudo make install
make veryclean
```

Ngspice and Klayout will be installed under `/usr/bin/` by default
```
sudo apt update
sudo apt install ngspice
sudo apt install klayout
```


##  License
This project is licensed under BSD 3 Clause. 

##  Acknowledgement
This project is supported by RIE2025 Manufacturing, Trade and Connectivity (MTC) Programmatic Fund, High Linearity Silicon Germanium Photonic Modulator for 6G Analog Radio over Fiber Project, under Grant M24M8b0004