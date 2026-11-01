
# AutoAccel: Open-Source PPA Design-Space Exploration of Multiplier Architectures on sky130

AutoAccel compares three unsigned integer multiplier architectures using parameterized SystemVerilog, simulation, formal equivalence checking, generic Yosys synthesis, and sky130 standard-cell mapping:

- **Conventional**: shift-and-add partial-product multiplier
- **Single-level Karatsuba**: one level of Karatsuba's three-product split
- **Recursive Karatsuba**: Karatsuba splits applied recursively down to a base-case width (`THRESHOLD = 8`)

**Status: experimental.** Results are pre-layout. Mapped metrics cover cell area, ABC static-timing delay, and static leakage only. Place-and-route, dynamic power, and signoff timing are not measured.

## Project team

Siddhesh Singh and Anshika Singh

## Current status

| Area | Status | Notes |
|---|---|---|
| RTL for all three architectures | Implemented | `rtl/multiplier/` |
| Simulation | Partial | Conventional and single-level Karatsuba have testbenches. Recursive design has no dedicated SystemVerilog testbench yet. |
| Formal equivalence | Partial | N=8 proven for single-level and recursive designs. N=16 unresolved (see below). |
| Software-model verification | Done | Recursive design checked against a bit-accurate model: exhaustive for N ≤ 8, and 150,000+ vectors each at N = 16, 32, 64. |
| Generic Yosys synthesis | Done | N = 8, 16, 32, 64 |
| sky130 mapped PPA | Done | N = 8, 16, 32, 64. Area-oriented mapping only. |
| Delay-targeted mapping | Not done | Planned (`map -D`) |
| Dynamic power | Not done | Requires switching-activity annotation |
| Place-and-route | Not done | |

## Architectures and widths

All modules take a parameter `N` and unsigned `N`-bit operands `A` and `B`, and produce a full unsigned `2N`-bit product `P`.

- `conventional_multiplier`: `rtl/multiplier/conventional_multiplier.sv`
- `karatsuba_multiplier` (single-level): `rtl/multiplier/PARAMETERIZED_MULTIPLIER.sv`. Requires even `N ≥ 2`.
- `karatsuba_recursive_multiplier`: `rtl/multiplier/karatsuba_recursive.sv`. Splits recursively down to `THRESHOLD = 8`. The middle product is computed by a conventional instance at width `N/2 + 1`. Verified and measured at N = 8, 16, 32, 64.

## Repository layout

| Path | Purpose |
|---|---|
| `rtl/multiplier/` | Conventional, single-level, and recursive Karatsuba RTL, plus a comparison wrapper |
| `tb/` | Self-checking simulation testbenches |
| `formal/` | Equivalence harnesses, configurations, logs, and work products |
| `scripts/` | Synthesis, comparison, plotting, selection, summary, and sky130 PPA scripts |
| `pdk/sky130hd_tt.lib` | sky130_fd_sc_hd liberty file (tt_025C_1v80) used for mapped PPA |
| `results/` | Generic and sky130 CSVs, comparison tables, plots, Yosys logs, and sky130 mapping logs |
| `notebooks/` | Analysis notebook that reads the CSVs and regenerates plots |
| `LICENSE` | Apache License 2.0 |

## Prerequisites

Tool versions used for each result set:

- **Simulation and formal checks**: Icarus Verilog 14.0 (development build), SymbiYosys v0.70-9-g79fc9ed, Bitwuzla 0.9.1, OSS CAD Suite Yosys 0.70+190
- **Checked-in sky130 mapped results**: conda-forge Yosys 0.69 (bundles a working `yosys-abc`)
- **Python**: 3.12. Plot generation requires Matplotlib (`pip install -r requirements.txt`).

Setup instructions below are for Windows PowerShell 7. Linux and macOS instructions are not yet documented.

```powershell
$suite = 'C:\path\to\oss-cad-suite'  # Replace with your OSS CAD Suite installation directory
$env:PATH = "$suite\bin;$suite\lib;$env:PATH"
python --version
yosys -V
iverilog -V
```

The PATH change applies only to the current PowerShell session.

## Simulation

Conventional testbench (default N=8, 108 vectors: 8 directed and 100 pseudorandom):

```powershell
New-Item -ItemType Directory -Force "$env:TEMP\autoaccel-sim" | Out-Null
iverilog -g2012 -s tb_conventional_multiplier -o "$env:TEMP\autoaccel-sim\conventional.vvp" rtl/multiplier/conventional_multiplier.sv tb/tb_conventional_multiplier.sv
Push-Location "$env:TEMP\autoaccel-sim"
vvp .\conventional.vvp
Pop-Location
```

The bench prints `STATUS: PASS` or `STATUS: FAIL` and does not call `$fatal`, so check the status line rather than the exit code. The random seed is not fixed, so results may vary between runs.

Single-level Karatsuba testbench (instantiates N = 8, 16, and 32; 1,045 vectors per configuration; calls `$fatal` on mismatch):

```powershell
iverilog -g2012 -s karatsuba_multiplier_tb_top -o "$env:TEMP\autoaccel-sim\karatsuba.vvp" rtl/multiplier/PARAMETERIZED_MULTIPLIER.sv tb/tb_PARAMETERIZED_KARATSUBA.sv
Push-Location "$env:TEMP\autoaccel-sim"
vvp .\karatsuba.vvp
Pop-Location
```

These are finite simulation checks against `A * B`, not formal proofs.

## Synthesis and results

Run the full flow from the repository root:

```powershell
python scripts/run_autoaccel.py
```

**Warning:** this overwrites the committed CSVs, width-specific synthesis logs, plots, and `results/project_summary.md`. Copy any results you want to keep before running it.

