#   LearnAFE: A Learnable Analog Front-End for Keyword Spotting
This repository contains code for keyword spotting with learnable analog front-end.


##  Table of Content
1. [Structure](#structure)
2. [Getting Started](#getting-started)
3. [Customization](#customization)
4. [Architecture](#architecture)
5. [Results](#results)
6. [License](#license)
7. [Acknowledgement](#acknowledgement)


##  Structure
While it is possible to have a stand-alone notebook, we have decided to split up the code into modules to improve readability and documentation. The following outline the directory structure.
```
./LearnAFE_KWS/
|
├───AFE_Config
│   ├───Design
│   ├───SpiceAC
│   └───SpiceTrans
├───ckpts
├───Figures
├───logs
├───SpeechCommands
│   └───speech_commands_v0.02
├───src
│   ├───data
│   ├───models
│   ├───utils
│   ├───train.py
│   └───test.py
├───.gitignore
├───environment.yaml
├───README.md
└───LearnAFE_KWS.ipynb
```


##  Getting Started

### Environment Setup
```
./home/
|
├───EDA_Tools
│   ├───magic
│   └───open_pdks
└───LearnAFE_KWS
```
Suggest to setup following environment under `EDA_Tools`
```
%%install ngspice and other possible configuration files
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
%%download and install open pdk
cd /home/EDA_Tools
git clone https://github.com/RTimothyEdwards/open_pdks
cd open_pdks
./configure --enable-sky130-pdk --enable-sram-sky130
make
sudo make install
make veryclean
```

%% Python Setup
The `environment.yml` can be used as a reference for the packages required. Before running the notebook, ensure that the circuit-design tools and the required packages have been installed successfully. Additionally, create a textfile in SpeechCommands -> speech_commands_v0.02 -> noise_list.txt with the following content. This is used to add background noise to the data for a more robust result.
```
%% noise_list.txt
_background_noise_/doing_the_dishes.wav
_background_noise_/dude_miaowing.wav
_background_noise_/exercise_bike.wav
_background_noise_/pink_noise.wav
_background_noise_/running_tap.wav
_background_noise_/white_noise.wav
```


##  Customization
- Code-a-Chip
    | Data Augmentation    | Filter Version | SR  | Hop length | Overlap | Max samples | Model          | Freeze |
    |----------------------|----------------|-----|------------|---------|-------------|----------------|--------|
    | Resample + Noise     | DSF16          | 20k | 640        | False   | 30          | LearnAFE_v2    | False  |


##  Architecture
- Learnable filter-bank on time domain
    
    Waveform --> `START TRAIN` --> { Time domain filter } --> Filtered waveform --> { Spiking + Framing } --> Feature Map --> { DSCNN } --> Classification Result


##  Results
| Data Augmentation | Model         | AFE Config     | Freeze | SR   | Hop_len | Overlap | Train Acc | Valid Acc | Test Acc | 20dB | 5dB  |
|-------------------|---------------|----------------|--------|------|---------|---------|-----------|-----------|----------|------|------|
| Resample + Noise  | LearnAFE_v2   | Design/DSF16   | True   | 20k  | 640     | False   | 94.0      | 91.3      | 90.2     | 89.1 | 82.7 |
| Resample + Noise  | LearnAFE_v2   | Design/DSF16   | False  | 20k  | 640     | False   | 95.6      | 93.8      | 92.7     | 92.4 | 89.4 |


##  License
This project is licensed under the MIT License. See LICENSE for more details.


##  Acknowledgement
This work was supported by the Agency for Science, Technology and Research (A*STAR), Singapore under the Nanosystems at the Edge programme, grant No. A18A1b0055. We thank Professor Zhengya Zhang for his insightful comments to strengthen this work.
