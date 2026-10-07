# Flipside

An open-source radiation-hardening library and cost–reliability explorer for SKY130.

Mac Rogers, The University of Queensland (Australia)

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Mac-Rogers/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/flipside/flipside.ipynb)

`prot_reg` provides five hardening modes (none, TMR, feedback TMR, Hamming, DMR) behind one register interface. The notebook
applies them to a rocket's parachute-deployment controller and measures each mode's cost (area and sign-off fmax after
RTL-to-GDS in LibreLane) and reliability (fault-injection campaigns over thousands of simulated flights, including
multi-cell strikes on the routed layout).

Tools: LibreLane (Yosys, OpenROAD, KLayout), SKY130, Icarus Verilog. License: Apache 2.0.
