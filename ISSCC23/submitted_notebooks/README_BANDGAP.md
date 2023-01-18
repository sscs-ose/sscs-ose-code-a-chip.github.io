Copyright 2022 John William Kustin

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

# Necessary Assumption
You must do the following before trying to use the `bandgap.ipynb` notebook:

`git submodule update --init`


`git submodule update --recursive`

## Directory Contents
1. `bandgap.ipynb` is the Jupyter Notebook which introduces a bandgap reference circuit in Skywater 130 nm. The notebook has an interactive portion. It requires access to `lookupMOS.py` and a binary file inside `bandgapReferenceCircuit/pyMOSChar/sky130.mos.jupyterData.dat`.

2. `bandgapReferenceCircuit/` is a submodule in this repository. The submodule is my personal repository and it contains both design files and a presentation of real measurement results. 
