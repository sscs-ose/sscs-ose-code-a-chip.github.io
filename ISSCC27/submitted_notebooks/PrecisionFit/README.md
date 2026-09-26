# PrecisionFit: Error-Budget-Driven FIR Filter Hardware Generator

**Licensed under the Apache License, Version 2.0** — see [`LICENSE`](LICENSE).
The generated RTL, result CSVs and figures are released under the same terms.

**The submission artifact is [`precisionfit.ipynb`](precisionfit.ipynb).**
The material in `src/` is the development and verification layer the notebook calls
into; the notebook alone tells the whole story and can be read top to bottom
without opening any `.py` file.

---

## What this is

A 17-tap symmetric lowpass FIR for 48 kHz audio, taken from a floating-point
reference all the way to synthesized Verilog, physically placed and routed on
the SkyWater SKY130 130 nm open PDK, asking one question:

> **Where can bits be removed without breaking the application's requirements —
> and does allocating bits by per-tap sensitivity beat allocating them
> uniformly?**

Every candidate design is (a) evaluated against an explicit **error budget**
(RMS ≤ 1e-3, SNR ≥ 60 dB vs. the float reference) *and* the filter's frequency
spec (0.5 dB ripple, 40 dB attenuation), (b) **proven bit-exact against a
bit-accurate fixed-point model** in RTL simulation, and (c) **synthesized with
Yosys** so the area axis is measured rather than assumed. The three headline
designs were then taken through a full LibreLane 3.x RTL-to-GDSII flow on
SKY130 to produce real µm² area and timing numbers.

---

## Headline results

### Generic-cell sweep (Filter A)

| Design | Synth cells | RMS error | SNR |
|---|---|---|---|
| Conservative uniform (widest passing) | 17,819 | 3.69e-5 | 76.6 dB |
| Best uniform (narrowest passing) | 11,466 | 2.21e-4 | 61.0 dB |
| **Sensitivity-guided (per-tap)** | **11,048** | 2.31e-4 | 60.7 dB |

Sensitivity-guided allocation lands **3.6% smaller** than the best uniform
design at a **4.2% higher RMS error** — both comfortably inside the error
budget. **This is not a clean win and is not reported as one.** The two
strategies sit on essentially the same accuracy–area frontier. The reason is
measured: the per-tap sensitivity spread is only **1.5×**, so there is little
for a non-uniform allocation to reallocate. The Filter B generalization test
flips the sign of that small difference (−4.2% cells), confirming the effect
is within sweep noise. Both outcomes are reported.

### Physical implementation (SKY130A, LibreLane 3.x)

Signoff corner: `nom_tt_025C_1v80` (typical-typical, 25 °C, 1.8 V).
Clock period: **14.6 ns (68.5 MHz)**. Die: 500 × 500 µm, 50% placement density.

| Design | Area (µm²) | TT setup slack | Placed cells |
|---|---|---|---|
| Conservative uniform | 145,389 | +1.976 ns | 27,600 |
| Best uniform | 96,137 | +4.392 ns | 18,097 |
| **Sensitivity-guided** | **94,870** | +4.238 ns | 17,773 |

All three close timing. Area ordering matches the generic-cell sweep.
Conservative→best_uniform: **33.9% area reduction**.
best_uniform→sensitivity_guided: **1.3% additional reduction** (consistent
with the small sensitivity spread measured in the sweep).

---

## Correctness

The project's central discipline is that **no RTL result is trusted unless it
matches the golden model bit-for-bit**, as raw integer bit patterns, on
impulse / step / full-scale chirp / two noise types / multitone / explicit
overflow-stress signals. Both the uniform and the per-tap paths pass this gate
on all three headline designs.

Two real, silent bugs were found by that gate during bring-up and are
documented in the notebook (section 5):

1. `shifted = rounded >>> SHIFT` assigned into a narrower wire truncates the
   *sign-fill*, not the result — the generator selects the correct upper bits
   instead.
2. The testbench's pipeline alignment (one leading zero-padding sample) was
   established by **measurement** against an impulse response, not assumed.

---

## Verification

**Simulation (Verilator 5.x, `-Wall`)**
- Lint clean on all generated RTL — no warnings
- Bit-exact against the golden model on 8 signal types including
  wrap-on-overflow, for every headline configuration (511 samples, raw
  integer comparison)
- Analytical worst-case error bounds verified to exceed empirical measurements
  on all 3 headline configs × 8 signals

