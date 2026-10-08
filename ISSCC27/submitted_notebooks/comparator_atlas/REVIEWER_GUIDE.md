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


## Audit route

The integrated decision JSON is [here](results/study/decision_data.json); the unchanged [strict source](presentation/specification_map.py) and [original 36-cell summary](results/study/specification_map/summary.json) define the selection. All disqualifying records link to [original/selected measurements](results/study/verified_measurements.csv) or [lower-energy-control measurements](results/study/professional/measurements.csv). Keys include design, condition, signed input, deadline and run ID. The record number is 1-based excluding the CSV header. The stored map is now the complete three-design local_boundary grid; other calibration policies remain in the original saved tables, not synthesized as missing control measurements.
