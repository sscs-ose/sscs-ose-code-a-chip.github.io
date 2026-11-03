# Third-party sources

The MOS subset is pinned to google/skywater-pdk-libs-sky130_fd_pr commit f62031a1be9aefe902d6d54cddd6f59b57627436. dependency_manifest.json records each file hash, including the upstream license. Bootstrap downloads and verifies them. They are Copyright 2020 The SkyWater PDK Authors, licensed under Apache-2.0.

Supplied passive subcircuits and parameter files retain their SkyWater copyright and license headers. passives/source_manifest.json records the source revision, hashes and Git blob identities. No supplied model file is modified. A copy of the upstream license is in passives/LICENSE.

ngspice 47 is downloaded or source-built separately. Its source and binary distribution are not included here. dependency_manifest.json pins distribution URLs and hashes. Original notices remain in downloaded distributions. See https://ngspice.sourceforge.io/ and https://github.com/google/skywater-pdk-libs-sky130_fd_pr for upstream sources.

The unchanged sky130_fd_sc_hd__dfrtp_1 SPICE and its functional-reference Verilog are from google/skywater-pdk-libs-sky130_fd_sc_hd commit ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1. Five additional HVT PMOS model files are from the same pinned primitive revision as the main model subset. All eight imported files retain their original bytes and copyright headers, with Git blob and SHA-256 identities in external_sources.json. The standard-cell repository's Apache-2.0 LICENSE is included under upstream/. These are required circuit/model source assets; simulator binaries and local research downloads are excluded.

The simple POR netlist, CACE declaration/template and README are from efabless/sky130_ef_ip__simple_por commit d8a9581533238bdb99cb0389fd4387587969dc12, designed by Tim Edwards. Its Apache-2.0 LICENSE is included. Required HVL cells are from google/skywater-pdk-libs-sky130_fd_sc_hvl commit 4fd4f858d16c558a6a488b200649e909bb4dd800, with its LICENSE. New primitive models use the existing f62031a1be9aefe902d6d54cddd6f59b57627436 revision; the shared primitive license is in passives/LICENSE. por_sources.json records Git blob and SHA-256 identities. No supplied source/model file is modified.

por_models.py explicitly implements the prior legacy diffusion-resistor mapping documented by Open PDKs: https://opencircuitdesign.com/open_pdks/history.html . The unused legacy bulk port and removed deck-level .end are explained in REUSE.md. No new repair or upstream adoption is claimed. This integration does not reproduce the complete CACE system or physical signoff.


## Reference-controller companion

The error-amplifier and startup subcircuit declarations are reused from
[2AMLogic/sky130-bandgap](https://github.com/2AMLogic/sky130-bandgap/tree/49b2571054696bee9dd4e6bc074d7d9a47248181),
commit `49b2571054696bee9dd4e6bc074d7d9a47248181`, under Apache-2.0. The exact source
snapshot and its LICENSE are in `upstream/reference_supervisor/2AMLogic/sky130-bandgap/`.
The startup PNP receives an explicit grounded fourth substrate terminal; amplifier
and startup MOS geometry, contact values and multiplicities are retained. The
source testbench and forced-node directives are not imported. The reference core,
comparator and consumer integration are separately described in [REFERENCE.md](REFERENCE.md).

The added PNP primitives and nominal parameter file use SKY130 primitive commit
`f62031a1be9aefe902d6d54cddd6f59b57627436`, under the already recorded primitive
library license. Original model headers are preserved. `reference_sources.json`
pins all five added source files by Git-blob and SHA256, including the credited
source license. Earlier primitive/POR/DFF source attribution remains applicable.