**Formal (SymbiYosys + Yices + abc pdr)**
- 15 proof tasks across all 3 headline DUTs: bounded model checking (smtbmc,
  depth 24–26, complete proofs for this architecture) plus unbounded IC3/PDR
- Properties proven: reset semantics (P1), pipeline timing (P2/P3), stall
  freeze (P4s), full datapath equivalence vs independent shadow MAC (P4a),
  requantizer correctness (P4b), saturation range (P5)
- All 15 tasks PASS; fastest < 1 s, slowest ~14 s

**Mutation testing**
- 4 injected bugs (requantizer shift off-by-one, rounding constant zeroed,
  symmetric pre-adder sign-bit drop, center-tap constant off-by-one LSB)
- All 4 killed by the formal property set — confirms properties are not vacuous

**Physical implementation (LibreLane 3.x / SKY130)**
- LVS clean on all three headline designs (Netgen)
- Timing met at TT corner (nom_tt_025C_1v80) for all three
- DRC runs skipped via `--skip` due to a LibreLane 3.0.14 bug where the
  OpenROAD DRC report format switched to XML mid-flow; LVS and timing signoff
  are unaffected

---

## Repository layout

```
precisionfit/
├── LICENSE                           Apache-2.0
├── README.md                         this file
├── env/install_tools.sh              environment setup + toolchain smoke test
├── precisionfit.ipynb                the deliverable — submission artifact
├── src/python/
│   ├── paths.py                      central path resolution (cwd-independent)
│   ├── reference.py                  float64 reference filter (A + B), test signals
│   ├── fixedpoint.py                 bit-accurate golden model (uniform + per-tap)
│   ├── metrics.py                    error stats, spec margins, analytical bounds
│   ├── sanity_check.py               convergence + path-equivalence checks
│   ├── rtlgen.py                     Verilog generator (uniform + per-tap widths)
│   ├── regen_rtl.py                  regenerates committed RTL; checks for drift
│   ├── verify_rtl.py                 bit-exact RTL-vs-model correctness gate
│   ├── synth_yosys.py                Yosys wrapper, parses cell-count JSON
│   ├── search.py                     uniform precision sweep
│   ├── sweep_with_synth.py           uniform sweep + synthesis (Filter A)
│   ├── sensitivity.py                per-tap sensitivity (both methods) + allocation
│   ├── sensitivity_search.py         sensitivity-guided sweep + synthesis
│   ├── build_comparison.py           three-way table + Pareto plot
│   ├── final_stress_test.py          stress set + empirical-vs-analytical separation
│   ├── generalization_filter_b.py    Filter B generalization test
│   ├── formal_verify.py              SymbiYosys driver + mutation tests
│   ├── _probe_ffir.py                formal shadow FIR model
│   ├── _probe_prop.py                formal property renderer
│   └── parse_openlane_results.py     LibreLane metrics parser
├── src/verilog/
│   ├── fir_symmetric.v.j2            the single RTL template (per-tap capable,
│   │                                 includes `ifdef FORMAL block for all properties)
│   ├── fir_nonuniform.v.j2           thin include wrapper (same template, no drift)
│   ├── fir_formal.v.j2               SymbiYosys harness template
│   └── rtl/                          generated .v files for the six headline designs
├── src/tb/
│   ├── fir_tb.cpp                    Verilator harness (fast path)
│   ├── fir_tb.v.j2                   Icarus harness template (fallback)
│   ├── tb_utils.py                   vector I/O + testbench rendering
│   └── build_and_run.sh              builds/runs, auto-selecting the backend
├── formal/                           SymbiYosys working dir (generated, not committed)
├── synth/
│   ├── yosys_synth.tcl               generic-cell synthesis (used by the sweeps)
│   ├── constraints.sdc               shared timing constraint — 14.6 ns (68.5 MHz)
│   ├── openlane_config.json          legacy OpenLane 2 template (superseded by ol_*.yaml)
│   ├── ol_conservative_uniform.yaml  LibreLane 3.x config — conservative_uniform
│   ├── ol_best_uniform.yaml          LibreLane 3.x config — best_uniform
│   ├── ol_sensitivity_guided.yaml    LibreLane 3.x config — sensitivity_guided
│   └── sky130.tcl                    OpenROAD manual flow (reference only)
├── results/
│   ├── sweeps/                       sweep CSVs (Filter A + Filter B)
│   └── pareto/                       three-way tables, Pareto plots, stress results,
│                                     and physical_implementation_results.csv
└── report/                           figures and tables for the submission
```

---

## Reproducing everything

### Software sweeps and verification

```bash
bash env/install_tools.sh
source venv/bin/activate

