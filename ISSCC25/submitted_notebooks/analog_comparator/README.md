# OpenFASoC: Design of Analog Comparator with Open Source Tool
This repository contains code for analog comparator design and simualtion.


##  Design Flow
1. Design schematic using xscheme tool
2. Extract schematic SPICE file
3. Draw layout and check DRC using Magic
4. Extract GDS and SPICE with magic.
5. Run LVS check with netgen
6. Simulation SPICE file using python
