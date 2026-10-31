# AutoMX-CIM — standalone fresh laboratory

## English five-block edition — 2026-10-27

The current notebook has **374 cells / 135 code cells**, with all text and generated outputs in English. Fresh Run All completed **135/135** without errors. The five-block physical top retains blackbox MHA/readout integration and verified GDS/LEF views. See `docs/ENGLISH_TRANSLATION_20261027.md` and `docs/english_translation_validation_20261027.json`. The closing section contains 15 numbered references with in-text links; duplicate introductory appendices were removed. Earlier dated notes below document previous editions.

## In-cell tables and plots — 2026-10-27

The opening **Main results** index links checkpoints, architecture, baseline, energy, area, and GDS. **72 previously empty cells now have outputs**: values read from 43 bundled reports, reconstructed plots, and API summaries in definition-only cells. Source/date appears below each table without measurement banners. Presentation validation executed 80 cells, producing 121 tables and nine figures; full tool transcripts remain in log files while cells show principal results. Previously verified Run All area/energy measurements and both top renders were preserved.

At this presentation update, the main notebook contained **384 cells / 129 code cells**. Report: `docs/output_validation_20261027.json`.

## Run All measured-cost tables — 2026-10-26

This edition contained **383 cells / 129 code cells**. Run All in env_mamba completed **129/129** without exceptions in **20.97 minutes**. Results: `runs/fresh_20261026_163634_350813/`.

- `meter-architecture-theory`: input/weight pins, weight storage, transistor/SAR/CPU boundaries, and the distinction between the partition affine fit and the top 2+2 LUT.
- `meter-early-checkpoints`: logic tables, 8T DC currents, pin/leaf counts, and block32 error; PEX cells add 0–3 ns VDD energy to logs/tables.
- `meter-baseline` / `meter-energy`: 33 fresh baseline patterns, 64 conversion rows, and ten projection-summary rows; PWM50 **565.005 pJ/conversion**, PWM100 **558.009 pJ/conversion**, both with zero errors over 32 transactions.
- `meter-area`: LEF/ODB and Yosys; controller **166,569.754 µm²**, digital SAR **8,415.571 µm²**. The **170,469 µm²** ADC footprint already includes its original digital circuitry.
- KLayout uses a fixed palette: met3–met5 overview, met1–met5 details, and no overlapping text. Both overview-render cells match pixel for pixel.

Energy integrates analog-rail power and net ADC-bridge work over the transient window from the precharged operating point to post-EOC hold. Internal RTL/CPU switching is separate from these analog values. Both modes use the same hardware and differ only in PWM; each has its own calibration fit. Area is unchanged; mode50 consumes **1.254%** more in this window. Calibration is separate from the 32 projections.

Independent validation reintegrated **74 raw waveforms**, confirmed macro-area agreement with ODB and identical baseline payloads, and found zero routing violations. See `docs/measured_costs_validation_20261026.json`, `standalone_verification.json`, and `docs/MEASURED_COSTS_PROGRESS_20261026.md`.

## Cell-to-macro chapter — updated 2026-10-25

This edition contained **383 cells / 129 code cells**. Its opening lessons add MXFP4 E2M1/E8M0, signed five-bit ACT_X2, ternary encoding, an 8T schematic, SPICE construction from branches → leaf → 4×1 column → 4×4 core, acquisition/conditioning, and block32 tiling. **83 explanations immediately precede definition cells**, covering 412 functions with concrete tasks, input/output contracts, and downstream consumers. Terms are defined on first occurrence; repeated descriptions link to their original explanation.

Eleven lesson cells passed independent env_mamba execution in approximately 11 seconds: code/scale tables, 45 logic combinations, nine ngspice DC states using actual TT NFET models, source-topology comparison, device counts, and tiled projection. The earlier 114 cells and outputs were preserved; the complete October 24 Run All remained in `.executed.ipynb` at this update. These were additional checks, without assigning a new execution date to earlier native results.

Find **F1.1 — Which bits does MXFP4 contain?** near the notebook opening. Lesson functions are fully defined in cells and use a separate namespace. Subsequent Run All executions write lesson artifacts under `runs/fresh_*/cell_to_macro/`; validated figures/netlists/logs from this addition are in `docs/cim_cell_to_macro_20261025/`.

Reports: `docs/cim_lessons_validation_20261025.json` and `docs/cim_lessons_structural_validation_20261025.json`. Run lessons separately with `python scripts/validate_cim_notebook_lessons.py`; this does not restart cold PnR.

Open **AutoMX_CIM_Code_a_Chip.ipynb** from this folder with the **env_mamba** kernel, then choose **Restart Kernel & Run All**.

This is the existing design-argument notebook, ported to run with its own source and tool inputs. It does not need the development checkout. Keep the whole folder together when moving it to another drive.

```bash
cd /media/nam/EDABK/AutoMX_CIM_standalone_20261024
./run_notebook.sh
```

For headless execution, use `./run_all.sh`. The notebook creates a new `runs/fresh_*` directory for every execution. Old run directories are retained; a new run does not reuse their results.


### Function explanations and paper-style MOS drawings

