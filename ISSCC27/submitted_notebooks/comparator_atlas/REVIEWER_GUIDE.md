# Comparator Atlas - quick tour

**Wei-Lun Hsu - National Tsing Hua University**

[Notebook](https://github.com/WLHsu0827/sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/ISSCC27/submitted_notebooks/comparator_atlas/Comparator_Atlas.ipynb) |
[Run in Colab](https://colab.research.google.com/github/WLHsu0827/sscs-ose-code-a-chip.github.io/blob/wlhsu0827-comparator-atlas-isscc27/ISSCC27/submitted_notebooks/comparator_atlas/Comparator_Atlas.ipynb) |
[Setup and data](REPRODUCIBILITY.md)

Download the [interactive report](results/study/report.html) and open the
HTML file locally; GitHub's file viewer does not execute its JavaScript.
View or download the [poster PDF](results/study/Comparator_Atlas_Poster.pdf)
or its [preview image](results/study/poster_preview.png).

## Suggested reading order

**Archived RC-deck outcomes; model physical fidelity not yet qualified.**
These RC results are outcomes of the archived 27-device simulation decks; extracted-model physical fidelity is not yet qualified. In the pinned Magic/open_pdks pipeline, mutual capacitances are retained while grounded capacitance increases. The physical error magnitude and direction are unknown; no exact duplication factor or corrected counts or energy are inferred. C-only is not independent ground truth, and RC-versus-C performance differences cannot be attributed solely to resistance. DRC/LVS establish their recorded structural checks, not parasitic-model fidelity. Schematic results are unaffected by this extraction concern. Recorded numerical agreement and simulation coverage do not establish silicon PVT performance.
See [the model-applicability evidence](REPRODUCIBILITY.md#archived-rc-model-applicability).

**Current layout: single-row-local-pitch-b1.** All-material area decreases from
matched a1's 2074.254 to 1873.3 um2 (9.688013%), retaining 27 guarded MOS devices and 15 ports.
The paired 45-PVT qualification contains 1440 transients and 720 qualified
pairs. Both layouts and C/RC modes have 180 correct points at 2 ns.
At 1 ns, C retains 170 correct / 10 unresolved; RC changes from 156/24 to
158/22 correct/unresolved, only at SS / 1.62 V / 125 C / +/-10 mV.
Mean RC core energy changes from 421.044730 to 412.879469 fJ;
worst latency changes from 1.810632 to 1.760276 ns.
These small changes are not robust global PPA benefits.
Read the [current version and all raw/native records](layout_single_row/v2/README.md)
before the explicitly historical studies below. The 1% / 20 ps criteria are
numerical acceptance bands, not physical uncertainty bounds.

1. **Question and circuit.** Read the abstract and 27-transistor circuit guide.
   The work asks when a calibrated regenerative comparator reaches a correct
   decision before a finite deadline, and what physical costs are involved.
2. **Choose a sampled schematic specification, then inspect its failures.**
   Read the [strict specification map](results/study/specification_map/selection_map.png)
   and [108 design rows / 36 specification cells](results/study/specification_map/summary.json).
   With `local_boundary` calibration at all 49 controlled-width-stress
   conditions, every included nonzero signed sample through 30 mV must be
   correct; only then is the least mean full-cycle core energy selected.
   At 1 ns, >= 1 mV gives NONE (no feasible compared design), >= 3 mV
   chooses `lvt_balanced_4b` (294/294,
   249.655 fJ mean), and >= 30 mV chooses
   `lvt_base_3b` (98/98,
   150.531 fJ mean).
   These are post-hoc descriptions of three compared designs, not changed
   training selection, continuous coverage or a global-best claim.
   The [keyed transition matrices](results/study/specification_map/failure_transitions.png)
   and wrong-sample location/code table precede the schematic widgets.
   The selected design has the same 20 wrong samples at 1 ns and 2 ns,
   all at signed +/-1 mV. Baseline and control gain wrong decisions as
   unresolved samples settle: longer deadlines need not improve every
   outcome class. All 1,176 matched pairs and grouped counts are in the JSON.
   Locations and codes do not establish a physical failure cause.
3. **Compare the adopted layout (b1) with matched a1, then read the original-control history.**
   The current version's GDS, paired table and two-layout figures are in
   Notebook Section 8. The later original-control sections retain the historical GDS, DRC/LVS
   negative controls and matched schematic/connectivity/C/RC results.
   The historical original-control 45-condition nominal RC study gives
   156/180 correct at 1 ns and
   180/180 at its declared 2 ns
   deadline. Its worst sample is 1.835 ns at
   FS / 1.62 V / -40 C / -3 mV. The earlier five-condition pilot is retained
   separately and is not retrospectively relabeled.

The adjacent specification table reports minimum observed decision margin
and maximum sampled core energy for qualified winners. NONE stays null;
the JSON retains every qualified design and all exact limiting ties.
For selected >= 3 mV at 1 ns, the minimum sampled margin is
154.517 ps and maximum sampled
core energy is 363.217 fJ,
over the same 294 samples.
Mean energy still determines selection. These finite observations are not
noise/jitter/PVT confidence bounds, timing signoff or a worst-cycle/system
energy guarantee.

The **Waveform lab** saves the untrimmed and calibrated 1 ns figures and
reading tables before its interactive controls. Eight selected saved traces
retain source identities and complementary output thresholds; moving the
deadline rereads them, not SPICE or full-cycle energy. The examples add no
new validation coverage.

The [two-point RC sensitivity check](REPRODUCIBILITY.md#bounded-rc-sensitivity-check)
leaves the slow FS point unresolved at 2 ns under a hypothetical 20%
internal-capacitor increase. It is not a PDK uncertainty bound or full-grid
rerun. The [GDS geometry audit](results/study/gds_geometry/README.md) links
selected polygons to nets and estimates isolated sheet/plate components.
The GDS-imported RC graph still differs from MAG; neither check qualifies
the full-net parasitics. C-only is not independent ground truth, and
RC-versus-C differences do not isolate resistance.

Run all notebook
cells to regenerate the analysis from the included data; full simulations
are separate optional modes. Detailed commands, versions and limitations are
collected in [Reproducibility](REPRODUCIBILITY.md).

Original code: MIT. GitHub Copilot assisted implementation, experiment
automation, figures and documentation; the author is responsible for the work.
