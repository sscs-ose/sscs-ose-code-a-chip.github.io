# HashPareto

**A reproducible, notebook-driven design-space explorer for an open-source SHA-256 core.**

HashPareto takes a verified SystemVerilog SHA-256 core, generates a family of
architectural variants (round-unrolling), hardens each one through the
open-source LibreLane RTL-to-GDS flow on the SkyWater SKY130 PDK, and reports
which variant is best for **throughput**, **area**, and **energy per hash** —
with a Pareto analysis that explains *why*.

Target: IEEE SSCS **Code-a-Chip** travel-grant notebook submission (ISSCC 2027
cycle).

## Results at a glance

4 of 5 variants hardened end-to-end (DRC/LVS/antenna clean, setup WNS = 0):

| UNROLL | Area (µm²) | Throughput (Mhash/s) | Energy/hash (nJ) | Power (mW) | Clock |
|-------:|-----------:|---------------------:|-----------------:|-----------:|------:|
| 1 | 176 750 | 0.149 | 16.94 | 2.53 | 100 ns |
| 2 | 197 497 | 0.286 | 8.98 | 2.57 | 100 ns |
| 4 | 243 908 | 0.526 | 4.96 | 2.61 | 100 ns |
| 16 | 524 671 | 0.185 | 4.95 | 0.92 | 300 ns |

**Takeaway:** unroll to 4 for the best area-energy tradeoff: 3.4× lower
energy per hash than U1 for only +38 % area, at the highest throughput of the
set. Unroll to 16 only with a wider ingress interface, since it adds 115 %
area over U4 without raising throughput or lowering energy. Functional
verification: **25/25 PASS** (5 variants × 5 cocotb suites vs
`hashlib.sha256`).

Full story in **`hashpareto.ipynb`** (the submission deliverable).


## Repository layout

```
.
|-- hashpareto.ipynb           the Code-a-Chip submission notebook
|-- data/
|   |-- metrics.csv            one row per completed LibreLane run
|   |-- pareto.csv             measured throughput + energy per hash
|   |-- cycles.csv             measured cycles per block
|   |-- figures/               Pareto, PPA, and layout figures
|   |-- layouts/               GDS-to-PNG renders
|   `-- vectors/               NIST SHA-256 test vectors
|-- docs/
|   |-- phase0_environment.md  exact toolchain versions + hashes
|   `-- phase1_verification.md bit-exact verification results (25/25 PASS)
|-- flow/variants/u<N>/        per-unroll configuration and sources
|-- rtl/                       vendored reference + generated core
|-- tools/                     run, metrics, and plotting helpers
|-- verif/cocotb/              cocotb + Verilator golden-hash harness
|-- LICENSE, NOTICE            Apache-2.0
`-- README.md
```

## Reproduce in three commands

The notebook runs from this directory using only `data/`. The commands below
regenerate the RTL checks and a hardened variant when the environment from
`docs/phase0_environment.md` is available (WSL2 + LibreLane devshell AppImage +
SKY130 via CIEL + `~/venv`).

```bash
# 1. Verify the RTL is bit-exact (~2 min)
for u in 1 2 4 8 16; do ~/venv/bin/python verif/cocotb/run.py --sim verilator --unroll $u; done

# 2. Harden one variant (~30-45 min)
tools/run_variant.sh 2 test_u2

# 3. Harvest metrics + regenerate plots
~/venv/bin/python tools/collect_metrics.py
~/venv/bin/python tools/make_plots.py
```

## Environment (summary)

The RTL-to-GDS flow runs under **WSL2 (Ubuntu 26.04)** on Windows 11, using
**LibreLane v3.0.16** (devshell AppImage: Yosys 0.62, OpenROAD, Magic 8.3.623,
Netgen 1.5.316, KLayout 0.30.7, Verilator 5.044). The **SKY130A/B** PDK is
installed via CIEL. No Docker required. Full versions and hashes:
`docs/phase0_environment.md`.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
