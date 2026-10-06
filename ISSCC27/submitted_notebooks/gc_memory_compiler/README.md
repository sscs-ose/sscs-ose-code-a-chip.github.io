# A 3T gain-cell (GC-eDRAM) memory compiler, from bitcell to signed-off hard block

`gain_cell_compiler.ipynb` walks through `gc_compiler`, an open-source compiler that generates
gain-cell eDRAM macros -- bitcell, array, periphery, decoder and replica column -- with post-layout
timing, retention, a refresh controller and (with LibreLane) a signed-off hard block, for SkyWater
sky130 and IHP SG13G2. The notebook is executed: every output is from a full local run.

* **Code:** https://github.com/barakhoffer/gc_compiler, release `v1.0`.
* **Run on Colab:** open the notebook's badge; its setup cells install the tools (via Nix), both PDKs
  and the compiler at that release. `FULL` also runs the slowest checks.
* **Run locally:** clone the repository and run inside `nix-shell`.

Author: Barak Hoffer

Licensed under the Apache License 2.0 (`LICENSE`).
