<a target="_blank" href="https://colab.research.google.com/github/onurkrts/sscs-ose-code-a-chip.github.io/blob/main/VLSI23/ChipWizard/ChipWizard.ipynb">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

# ChipWizard 

```
Copyright 2023 Integrated Circuits Design and Training Laboratory @ TUBITAK BILGEM
SPDX-License-Identifier: Apache-2.0
```

|Name|Affiliation|IEEE Member|SSCS Member|
|:--:|:----------:|:----------:|:----------:|
|Onur Karataş  <br />  Email: onur.karatas@tubitak.gov.tr|[TUTEL](https://tutel.bilgem.tubitak.gov.tr/en/), [TUBITAK BILGEM](https://bilgem.tubitak.gov.tr/en), TURKEY|No|No|

## Overview
The process of designing a custom chip involves several steps, including RTL production, synthesis, placement and routing, and layout production. The open-source Chipyard framework simplifies the process of RTL production, while Openlane streamlines the process of layout production.

RTL production with Chipyard involves defining the circuit functionality and creating a hardware description in a high-level language such as Chisel. Once the RTL code is written, it is simulated and tested using Chipyard's simulation infrastructure.

The next step involves synthesis, where the RTL code is converted into a gate-level netlist. This netlist is then passed to Openlane, which automates the placement and routing process. Openlane generates a floorplan for the design and places the gates accordingly, taking into account the size and location of the chip. Once the gates are placed, Openlane generates the routing solution, which determines the connections between the gates. This process involves selecting the most efficient routing path to minimize signal delays and optimize the chip's performance.

In conclusion ChipWizard, the combination of Chipyard and Openlane simplifies the process of designing a custom chip, making it usable on a notebook.

## Tools version
* chipyard version : 1.8.1
* openlane version : 2023.03.01_0_ge10820ec
* open_pdks.sky130a version: 1.0.403_0_g12df12e
