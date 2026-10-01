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

The RC numbers below come from the archived 27-device extraction, whose
physical accuracy has not been independently established. In the pinned
Magic/open_pdks flow, coupling capacitance remains while grounded capacitance
increases. Neither the size nor the direction of any physical error is known.
Do not treat the C-only netlist as ground truth or attribute RC-versus-C changes
to resistance alone. DRC/LVS and numerical checks do not establish silicon
performance. The schematic comparison is unaffected.
[Extraction details](REPRODUCIBILITY.md#archived-rc-model-applicability).

1. **Start with the question and circuit:** the abstract and 27-transistor
   guide show how offset calibration and finite decision time are evaluated.
2. **Compare the schematic candidates:** under the same local calibration
   policy, the original and selected designs make 310/392 and 372/392 correct
   decisions at 1 ns for sampled absolute inputs of at least 1 mV. The
   lower-energy control shows the energy trade-off; none is claimed to be
   best for every specification.
3. **Then inspect the layout:** the GDS, DRC/LVS negative controls and matched
   schematic/connectivity/C/RC records are linked in the notebook. On the
   45-condition nominal RC grid, 156/180 decisions meet 1 ns and 180/180 meet
   the separately declared 2 ns deadline. The slowest takes 1.835 ns
   (FS / 1.62 V / -40 C / -3 mV). The earlier five-condition pilot retains
   its original 1 ns result.

The [two-point RC sensitivity check](REPRODUCIBILITY.md#bounded-rc-sensitivity-check)
shows why the slowest 2 ns result needs context: scaling its internal
capacitor cards by a hypothetical 20% leaves the FS decision unresolved at
that deadline. This is not a measured PDK uncertainty bound or a rerun of
the full grid. The [GDS geometry audit](results/study/gds_geometry/README.md)
matches selected conductor polygons to named nets and estimates isolated
sheet and plate components. The imported GDS RC graph still differs from
the archived MAG extraction; neither check certifies the full-net parasitics.

The **Waveform lab** has eight selected saved traces linked to their source
runs, including a wrong-sign decision, its calibrated counterpart and late
RC decisions. Move the deadline cursor to inspect the complementary output
thresholds. This only rereads recorded waveforms; it does not rerun SPICE,
reduce full-cycle energy or add validation points.

For a design decision, read the
[strict schematic specification map](results/study/specification_map/selection_map.png)
and its [108 design rows / 36 specification cells](results/study/specification_map/summary.json).
This uses `local_boundary` calibration at all 49 controlled-width-stress
conditions, not the nominal 45-PVT RC grid. Only designs correct at **all**
included nonzero signed sampled inputs qualify; then the lowest measured
mean full-cycle core energy wins. At 1 ns, the >= 1 mV band has no feasible
design, >= 3 mV chooses `lvt_balanced_4b`, and >= 30 mV chooses `lvt_base_3b`.
It is post-hoc existing-data guidance, not continuous-input coverage or a
worst-cycle/system energy budget. In the Notebook, the Waveform lab saves
the untrimmed and calibrated 1 ns figures and reading tables before the
interactive controls, so static readers can see the same lesson.

Run all notebook cells to regenerate the analysis from the included data.
Fresh simulations are optional, separate modes; see
[Reproducibility](REPRODUCIBILITY.md) for commands and versions.
