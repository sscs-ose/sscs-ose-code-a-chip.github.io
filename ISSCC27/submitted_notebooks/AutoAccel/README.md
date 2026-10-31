# AutoAccel: Open-Source PPA Design-Space Exploration of Multiplier Architectures on sky130

Automated Design-Space Exploration of Arithmetic Accelerators: Conventional vs. Karatsuba Multipliers on an Open-Source Flow.

AutoAccel compares conventional, single-level Karatsuba, and recursive (threshold-based) Karatsuba unsigned multipliers using parameterized SystemVerilog, simulation, formal equivalence, generic Yosys synthesis statistics, and sky130 standard-cell PPA. The current experiment focuses on integer multiplication. Mapped results report sky130_fd_sc_hd cell area, ABC static-timing delay, and static leakage; they do not include place-and-route, dynamic power, or signoff timing.

## Architectures and widths

- `conventional_multiplier` is a shift-and-add partial-product implementation in `rtl/multiplier/conventional_multiplier.sv`.
- `karatsuba_multiplier` uses one level of Karatsuba's three-product split identity in `rtl/multiplier/PARAMETERIZED_MULTIPLIER.sv`.
- `karatsuba_recursive_multiplier` (in `rtl/multiplier/karatsuba_recursive.sv`) applies Karatsuba splits recursively down to a configurable base-case width (`THRESHOLD = 8`); the two half-width products recurse and the middle product is computed exactly by a conventional instance at width `N/2 + 1`.
- All modules use parameter `N`, unsigned `N`-bit operands `A` and `B`, and a full unsigned `2*N`-bit product `P`. The single-level Karatsuba requires even `N >= 2`; the recursive design requires `N` even with the halving chain staying even above the threshold (verified and measured for `N = 8, 16, 32, 64` with `THRESHOLD = 8`).

## Repository layout

| Path | Purpose |
|---|---|
| `rtl/multiplier/` | Conventional, single-level Karatsuba, recursive Karatsuba RTL, and a comparison wrapper |
| `tb/` | Self-checking simulation testbenches |
| `formal/` | Equivalence harnesses, configurations, logs, and retained work products |
| `scripts/` | Synthesis, comparison, plotting, selection, summary, and sky130 PPA scripts |
| `pdk/sky130hd_tt.lib` | sky130_fd_sc_hd liberty (tt_025C_1v80) used for mapped PPA |
| `results/baseline.csv` | Generic cell counts and the width-specific Yosys log for each measurement |
| `results/comparison.csv` | Conventional-versus-Karatsuba comparison derived from the baseline |
| `results/architecture_recommendations.csv` | Lower-cell-count choice and reduction relative to the other architecture |
| `results/sky130_baseline.csv` | sky130 mapped area, cells, delay, depth, and leakage per architecture and width |
| `results/sky130_comparison.csv` | Mapped area/delay/leakage change versus conventional |
| `results/plots/` | Generated comparison plots |
| `results/*_yosys.log` | Yosys synthesis transcripts |
| `results/sky130_logs/` | Per-run sky130 mapping logs (yosys + ABC + stat) |
| `notebooks/` | Analysis notebook reading the audited CSVs and regenerating plots |
| `LICENSE` | Apache License 2.0 covering the repository |

## Prerequisites

The flow was checked with Python 3.12, OSS CAD Suite Yosys 0.70+190, Icarus Verilog 14.0 development build, SymbiYosys v0.70-9-g79fc9ed, and Bitwuzla 0.9.1. The checked-in sky130 mapped results were produced with the conda-forge Yosys 0.69 build (which bundles a working `yosys-abc`). Plot generation requires Matplotlib. Use a PowerShell 7 session and configure the installed OSS CAD Suite for that session:

```powershell
$suite = 'C:\path\to\oss-cad-suite' # Replace with your OSS CAD Suite installation directory
$env:PATH = "$suite\bin;$suite\lib;$env:PATH"
python --version
yosys -V
iverilog -V
```

The PATH change above applies to the current PowerShell process only. Install Python dependencies with `pip install -r requirements.txt` (Matplotlib).

## Simulation

Run the conventional testbench at its default `N=8`:

```powershell
New-Item -ItemType Directory -Force "$env:TEMP\autoaccel-sim" | Out-Null
iverilog -g2012 -s tb_conventional_multiplier -o "$env:TEMP\autoaccel-sim\conventional.vvp" rtl/multiplier/conventional_multiplier.sv tb/tb_conventional_multiplier.sv
Push-Location "$env:TEMP\autoaccel-sim"
vvp .\conventional.vvp
Pop-Location
```

