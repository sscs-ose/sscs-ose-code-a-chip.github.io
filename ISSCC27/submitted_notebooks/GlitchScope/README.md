# GlitchScope

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/ISSCC27/submitted_notebooks/GlitchScope/GlitchScope.ipynb)

**Find where a digital circuit wastes energy on glitches, and fix it automatically.** An open, SPICE-calibrated
glitch-energy analyser and verified glitch-aware register placement for standard-cell logic (SKY130, and any Liberty
library). IEEE SSCS Code-a-Chip submission, ISSCC 2027.

**Team Glitch Hunters:** Daney Alex (INL, EPFL) · Supervisor: Prof. Mahsa Shoaran (INL, EPFL) · daney.alex@epfl.ch · GitHub [DaneyAlex5](https://github.com/DaneyAlex5)

*AI assistance.* The code, experiments and text were developed with substantial help from an AI assistant. The author defined the project, ran the server-side SPICE and GLOW experiments and reviewed the results.

© 2026 École Polytechnique Fédérale de Lausanne (EPFL). Licensed under the Apache License 2.0 (see `LICENSE`); third-party material and its licences are listed in `NOTICE`.

Two circuits with the same function and the same RTL activity can burn very different energy: unequal path delays
create *glitches*, short pulses that do no useful work but still charge capacitance. Given a gate-level netlist, a
testbench VCD (or random vectors) and a Liberty file, GlitchScope

1. replays every clock cycle with Liberty timing next to a zero-delay reference and separates required transitions
   from **glitch transitions**;
2. decides which pulses survive each gate with **M2**, a per-cell pulse-rejection model calibrated in ngspice
   (including the slope of the edge that ends a pulse), and charges filtered pulses the energy they still draw;
3. measures **where to fix**: the glitch energy removed if a gate, a block or a logic stage were glitch-free
   (interventional re-simulation), with Shapley allocation and the best joint fix set;
4. **fixes it** (`--optimize`): moves the registers (retiming, same latency) or adds pipeline stages, measuring every
   candidate's total energy (logic, glitches, flip-flops and clock tree) with a MILP whose glitch model is re-fitted
   to those measurements; writes the new netlist as `optimized.v`, certified as a legal Leiserson–Saxe retiming
   (`scripts/retiming_certificate.py`; SAT-based sequential equivalence where it completes) and checked cycle by cycle;
5. writes an interactive `report.html`, CSV tables, a glitch-only VCD and a SAIF that OpenSTA reads.

## Key results

| | |
|---|---|
| Automatic fix of a 2,368-cell 16×16 array multiplier, same latency and clock, measured in **transistor-level ngspice of the routed netlists** (extracted cells, real flip-flops and clock tree, extracted wire capacitance; 40 paired cycles) | **−36 %** energy (95 % CI 34–38 %), vs −24 % for min-period retiming; +14 % cell area; GlitchScope's model predicted −47.5 % after layout (−49 % before); all ten routed layouts DRC-clean (Magic, full SKY130 deck) |
| Same fix before layout, transistor-level ngspice (analytic clock tree, no wires) | −37 % (CI 35–39 %) vs −20 % for min-period retiming |
| Accuracy vs transistor-level SPICE on 7 circuits | glitch counts within 13 % on five (0.89–1.13×), c432 1.41×, 8×8 NOR array 1.36×; without filtering 1.8–3× over-count; energy within 13 % on six |
| 68 ISCAS'85/'89, ITC'99 and EPFL circuits | glitch share medians 13–29 % of logic energy (1.6–84 %) |
| Register placement on 16 of them plus our multiplier (model; c6288 also in SPICE) | 26–42 % below exact minimum-register retiming on the three glitch-dominated circuits (9–27 % at a tighter clock); ≤ 1 % on the others |
| vs GLOW (MILP retiming, ICCAD 2026 to appear; run on GlitchScope's retiming graphs and costs, 1-h limit, also warm-started) | ISCAS c6288: 21 % less energy in transistor-level ngspice (CI 19–24 %; model 30–31 %), and 16 % below minimum-register retiming; warm-started from minimum-register retiming, GLOW keeps that placement on all four large designs; within 2.3 % on ITC'99 control logic |
| 12 PDK corners and Monte-Carlo mismatch (GlitchScope model) | 47–50 % saving at every corner, ≥ 47.7 % on every die; better than min-period retiming on 30/30 dies at each mismatch level; with the fixed-supply choice and supply scaling, min-period retiming wins by 1–3 points at the tightest clocks (see next row) |
| Placement and supply chosen together (voltage-aware study, PDK corners, model) | beats min-period retiming at every throughput: 70 % vs 64–65 % saving at the tightest clocks |
| PicoRV32 fast multiplier (real RISC-V core, 7,977 cells, MUL instruction stream) | glitches 53 % of logic energy (36 % of total); `--optimize` −5.4 % by removing 33 flip-flops; the same placement as exact minimum-register retiming (certified), so no glitch-aware gain here |
| Operand workloads | holds on 16-bit signal data (−45 % vs −31 %); on int8 neural-network-like data neither glitch-aware nor min-period retiming pays, and `--optimize` returns minimum-register retiming (64 flip-flops, −2.7 %) |
| int8 dot-product PE (AI-accelerator building block), placed and routed | returns minimum-register retiming (glitch-aware gain within the 5 % tie): −10 % / −20 % power after layout with 5.5 / 8.3 % less area (array / Booth multiplier) |

## Quick start

```bash
pip install ".[notebook]"
glitchscope --netlist bench/netlists/mac.v --vcd bench/sim/mac.vcd \
            --lib sky130_fd_sc_hd__tt_025C_1v80.lib --groups level:8 --out report/
glitchscope --netlist bench/layout/mul16_v0.v --random-vectors 60 --period-ps 15000 \
            --lib sky130_fd_sc_hd__tt_025C_1v80.lib --optimize --out mul16_opt/      # automatic fix
```

Options: `--groups hier | level[:bands] | regex:<pattern>`, `--fixes N` (what-if edits), `--workers N`, `--spef
<file>` (post-layout wire capacitance), `--sample N` (stratified cycle sampling with 95 % confidence intervals),
`--area-tie` (final choice: fewest flip-flops within this fraction of the lowest energy, default 0.05). The event
simulator runs in a small C++ kernel compiled on first use (event-identical Python fallback).

Your own design: synthesise with `bench/synth_seq.sh <rtl.v> <top>` or any flow that writes a gate-level netlist,
simulate your testbench to a VCD, and run `glitchscope`. Pulse filtering is calibrated for 12 SKY130 and 8 GF180 cell
functions; other functions and libraries fall back to inertial delay. Another PDK, including a private one on your
own machine, needs only its Liberty file plus an optional ngspice calibration run: see
[`docs/USING_YOUR_OWN_PDK.md`](docs/USING_YOUR_OWN_PDK.md).

## Reproducing

`GlitchScope.ipynb` regenerates every figure in seconds from the cached results in `data/`; the reproduction table
in its appendix (A11) lists the script and runtime behind each cache. 76 unit and regression tests:
`python scripts/run_tests.py`. Standard benchmark sources are fetched at pinned commits and mapped locally by
`bench/fetch_benchmarks.py`; they are not redistributed, only results are.

Toolchain: Yosys 0.65, Icarus Verilog, ngspice, OpenSTA, OpenROAD + OpenROAD-flow-scripts, Magic, SKY130A (Ciel
`0fe599b`). Paths are set in `tools.env` (see `tools.env.example`). On Colab, set
`INSTALL_EDA_TOOLS = True` in the first cell for pinned litex-hub builds (live runs only; figures need none).

## Prior art

Delay-annotated glitch power is mature in commercial flows; per-cell SPICE filtering thresholds were proposed by
Villegas & Vourkas (JLPEA 2024, proprietary 32 nm data); gate sizing for glitch reduction goes back to Hashimoto et
al. (DAC 1999) and retiming for low power to Monteiro et al. (ICCAD 1993), recently formulated as a MILP with a
probabilistic switching model (GLOW, IWLS 2026 / ICCAD 2026). GlitchScope contributes an open, transistor-validated
implementation on an open PDK with public calibration data, measured (interventional) attribution instead of traced
credit, and a register-placement loop in which every candidate is measured, verified and confirmed after
open-source place and route and in SPICE.

## Licence

Copyright 2026 École Polytechnique Fédérale de Lausanne (EPFL). Licensed under the Apache License 2.0
(see `LICENSE`). Third-party material included in this folder, and third-party material that is downloaded but not
included, is listed with its licence in `NOTICE`.