# correctness first — both must pass before any result means anything
python src/python/sanity_check.py           # model converges, code paths agree
python src/python/verify_rtl.py             # generated RTL bit-exact vs model

# sweep stages that produce the committed CSVs
python src/python/sweep_with_synth.py       # uniform + synthesis   (~2 min)
python src/python/sensitivity_search.py     # sensitivity-guided    (~1 min)
python src/python/build_comparison.py       # three-way table + Pareto plot
python src/python/final_stress_test.py      # stress + bit-exactness on the 3 winners
python src/python/generalization_filter_b.py  # Filter B            (~4 min)

# formal verification (requires yosys, sby, yices)
python src/python/formal_verify.py          # proofs + mutation tests (~3 min)

# the deliverable
jupyter nbconvert --to notebook --execute --inplace precisionfit.ipynb
```

### Physical implementation (LibreLane 3.x + SKY130)

Requires LibreLane 3.x in a Python venv, Docker, and the SKY130 PDK via
`ciel`. The flow is fully specified by the three committed configs
`synth/ol_<design>.yaml`. Short form:

```bash
# install
python3 -m venv ~/.venv/librelane && source ~/.venv/librelane/bin/activate
pip install --upgrade librelane

# download PDK (one-time, ~1.5 GB)
python3 -m librelane --dockerized --install-pdk sky130A

# run all three headline designs (from project root)
cd /path/to/precisionfit
for design in conservative_uniform best_uniform sensitivity_guided; do
  python3 -m librelane \
    --docker-no-tty --dockerized --pdk-root ~/.ciel --design-dir . \
    --skip Magic.DRC --skip KLayout.DRC \
    --skip Checker.MagicDRC --skip Checker.KLayoutDRC \
    --skip KLayout.XOR --skip Checker.XOR \
    --run-tag $design synth/ol_${design}.yaml
done

# parse results into CSV
python3 src/python/parse_openlane_results.py
```

The `--skip` flags work around a LibreLane 3.0.14 bug where the OpenROAD DRC
report format switched to XML mid-flow. LVS and timing signoff are unaffected.
The `runs/` output directory is excluded from git (`.gitignore`); only the
parsed `results/pareto/physical_implementation_results.csv` is committed.

### Simulation backend

`src/tb/build_and_run.sh` prefers **Verilator** (fast) and falls back to
**Icarus Verilog**. Both harnesses implement the same stimulus protocol; the
bit-exact verdict is identical either way.

### Formal verification backend

`formal_verify.py` requires `sby` (SymbiYosys), `yosys`, and `yices` (or `z3`
for the smtbmc engine). PDR tasks additionally use `abc`. The `formal/`
directory is created on first run and is not committed.

---

## Scope and honest limitations

- **Power/energy was not measured.** No switching activity was annotated; no
  energy claim is made anywhere. Area savings are not claimed to imply energy
  savings.
- **The full sweep used generic-cell count as the area proxy** (Yosys `synth`
  + `abc -g cmos2`). Physical implementation was run only for the three Pareto-
  corner headline designs. The µm² ordering confirmed the generic-cell ordering.
- **The SS-corner (max_ss_100C_1v60 with OCV derating) cannot close at a
  practical frequency** for this fully-parallel 9-multiplier FIR topology.
  The effective critical path under full derating is ~24 ns; timing signoff is
  reported at the TT corner (nom_tt_025C_1v80), the standard academic PVT
  corner.
- **One architecture** (direct-form, symmetric-folded, fully parallel, fixed
  pipeline). Transposed-form, folded or time-multiplexed variants could land
  elsewhere.
- The finite-difference *margin* sensitivity ranking is **ε-unstable** (11–44%
  rank agreement across decades of ε). Allocation uses an exact, spec-weighted
  response-influence measure instead; both methods are implemented, compared
  and reported in the notebook (section 7).
- "Best" and "conservative" uniform are **sweep results bounded by the swept
  ranges** (coefficient 4–16 bits, input 6–18 bits, guard {2, 4}), not global
  optima.
- Filter A's transition band was widened from the original plan (4→7 kHz to
  4→10 kHz) because the original spec is infeasible at 17 taps; the deviation
  and its reason are stated in the notebook (section 2).
