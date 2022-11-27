# Necessary Assumption
You must do the following before trying to use this notebook:

`git submodule update --init`


`git submodule update --recursive`

## Directory Contents
1. `notebook.ipynb` is the Jupyter Notebook which introduces a bandgap reference circuit in Skywater 130 nm. The notebook has an interactive portion. It requires access to `lookupMOS.py` and a binary file inside `bandgapReferenceCircuit/pyMOSChar/sky130.mos.jupyterData.dat`.

2. `bandgapReferenceCircuit/` is a submodule in this repository. The submodule is my personal repository and it contains both design files and a presentation of real measurement results. 