The conventional bench checks 8 directed vectors and 100 pseudorandom vectors (108 total). It prints `STATUS: PASS` or `STATUS: FAIL`; it does not call `$fatal` on a mismatch, so inspect that status line rather than relying only on the simulator exit code. The random seed is not fixed by the bench. To test `N=16`, use this compile command (then run it from the temporary directory as above):

```powershell
iverilog "-Ptb_conventional_multiplier.N=16" -g2012 -s tb_conventional_multiplier -o "$env:TEMP\autoaccel-sim\conventional_N16.vvp" rtl/multiplier/conventional_multiplier.sv tb/tb_conventional_multiplier.sv
```

Run the Karatsuba bench, which instantiates separate `N=8`, `N=16`, and `N=32` configurations:

```powershell
iverilog -g2012 -s karatsuba_multiplier_tb_top -o "$env:TEMP\autoaccel-sim\karatsuba.vvp" rtl/multiplier/PARAMETERIZED_MULTIPLIER.sv tb/tb_PARAMETERIZED_KARATSUBA.sv
Push-Location "$env:TEMP\autoaccel-sim"
vvp .\karatsuba.vvp
Pop-Location
```

Each Karatsuba configuration checks 25 corner pairs, 4 directed vectors, 16 pattern pairs, and 1,000 pseudorandom vectors (1,045 total). The bench calls `$fatal` if a mismatch occurs. These are finite simulation checks against `A * B`; they are not formal proofs. The current wrapper launches all three configurations together.

For a standalone run with an unambiguous per-width result, select one parameterized bench instance. For example, for `N=16`:

```powershell
iverilog "-Pkaratsuba_multiplier_tb.N=16" -g2012 -s karatsuba_multiplier_tb -o "$env:TEMP\autoaccel-sim\karatsuba_N16.vvp" rtl/multiplier/PARAMETERIZED_MULTIPLIER.sv tb/tb_PARAMETERIZED_KARATSUBA.sv
Push-Location "$env:TEMP\autoaccel-sim"
vvp .\karatsuba_N16.vvp
Pop-Location
```

## Synthesis and results

Run the complete data flow from the repository root:

```powershell
python scripts/run_autoaccel.py
```

This workflow synthesizes both architectures at `N=8,16,32,64`, compares the results, regenerates plots, writes architecture recommendations, runs the selector unit tests, and regenerates `results/project_summary.md`. **It overwrites the corresponding CSV files, width-specific synthesis logs, plots, and summary.** Preserve or copy those artifacts before rerunning if you need to retain a prior result set.

The synthesis script uses the installed `yosys` executable and runs `read_verilog -sv`, `hierarchy -top ... -chparam N ...`, `proc; opt; techmap; opt; stat`. The reported quantity is the final generic Yosys cell count after this flow. It is a unitless count, not an area in square micrometers or a physical timing or power measurement. Comparisons use:

```text
Karatsuba reduction (%) = 100 * (conventional_cells - karatsuba_cells) / conventional_cells
```

Positive values indicate fewer generic cells for Karatsuba; negative values indicate more. The recommendation script selects the lower-count architecture and reports the magnitude of its reduction relative to the higher-count architecture. `results/baseline.csv` points to the active width-specific logs, named `*_N<width>_yosys.log`. Older unqualified logs such as `results/karatsuba_yosys.log` are retained historical artifacts and are not the source for the current CSV.

To run individual stages instead of the full workflow:

```powershell
python scripts/run_synthesis.py
python scripts/compare_results.py
python scripts/plot_results.py
python scripts/select_architecture.py
python -m unittest discover -s scripts -p 'test_select_architecture.py' -v
python scripts/generate_summary.py
```

## Formal equivalence

The retained N=8 SymbiYosys configuration compares the actual conventional and Karatsuba modules at `N=8`, with the same unconstrained operands and an assertion over the full 16-bit product. The recorded run used Bitwuzla and completed `PASS` (`rc=0`; 12 seconds) in `formal/logs/N8_sby_console_run2.log`; its status record is `formal/logs/N8_sby_status_run2.txt`.

To repeat with a fresh work directory and retain a console transcript:

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

The expected successful result is `DONE (PASS, rc=0)` in the console output and a `PASS` status in the SBY work directory. `FAIL` or a counterexample is not a proof; timeout, interrupted execution, or `UNKNOWN` remains unresolved.

**Current formal status:** N=8 is proven equivalent (both single-level and recursive architectures). N=16 is unresolved: the full-output proof and selected per-bit attempts timed out under SymbiYosys/Bitwuzla; a Yosys built-in SAT (minisat) attempt on a combinational miter also did not resolve within a 20-minute budget. Bit 0 passed, which does not establish equality of the full 32-bit output. No confirmed counterexample is present in the recorded timeout runs. No claim of N=16 equivalence is made. The recursive design was additionally verified against a bit-accurate software model: exhaustive for all N<=8 input pairs and 150,000+ directed/pseudorandom vectors at each of N=16, 32, 64.