Individual stages:

```powershell
python scripts/run_synthesis.py
python scripts/compare_results.py
python scripts/plot_results.py
python scripts/select_architecture.py
python -m unittest discover -s scripts -p 'test_select_architecture.py' -v
python scripts/generate_summary.py
```

### Generic-cell results (Yosys `proc; opt; techmap; opt; stat`)

| Width | Conventional | Karatsuba (single) | Karatsuba reduction | Lower count |
|---:|---:|---:|---:|---|
| 8 | 404 | 492 | -21.78% | Conventional |
| 16 | 1,903 | 1,685 | 11.46% | Karatsuba |
| 32 | 8,306 | 5,943 | 28.45% | Karatsuba |
| 64 | 34,837 | 21,581 | 38.05% | Karatsuba |

Reduction = 100 × (conventional − karatsuba) / conventional. Positive means fewer cells for Karatsuba.

These are unitless generic-cell counts from one Yosys version and script. They are not area in µm² or a physical timing or power measurement. The table compares single-level Karatsuba only.

### sky130 mapped area (µm², pre-layout)

ABC area-oriented mapping (`scripts/abc_area.script`), liberty cell-area sum.

| Width | Conventional | Karatsuba (single) | Karatsuba (recursive) |
|---:|---:|---:|---:|
| 8 | 3,031.66 | 4,244.07 (+40.0%) | 2,862.75 (−5.6%) |
| 16 | 13,370.32 | 13,700.64 (+2.5%) | 12,781.01 (−4.4%) |
| 32 | 53,352.42 | 47,663.21 (−10.7%) | 44,480.16 (−16.6%) |
| 64 | 215,884.55 | 171,504.49 (−20.6%) | 145,170.48 (−32.8%) |

### sky130 critical-path delay (ps, ABC static timing, no delay target)

| Width | Conventional | Karatsuba (single) | Karatsuba (recursive) |
|---:|---:|---:|---:|
| 8 | 2,703 | 4,612 | 3,629 |
| 16 | 3,877 | 6,713 | 6,871 |
| 32 | 5,450 | 9,231 | 12,208 |
| 64 | 7,026 | 14,993 | 18,011 |

### Interpretation

- Recursive Karatsuba has the smallest mapped area at every measured width under this flow. Its critical-path delay is higher at every width, so no overall PPA improvement is claimed.
- The generic-cell and sky130 results rank the architectures differently at N = 8. The sky130 mapping is more representative of standard-cell area, but it depends on the mapping script and ABC behavior.
- At N = 8, the recursive design uses the conventional base case by construction. The 5.6% area difference from conventional is attributed to ABC's sensitivity to netlist structure, not to a different architecture. This has not been independently confirmed.
- Results apply only to this tool flow (Yosys 0.69 with the ABC area script) and to these four widths.

## Formal equivalence

The N=8 SymbiYosys configuration compares the conventional and Karatsuba modules with unconstrained operands and an assertion over the full 16-bit product. The recorded run (Bitwuzla, `rc=0`, about 12 seconds) is in `formal/logs/N8_sby_console_run2.log`.

To repeat with a fresh work directory:

```powershell
Push-Location formal
$tag = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$run = "work\SBY_N8_$tag"
$log = "logs\N8_$tag.log"
& sby.exe -d $run multiplier_N8_sby.sby 2>&1 | Tee-Object -FilePath $log
$proofExit = $LASTEXITCODE
"COMMAND: sby.exe -d $run multiplier_N8_sby.sby`r`nEXIT_CODE: $proofExit" | Add-Content $log
Pop-Location
if ($proofExit -ne 0) { throw "N=8 formal run failed with exit code $proofExit" }
```

Expected success: `DONE (PASS, rc=0)`. A `FAIL` or counterexample is a bug. A timeout or `UNKNOWN` is unresolved, not a pass.

**Current formal status**

- **N = 8**: proven equivalent for both single-level and recursive designs.
- **N = 16**: unresolved. The full-output proof and selected per-bit attempts timed out under SymbiYosys/Bitwuzla, and a Yosys minisat SAT attempt on a combinational miter did not finish within 20 minutes. Bit 0 passed, which does not establish equality of the full 32-bit output. No counterexample was found in the timeout runs. **No equivalence claim is made for N = 16.**
- **N ≥ 32**: no formal results. Recursive designs are checked only by simulation and the software model.

## Limitations

- Formal equivalence is established only for N = 8.
- The recursive design has no dedicated SystemVerilog testbench. It is verified by formal N=8 equivalence and the software model.
- Single-level Karatsuba and conventional designs are tested by their own benches, not under one shared methodology.
- Only unsigned multipliers are covered.
- `THRESHOLD` is fixed at 8. No threshold sweep has been run.
- Mapped PPA is pre-layout. Area excludes routing overhead, delay uses default wireload, and leakage is static only.
- Results depend on the Yosys, ABC, and liberty versions listed above.
- The conventional multiplier is a shift-and-add design, not a Wallace or Dadda tree or a Booth multiplier.

## Planned work

- Complete the N=16 formal proof, or keep it documented as unresolved.
- Add a SystemVerilog testbench for the recursive design.
- Add a fixed random seed and machine-readable failure status to the conventional testbench.
- Add a delay-targeted sky130 mapping pass (`map -D`).
- Add an activity-annotated dynamic power estimate.
- Add place-and-route results.
- Add an area-delay product analysis and a threshold sweep.
- Add a stronger baseline, such as Yosys's native `$mul` or a Booth multiplier.
- Add cross-platform setup instructions.

## License

Apache License 2.0. See `LICENSE`.