Every definition cell starts with `Implementation:`, a table describing **every function/method/callback**, inputs with sources/shapes/units, return values/saved files, and downstream consumers. Each term is defined once, with explanations added only for newly introduced terms. Identical functions/contracts link to their first explanation.

The 8T schematic uses four-terminal enhancement NMOS symbols with explicit drain/gate/source/body, intermediate nodes, W/L, and rails. The next lesson enlarges an NMOS and shows conceptual active/poly/contact plan views and cross-sections rather than actual GDS. Vector files: [cell8T](docs/cim_cell_to_macro_20261025/ternary_cell_paper.pdf), [NMOS anatomy](docs/cim_cell_to_macro_20261025/nmos_device_anatomy.pdf).

The pre-deduplication explanation report is `docs/cim_function_reference_validation_20261025.json`. After consolidation, `docs/cim_note_deduplication_20261025.json` records 238 term definitions (2,445 repeated lines removed), 335 full function descriptions, and 77 reuse links; all 125 code cells, outputs, and the order of 372 cells were preserved. No internal links were broken.

## What Run All creates again

- Eight native ngspice PEX jobs: the same pair at all four load/PWM conditions.
- Three calibration, thirty projection and eight additional challenge conversions, using the coupled transistor / real SAR RTL partition.
- Independent record/state checks, frozen calibration, holdout decoding, MHA reconstruction, waveforms and figures, all read from the current run.
- Fresh SAR synthesis and a **cold top implementation from RTL**: synthesis, floorplan, PDN, placement, CTS, global routing and detailed routing.
- New top GDS/DEF/LEF, geometry inventory, bounded DRC, fresh macro-boundary signal extraction/LVS, rail connectivity, routing RC, digital TT STA and boundary Liberty.
- Current-run Icarus replay and KLayout rendering, followed by the design-decision summary and final manifest.

There is no old routed top ODB or top GDS among the source inputs. Old ADC codes, voltage records and waveforms are not seeded into review data. The historical exploratory recipes remain visible; the active final path performs the new measurements listed above.

## Included inputs and dependencies

`inputs/` carries RTL wrapper source, the analog core/acquisition and conditioner schematic/PEX models, and five hard-macro IP GDS/LEF views (CIM/acquisition, conditioner/mux, SAR ADC, MHA and readout/calibration). These are circuit/IP source inputs, rather than results of the new top run. `pdks/` carries the analog and digital SKY130 installations. `tools/` contains the OpenLane source, an offline Docker image archive, the ngspice shared runtime and Netgen 1.5.325 with a relative Tcl loader.

The host still needs Linux, Docker access, Icarus Verilog, ngspice, KLayout, Tcl (`tclsh`) and the Python notebook environment. These are operating-system tools, not the old design checkout. On the prepared server the launchers select env_mamba; set `AUTOMX_PYTHON` to another compatible Python executable if needed.

`%%standalone_runtime` defines the complete portable runtime directly in a notebook cell. The `automx_standalone` module imported by later cells is that cell-defined module. Native implementation and analysis bodies remain visible in their original cells.

Cold PnR starts in parallel with the analog measurements. Its command is printed at launch; the synthesis cell collects the current process's complete log before accepting the new outputs. Containers mount only this folder and run with networking disabled. Python guards reject design-input reads from the old checkout/PDK/OpenLane locations.

The physical profile targets a functional prototype: no filler insertion or long automatic signoff campaign. The cold flow uses KLayout as the primary GDS writer; Magic performs the independent DEF/LEF extraction for LVS. A dedicated TT stage generates fresh SPEF, STA and Liberty instead of repeating the long multicorner RCX/ETM campaign. Routing has a 32-iteration budget and stops early when clean. Independent checks record the actual result, including violations or a bounded DRC timeout. It does not certify fabrication readiness. The ground jumpers use explicit M4 landings, M5 metal and vias; rail checks use native Tcl status and log markers so a printed tool error cannot become a Python PASS.

## Outputs

After a successful run:

- The cell outputs contain the actual tool logs and new measurements.
- `runs/fresh_*/full_native/full_native/runall_manifest.json` identifies the new views.
- The same run contains `streamout/automx_cim_mixed_signal_proto.gds`, DEF/LEF, timing SPEF/LIB/SDC, conversion waveforms and tool receipts.
- `runs/fresh_*/review_data/` holds the current-run evidence used by the analysis.
- `standalone_execution.json` and `AutoMX_CIM_Code_a_Chip.executed.ipynb` are written by the headless launcher, including on failure.

The bundled Netgen runs through host Tcl because the older container Netgen can crash on this design. Its Tcl loader resolves the bundled shared library relative to itself; a native file-access trace confirmed no old design checkout reads.

If a tool fails, retain that run and inspect its log. Do not overwrite it with an older result or call an incomplete run successful. Correct the source/configuration, then Run All creates another empty output directory.

The MHA and readout physical views in `inputs/digital_blocks/` are checked against the current RTL, layout settings, clock and pinned OpenLane image. Changed or missing blocks are hardened automatically. Every Run All routes a fresh five-block parent top and checks hierarchical gate-level timing with parent and child SPEFs. The pin-only interface Liberty files are used for placement and CTS. `render_top/block_floorplan.svg` shows block boundaries and names from actual DEF/LEF data.