## Current synthesis results

| Operand width | Conventional cells | Karatsuba cells | Karatsuba reduction | Lower count |
|---:|---:|---:|---:|---|
| 8 | 404 | 492 | -21.78% | Conventional |
| 16 | 1,903 | 1,685 | 11.46% | Karatsuba |
| 32 | 8,306 | 5,943 | 28.45% | Karatsuba |
| 64 | 34,837 | 21,581 | 38.05% | Karatsuba |

These values describe the saved Yosys generic-cell reports and depend on the RTL, Yosys version, and synthesis script. They do not establish physical PPA or generalize beyond the measured configurations.

## sky130 standard-cell PPA results

The `scripts/run_sky130_ppa.py` flow maps all three architectures to the SkyWater `sky130_fd_sc_hd` high-density cell library at the `tt_025C_1v80` corner. Each run performs explicit Yosys coarse synthesis (proc/flatten/opt/alumacc/techmap), `dfflibmap`, ABC technology mapping against the liberty file with the area-oriented script `scripts/abc_area.script` (`strash; map; topo`), ABC `stime` static timing, and a Yosys `stat -liberty`/`ltp` report on the mapped netlist. Mapped data is checked in under `results/sky130_baseline.csv`, `results/sky130_comparison.csv`, and `results/sky130_logs/`.

The checked-in mapped results were produced with Yosys 0.69 (conda-forge build) and its bundled ABC; the recorded flow avoids ABC's SAT-based sweeping (`&fraig`, `dch`) because it is exponential on dense multiplier netlists at N>=32.

Mapped area (um^2 of standard cells, pre-layout):

| Operand width | Conventional | Karatsuba (single) | Karatsuba (recursive) | Best area |
|---:|---:|---:|---:|---|
| 8 | 3,031.66 | 4,244.07 (+40.0%) | 2,862.75 (-5.6%) | Recursive |
| 16 | 13,370.32 | 13,700.64 (+2.5%) | 12,781.01 (-4.4%) | Recursive |
| 32 | 53,352.42 | 47,663.21 (-10.7%) | 44,480.16 (-16.6%) | Recursive |
| 64 | 215,884.55 | 171,504.49 (-20.6%) | 145,170.48 (-32.8%) | Recursive |

ABC static-timing critical-path delay (ps, area-oriented mapping, no delay target):

| Operand width | Conventional | Karatsuba (single) | Karatsuba (recursive) |
|---:|---:|---:|---:|
| 8 | 2,703 | 4,612 | 3,629 |
| 16 | 3,877 | 6,713 | 6,871 |
| 32 | 5,450 | 9,231 | 12,208 |
| 64 | 7,026 | 14,993 | 18,011 |

Interpretation and caveats:

- Under real standard-cell mapping, the recursive Karatsuba is the area winner at every measured width, including N=8. This differs from the generic-cell table above, where Karatsuba loses at N=8; the generic-cell metric and the mapped metric rank architectures differently, which is itself a useful DSE finding.
- The area-oriented mapping costs delay: Karatsuba variants trade speed for area in this flow. A delay-targeted mapping pass (`map -D` / abc9) is future work and is expected to narrow the gap.
- At N=8 the recursive design reduces to the conventional base case by construction; the ~6% area difference between the two rows reflects ABC mapping sensitivity to the initial netlist structure, not an architectural difference. Mapped comparisons should be read with this tool-dependence in mind.
- Area is the liberty cell-area sum before place-and-route and excludes routing overhead. Delay is combinational static timing at the tt_025C_1v80 corner with default wireload. Static leakage is the liberty `cell_leakage_power` sum over the mapped cells; dynamic power requires switching-activity annotation and is not reported.

## Limitations and next work

- Finish a scalable full-output N=16 formal proof; retain timeout and failure as distinct outcomes.
- Add a deterministic random seed and machine-readable failure status to the conventional simulation bench.
- The Karatsuba bench currently exercises only the Karatsuba implementation, not both architectures under one simulator test. The recursive design is not yet covered by a SystemVerilog testbench; it is verified by formal N=8 equivalence and a bit-accurate software model.
- Add a delay-targeted sky130 mapping pass (`map -D`) and an activity-annotated dynamic power estimate to complete the PPA picture.
- Add cross-platform tool setup instructions.
- The repository is licensed under Apache-2.0 and includes an analysis notebook in `notebooks/` reading the audited result CSVs. Confirm both meet the current Code-a-Chip submission instructions before submitting.
- Physical implementation (place-and-route) and dynamic power are not measured by the current flow; mapped cell area, static timing, and static leakage are reported instead.

## Project team

Two-person undergraduate ECE/VLSI team.
