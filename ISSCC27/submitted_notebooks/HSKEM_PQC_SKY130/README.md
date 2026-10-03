# HSKEM_PQC_SKY130 — IEEE SSCS Code-a-Chip, ISSCC 2027

**Measuring the Design Decisions of an Open-Source Post-Quantum HSM Chip: ML-KEM-512 NTT and Keccak from Python Golden Model to SKY130 Layout**

- **Author:** Nguyen Tan Dat — University of Science, VNU-HCM (HCMUS) · nguyentandat08052007@gmail.com
- **License:** Apache-2.0 (see `LICENSE` and `NOTICE`)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tandat08052007/sscs-ose-code-a-chip.github.io/blob/isscc27-hskem-pqc-sky130/ISSCC27/submitted_notebooks/HSKEM_PQC_SKY130/HSKEM_PQC_SKY130.ipynb)

[Notebook](HSKEM_PQC_SKY130.ipynb) · [Routed block layouts (GDS)](https://github.com/tandat08052007/sscs-ose-code-a-chip.github.io/releases/tag/hskem-block-layouts) ·
[The ORFS build, packaged for Colab](https://github.com/tandat08052007/sscs-ose-code-a-chip.github.io/releases/tag/hskem-orfs-6101364b) ·
[Reproducing the physical design](#reproducing-the-physical-design)

## Overview

HSKEM is a post-quantum hardware security module that I designed, prototyped on a DE25-Nano FPGA board
and implemented as a SKY130 digital core with open-source tools. This submission examines the two
datapaths at the heart of ML-KEM-512 — the number-theoretic transform and the Keccak-f[1600]
permutation — and measures, from RTL to routed layout and up to the complete chip, what each
architectural decision made for the ASIC actually costs in area, latency, energy and security. From
those measurements it derives redesigns of the NTT and of the datapath around it: storing two
coefficients in every word of an OpenRAM macro and then streaming data between a two-lane engine and the
datapath, with changes that remove no check, cut a decapsulation of the whole co-processor from 99,537 to
6,856 cycles in RTL simulation, within 3 % of a compact published design, and the FPGA board reproduces
the count to the cycle.

The entry point is `HSKEM_PQC_SKY130.ipynb`, which runs locally or in Google Colab. Every table and
figure in the notebook is computed from the files in this folder, and the quantitative statements in its
text are guarded by assertions against the data, so the prose cannot silently drift from the results.

## Reviewer quick start

1. Open the notebook in Colab with the badge above and choose *Runtime → Run all*. The first cell
   fetches this folder and the YosysHQ OSS CAD Suite; nothing else needs to be installed.
2. In Colab the notebook re-runs the golden-model checks, the NIST ACVP vectors, the RTL simulations,
   the SKY130 synthesis, the design iteration, a gate-level simulation of a routed netlist and the
   leakage assessment. A complete run took about 30 minutes on a free Colab instance; the last cell
   reports the measured time of every section.
3. Place-and-route and the full-system simulation take longer than a default run should; their
   committed results are read from `results/`. Both can be repeated from the notebook, also in Colab,
   by setting `RUN_PNR_COLAB = True` (Appendix E.2, 30–45 minutes), `RUN_SYSTEM_SIM = True` (Section 8,
   about six minutes), `RUN_PACKED_SYSTEM = True` (the eight redesigned systems of Section 8, about fifteen
   minutes) or `RUN_STREAMED_SYSTEM = True` (the twelve builds of the streamed system, about a quarter of
   an hour on twelve cores and correspondingly longer on Colab's two).
4. The notebook is organized around three questions — Part I *Is it correct?*, Part II *What does it
   cost?*, Part III *Does it hold up?* — followed by findings and limitations; supporting detail is in
   Appendices A–E. A reader with ten minutes can read the "At a glance" section and the findings of
   Section 11, which close with the checks that looked right and were not, and with the lessons that
   transfer to other designs.
5. Appendix B.2 renders one of the published block layouts from its GDS file after checking its
   SHA-256; `RUN_DRC_COLAB = True` also runs the SKY130 front-end design rules on it.

## Contents

| Path | Content |
|---|---|
| `golden/mlkem_ref.py` | Independent FIPS 203 NTT and FIPS 202 Keccak-f model, checked against schoolbook multiplication, `kyber-py` and `hashlib` |
| `golden/mlkem_full.py`, `golden/acvp/` | Complete ML-KEM-512 built on the golden NTT and validated against the official NIST ACVP-Server vectors (25 key generations, 25 encapsulations, 10 decapsulations); provenance in `acvp/SOURCE.txt` |
| `golden/gen_vectors.py` | Test-vector generator for the RTL testbenches |
| `golden/packed_ntt_model.py` | Cycle-accurate model of the packed-pair, layer-fused NTT schedule, checked bit-exact against the golden model |
| `golden/leakage.py` | Fixed-versus-random TVLA on simulated register-transition traces, with a negative control; `scripts/run_leakage.sh` runs it for the FPGA configuration, with `LEAK_ASIC=1` for the single-port ASIC configuration and with `LEAK_PACKED=1` for the packed engine |
| `rtl/` | NTT engine, Barrett reducer, Keccak-f[1600] core and SRAM behavioural models, copied from the HSKEM tree by `scripts/sync_rtl.sh`; the parameterized NTT redesign (`kyber_ntt_engine_opt.sv`), the packed-pair NTT (`kyber_ntt_engine_packed.sv`, with its 24 × 128 macro binding `ntt_pair_sram_macro.sv`) and the Keccak lane wrapper for physical design |
| `hskem_rtl/` | The complete HSKEM RTL and full-system testbench used in Section 8, copied by `scripts/sync_full_rtl.sh`; one documented change (`PUBLICATION_PATCH.diff`) replaces a demo-board test credential with a public placeholder and recomputes the testbench's two provisioning tags accordingly; the redesigned systems of Section 8 are generated from it by `scripts/make_packed_system.py`, which leaves it unchanged |
| `formal/` | SAT-based proof that the Barrett reducer computes a mod q for all 2^24 inputs, with variants and a negative control |
| `figures/` | Method overview and block diagrams of HSKEM and of the NTT datapath, the layout renders, in `figures/pdf/` vector copies of the main figures, written by the notebook, and the A0 poster `figures/poster.pdf` (`scripts/make_poster.py`) |
| `tests/` | Unit tests of the analysis scripts on hand-checked inputs (`python3 -m pytest -q tests`); the notebook runs them in Appendix E.4 |
| `tb/` | Icarus Verilog testbenches (bit-exact comparison, latency and constant-time checks, zeroize, leakage traces), the read-only decapsulation cycle and state profilers, the packed engine's write-contract checker, the SRAM access counter and the activity window of the chip-level energy measurement |
| `flow/` | OpenROAD-flow-scripts design configuration, timing constraints and OpenSTA scripts for SKY130 HD, with the macro-placement and macro-pin repair hooks of the macro-store points; `flow/macros/` holds the OpenRAM views of the chip's NTT coefficient SRAM and of the 24 × 128 macro used by the packed engine, and `flow/macros/spice/` the transistor netlists of all eight macro types on the chip |
| `board/` | Measurement scripts for the DE25-Nano and ESP32: UART console, repeated two-role ML-KEM flow, repeated HSM-invariant scenario |
| `scripts/` | Simulation, Colab synthesis, place-and-route, gate-level simulation and power, corner analysis, front-end design-rule check, system-level profiling, chip-level energy (logic and SRAM), metric collection, the layout renders (`render_gds.py`, `make_layout_figures.py`, and `layout_zoom_figure.py` for the three-scale view of the released macro-store GDS) and notebook generation |
| `third_party/` | SKY130 HD functional cell models (Apache-2.0), so that routed netlists can be simulated without downloading the PDK |
| `results/` | Simulation logs, controller traces, synthesis and post-route metrics with routed netlists of the compared design points, per-block chip statistics, system-level profiles, the full chip's signoff summary, three-corner timing, front-end DRC and energy, TVLA data, and FPGA measurements with SHA-256 checksums |

## Reproducing the physical design

The place-and-route results (Sections 6–7 and Appendices B–C) were produced on Linux with a local build of OpenROAD-flow-scripts at commit `6101364b`
(OpenROAD `f5522624`). With such an installation, one design point is regenerated by

```
ORFS_ROOT=/path/to/OpenROAD-flow-scripts bash scripts/run_orfs.sh ntt_opt_pipe_w12 20
python3 scripts/collect_metrics.py
```

`scripts/run_chunk.sh` lists every design point that was run; `scripts/sta_corners.sh` repeats the corner
analysis on the routed results.

The SRAM energy of Section 8 is reproducible from the published files alone. With ngspice 41 or later
(built with KLU) and the SKY130 PDK,

```
PDK_ROOT=/path/to/pdks bash scripts/sram_energy_spice.sh /tmp/sram_energy sky130_sram_1rw_16x256_wpr8
python3 scripts/sram_energy_model.py results/fullchip/sram_macro_spice.json results/fullchip/sram_accesses.json sram_energy.json
```

simulates one macro from `flow/macros/spice/` (20 minutes to two hours per macro) and turns the committed
per-macro results into the energy of a decapsulation. The logic part, `scripts/fullchip_power.sh`, needs
the chip's layout database, which is not published (see below).

Without an ORFS installation, the exact build used here is available as a relocatable archive
(`orfs-6101364b-sky130hd.tar.xz`, about 130 MB, attached to the release
[`hskem-orfs-6101364b`](https://github.com/tandat08052007/sscs-ose-code-a-chip.github.io/releases/tag/hskem-orfs-6101364b) of the author's fork and produced by `scripts/make_orfs_bundle.sh`). It runs on a stock Ubuntu 22.04 machine,
including Colab (`RUN_PNR_COLAB = True` in Appendix E.2 of the notebook), and in a clean Ubuntu 22.04
container it reproduced every final metric of three committed layouts: the pipelined NTT (with twelve
threads and with two), the single-port NTT and the one-round-per-clock Keccak core
(`results/asic/bundle_reproduction.json`).

The routed GDS files of the block-level design points compared in the notebook are attached to the
release [`hskem-block-layouts`](https://github.com/tandat08052007/sscs-ose-code-a-chip.github.io/releases/tag/hskem-block-layouts)
of the author's fork, with their SHA-256 sums. The full-chip layout itself is not published: its logic contains the demonstration board's
provisioning test credential (see `hskem_rtl/PUBLICATION_PATCH.diff`). Its signoff results, the SHA-256 of
the GDS and a cell-level placement map without connectivity are provided in `results/fullchip/`, and a
downscaled render that shows the floorplan but resolves no cell or wire in `figures/fullchip_layout.jpg`.

## Tool versions

The committed results were produced with Icarus Verilog 12.0; the YosysHQ OSS CAD Suite 2026-09-28
(Icarus Verilog 14-devel, Yosys with the `slang` front end); OpenROAD-flow-scripts commit `6101364b`
(OpenROAD `f5522624`, with its OpenSTA); KLayout 0.30.7; Magic 8.3.629 and ngspice 41 (conda-forge build)
for the SRAM energy; and Python 3 with NumPy, pandas, Matplotlib
and `kyber-py` 1.2.0. The FPGA bitstream used for the hardware cross-check was
built with Quartus Prime Pro 26.1; it is the only non-open-source tool involved.

## Scope

This is pre-silicon design and verification work. The design has not been fabricated, and no claim of
FIPS validation is made.
