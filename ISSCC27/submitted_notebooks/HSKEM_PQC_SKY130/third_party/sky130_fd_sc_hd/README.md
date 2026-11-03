# SKY130 HD standard-cell functional models

`primitives.v.gz` and `sky130_fd_sc_hd.v.gz` are the Verilog models of the SkyWater SKY130
`sky130_fd_sc_hd` standard-cell library, as built by open_pdks and installed by `ciel`
(PDK version in `PDK_VERSION.txt`; SHA-256 of the unmodified files in `UPSTREAM_SHA256.txt`).

They let `scripts/run_gls.sh` simulate the committed routed netlists without downloading the PDK.
One mechanical change was made, because Icarus Verilog rejects text after a `` `endif `` directive,
which the models use as a comment: that trailing text was removed (see `scripts/run_gls_power.sh`,
which applies the same cleaning). The files are otherwise unchanged and gzip-compressed.

The SkyWater SKY130 PDK is licensed under the Apache License, Version 2.0
(https://github.com/google/skywater-pdk). Copyright 2020 The SkyWater PDK Authors.
