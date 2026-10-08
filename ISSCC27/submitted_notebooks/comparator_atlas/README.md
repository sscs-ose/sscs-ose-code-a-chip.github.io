# Comparator Atlas: correct before the deadline - or NONE?

**SKY130 StrongARM comparators | sampled design decisions**

**Wei-Lun Hsu - National Tsing Hua University**

IEEE SSCS Code-a-Chip - ISSCC 2027 | Original code: MIT

[Notebook](Comparator_Atlas.ipynb) | [Quick tour](REVIEWER_GUIDE.md) | [Reproduction](REPRODUCIBILITY.md) | [Run in Colab](https://colab.research.google.com/github/WLHsu0827/sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/ISSCC27/submitted_notebooks/comparator_atlas/Comparator_Atlas.ipynb)

Which SKY130 StrongARM comparator meets your sampled input band and deadline?
Calibration alone does not ensure a correct decision on time. Comparator Atlas lets you
compare three designs using saved schematic measurements: choose a specification, inspect
correct, wrong and unresolved outcomes, and trace failures to their exact records.
Rank mean energy only after every included point qualifies. If none does, return NONE,
not the best average.

## A three-minute route

1. Download [the self-contained report](results/study/report.html) and open it locally; GitHub's viewer does not run its controls. Try the three 1 ns presets below.
2. Inspect each design's qualification and exact failing keys, trim codes, latencies and CSV record locations. Only identity-matched retained traces get a waveform link; other keys show measurement records.
3. Compare wrong with unresolved: the same 20 selected +/-1 mV wrong samples remain at 2 ns. Then read the separate b1/a1 layout example and its physical-fidelity warning.

| 1 ns sampled band | Strict choice | Correct / included points | Mean core energy |
|---|---|---|---|
| >=1 mV | NONE | No candidate qualifies at all points | null, not zero |
| >=3 mV | lvt_balanced_4b | 294/294 | 249.655 fJ |
| >=30 mV | lvt_base_3b | 98/98 | 150.531 fJ |

This is a post-hoc comparison of exactly three schematic designs, local_boundary calibration, all 49 controlled-width-stress conditions and both signs at six finite sampled magnitudes through 30 mV. The six deadlines produce 36 cells: 28 NONE, 5 selected, 3 lower-energy control. Exact mean-energy ties retain every tied design; no interpolation or global optimization is implied. The original nine-candidate training choice is unchanged.

**Different input bands are different specifications.** The table is not a same-specification energy improvement.

**Energy and evidence contract.** Full-cycle 20-30 ns core energy excludes input/clock drivers and calibration/controller infrastructure. A null unresolved latency is not zero; failed designs and NONE retain null sampled limits. The report shows all keyed witnesses with their source table and record number; a retained raw wave is not promised for every measurement.

## Separate secondary demonstration: archived b1 vs a1

The adopted b1's 110 x 17.03 um all-material GDS bbox is 1873.3 um2 versus matched a1's 2074.254 um2 (-9.688013%), not die or signoff area. Historical native proofs are reused, not rerun. In the separate known-nonblind nominal code-zero 45-PVT comparison, b1 RC gives 158 correct / 0 wrong / 22 unresolved at 1 ns versus a1's 156/0/24; both C modes 170/0/10; all four 180/0/0 at 2 ns. Only SS / 1.62 V / 125 C / +/-10 mV improve; FS 1 ns failures/nulls remain. Mean b1 RC 412.879469 fJ and worst sampled 1.760276 ns are archived finite observations, not robust physical PPA. 1440 actual transients differ from 720 numerical pairs, 720 finest traces and 1440 two-deadline rows.

**Archived RC-deck outcomes; model physical fidelity not yet qualified.** No silicon, independently qualified physical PEX, yield, physical uncertainty or timing-signoff claim.

## Notebook, artifacts and execution

The [Notebook](Comparator_Atlas.ipynb) has the same integrated strict Python selection controls and saved static presets. Run all in the review environment; its bootstrap retrieves the submitted GitHub entry when needed and checks requirements-review.txt. Default execution analyzes saved data. Optional live/full modes require the explicitly documented tools and models and are false by default.

[Poster PDF](results/study/Comparator_Atlas_Poster.pdf) | [Poster preview](results/study/poster_preview.png) | [Abstract](results/study/abstract.txt) | [Methodology and dated execution scope](REPRODUCIBILITY.md).

Saved results, source links and maintainer executions are distinct forms of evidence; the dated reproduction scope states which source was actually executed.

GitHub Copilot assisted implementation, experiment automation, figures and documentation; the author is responsible for the work.


## Technical evidence and version history

The original Waveform Lab retains eight recorded examples with a deadline cursor and complementary-rail thresholds. The scientific and version history below keeps the calibrated schematic and nominal layout populations separate.

### Current area version: single-row-local-pitch-b1

Relative to the matched adopted a1 control, b1 reduces the
**all-material GDS bbox by 9.688013%**:
121.8 x 17.03 um (2074.254 um2) to 110 x 17.03 um (1873.3 um2).
Wells, body ties, guards and shields are included; only TEXT is excluded.
The 27 guarded PCells, device dimensions, flavors, junctions, 15 ports,
pair order, mirroring, vertical placement and local escapes are unchanged.
The fixed ordinary/ordinary and ordinary/wide intervals are 3.8 and 4.2 um;
horizontal endpoints follow placements. The prior bounded candidate passed
14 native checks on one actual DRC attempt. Both native proofs and extracts
were reused, not rerun, in full45 and publication. New local planning margins
are at least 0.20 um; inherited unchanged global M3 margin is 0.16 um.

A separate nominal, code-zero comparison of both layouts completed
**1440 transients and 720 qualified 10/5 ps pairs**, with 180 input/PVT
points per layout and export mode (C or RC). The conditions were known
before qualification; this was not a blinded test.
Both layouts and modes are correct at all 180 points at the fixed 2 ns
primary deadline. At 1 ns, C-only retains 170 correct / 10 unresolved points.
RC improves from 156 correct / 24 unresolved to 158 correct / 22 unresolved,
only at SS / 1.62 V / 125 C / +/-10 mV; FS unresolved keys remain.
No previously correct point is lost. Unresolved latency remains null.
Mean RC core energy decreases from 421.044730 to 412.879469 fJ per cycle
(-1.939286%, ratio of means; -1.945659%, mean per-point change);
worst recorded latency decreases from 1.810632 to 1.760276 ns.
Observed minimum 2 ns RC margin changes from 189.368 to 239.724 ps.
All 360 primary energy and timing changes decrease, but these finite-grid
observations do not establish robust physical global PPA benefits.
The 1% energy / 20 ps numerical criteria are not physical uncertainty bounds.

**Archived RC-deck outcomes; model physical fidelity not yet qualified.**
[Exact versioned native/raw evidence and offline audit](layout_single_row/v2/README.md).
The [prior adopted a1 version](layout_single_row/v1/README.md) is retained unchanged.
The original compact control, its historical 45-PVT study, the calibrated
49-condition schematic study and failure records remain separate and unchanged.
No silicon, independently qualified PEX or signoff result is claimed.


### Research question and contribution

Offset calibration alone does not ensure that a comparator finishes its
decision in time. This notebook follows a SKY130 StrongARM comparator from
device sizing and calibration through PVT evaluation, layout and parasitic
extraction. Interactive waveforms explain the difference between a wrong
decision and an unresolved one.

The question is how the input band and decision deadline affect correctness
and core energy after calibration, and how a smaller legal layout changes
the recorded nominal-layout outcomes under matched conditions.
The contribution is a reproducible finite-grid comparison, not a new
comparator topology. StrongARM operation and auxiliary-pair calibration
are established topics; see the complete references in the Notebook.
Nine sizing candidates were compared before a separate lower-energy
control was evaluated. Layout comparisons use the selected 27-transistor
circuit without inheriting the schematic calibration or width stress.

### Results

**Archived RC-deck outcomes; model physical fidelity not yet qualified.**

**Read the RC results as simulations of the archived extraction, not measured
silicon performance.** The pinned Magic/open_pdks flow retains coupling
capacitance while grounded capacitance increases. The C-only netlist is not an
independent reference, so the RC-versus-C difference cannot be assigned to
resistance alone. Its physical error has not been established; DRC/LVS and
timestep checks cannot settle that question. This does not affect the schematic
comparison. [Extraction details and limits](REPRODUCIBILITY.md#archived-rc-model-applicability).

The schematic comparison uses the same local calibration policy, a 1 ns
deadline and sampled absolute inputs of at least 1 mV:

| Design | Correct / points | Fully passing conditions | Mean core energy (fJ) | Gate-area proxy (um2) |
| --- | ---: | ---: | ---: | ---: |
| `baseline` | 310/392 | 16/49 | 143.01 | 10.83 |
| `lvt_balanced_4b` | 372/392 | 29/49 | 251.53 | 20.55 |
| `lvt_base_3b` | 351/392 | 18/49 | 156.65 | 10.83 |

These are finite-grid results: 45 PVT combinations at controlled width
stress plus four nominal controls. The lower-energy candidate was evaluated
after the original selection.

The [strict sampled specification map](results/study/specification_map/selection_map.png)
turns these **calibrated schematic, 49 controlled-width-stress conditions**
into a design guide, not a claim that one circuit is always best. Every
included signed sampled input must be correct before mean full-cycle core
energy is compared. At 1 ns, |input| >= 1 mV has no feasible compared design;
>= 3 mV selects `lvt_balanced_4b`, while >= 30 mV selects `lvt_base_3b`.
This post-hoc, existing-data map is not the 45-PVT RC grid, a continuous-input
guarantee or a worst-cycle/system energy bound.
[Auditable records](results/study/specification_map/summary.json) and
[recomputation instructions](REPRODUCIBILITY.md#strict-schematic-specification-map)
are included. The Notebook also saves two waveform figures and reading
tables before its widgets, so the wrong-versus-calibrated lesson is readable
without widget JavaScript.

The [matched failure transitions](results/study/specification_map/failure_transitions.png)
separate wrong from unresolved outcomes: baseline's 60 unresolved 1 ns
samples become 29 correct, nine wrong and 22 unresolved at 2 ns. The selected
design's 20 wrong samples are the same keyed set at both deadlines, all at
signed +/-1 mV; the Notebook and JSON expose locations and calibration codes,
not a physical-cause diagnosis. Qualified designs also retain minimum sampled
decision margins and maximum sampled core energies with all limiting ties.
For selected >= 3 mV at 1 ns: 154.52 ps minimum margin, 363.22 fJ sampled maximum.
These are finite observations, not timing/noise signoff or a worst-cycle/system
energy guarantee; mean-energy selection and the 36 map choices are unchanged.

#### Historical original compact control: schematic and archived RC

The original compact control passes its recorded DRC/LVS and negative controls.
Its historical nominal, code-zero study covers **45 PVT conditions and four signed
inputs per condition**. Schematic and extracted RC were simulated under the
same ngspice-47 settings and checked at 10/5 ps.

| Historical original compact control | Schematic | Archived original-control RC |
| --- | ---: | ---: |
| Correct at 1 ns | 180/180 | 156/180 |
| Correct at the declared 2 ns deadline | 180/180 | 180/180 |
| Mean core energy (fJ/cycle) | 245.84 | 425.49 |

The slowest original-control RC sample is **1.835 ns at FS / 1.62 V /
-40 C / -3 mV**. The 24 remaining 1 ns points are unresolved, not wrong.
The earlier five-condition ngspice-42 layout pilot remains a separate record:
12/20 RC points met its original 1 ns target; 20/20 met a retained 2 ns window.
The full-grid 2 ns criterion was declared separately rather than rewriting that
pilot's result.

![Historical original compact control: 45-PVT timing](results/study/postlayout_pvt45/figures/pvt45_timing.png)

This historical original-control figure is not the adopted area version.
Each cell is the maximum over four signed inputs. Black outlines mark
conditions with a missed 1 ns sample. [Vector PDF](results/study/postlayout_pvt45/figures/pvt45_timing.pdf).

### Run

Open the notebook in Colab and run all cells, or run locally:

```text
python -m pip install -r requirements-review.txt
python -m pytest --nbmake --nbmake-timeout=600 Comparator_Atlas.ipynb
```

Default execution analyzes the supplied data and remeasures saved waveforms.
Fresh SPICE examples and the full campaign are optional notebook modes.
The Colab link uses the submitted fork before upstream merge.
The project requires no commercial EDA license or paid API key.
Local CPU execution is supported; Colab's free tier has resource limits.

### Files

- `Comparator_Atlas.ipynb` — circuit, methods, plots and discussion.
- `comparator_atlas/` — simulation, calibration and analysis code.
- `results/study/` — measurements, figures, report, poster and abstract.
- `layout_single_row/v2/` — adopted b1 geometry, matched a1/b1 qualification and raw traces.
- `layout_single_row/v1/` — preserved historical adopted-a1 evidence.
- `layout_compact_repair/` — historical original compact control, extraction and physical evidence.
- `results/study/postlayout_pvt45/` — historical original-control schematic/RC grid, not candidate data.
- `REPRODUCIBILITY.md` — tool versions, data map and complete run commands.

### Scope

The calibrated schematic and nominal-layout experiments have different scopes.
Full-grid layout inputs are limited to -10, -3, +3 and +10 mV at code zero;
five conditions had been observed previously, and this is not a blinded test.
Core energy excludes external drivers and calibration infrastructure.
The results are deterministic simulations, not silicon measurements or
foundry statistical yield. References and detailed conditions are in the
notebook.

### License and acknowledgment

Original code is [MIT licensed](LICENSE). Third-party notices are retained
in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
GitHub Copilot assisted implementation, experiment automation, figures and
documentation; the author is responsible for the work.
