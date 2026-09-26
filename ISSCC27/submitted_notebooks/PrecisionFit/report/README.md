# Submission figures and tables

This directory holds the figures and tables quoted in the notebook, copied here
for convenience. The notebook is the authoritative artifact; everything here is
either regenerated from it or from the scripts it calls.

| File | Content |
|---|---|
| `fig5_filter_a_pareto_frontier.png` | Filter A accuracy-area frontier, uniform vs. sensitivity-guided |
| `fig6_filter_b_pareto_frontier.png` | Filter B generalization test, same comparison |
| `three_way_comparison.csv` | Three Filter A headline designs — generic-cell area, RMS error, SNR |
| `filter_b_three_way_comparison.csv` | Same table for Filter B |
| `layout_conservative_uniform.png` | KLayout render of the conservative_uniform placed-and-routed layout |
| `layout_best_uniform.png` | KLayout render of the best_uniform placed-and-routed layout |
| `layout_sensitivity_guided.png` | KLayout render of the sensitivity_guided placed-and-routed layout |

Also relevant (written by scripts into `../results/`):

| File | Content |
|---|---|
| `../results/pareto/physical_implementation_results.csv` | **Real SKY130 µm² area and TT timing for all three headline designs** (LibreLane 3.x) |
| `../results/gds/fir_conservative_uniform.gds` | **GDS-II layout** — conservative_uniform (6.5 MB, KLayout export) |
| `../results/gds/fir_best_uniform.gds` | **GDS-II layout** — best_uniform (4.5 MB, KLayout export) |
| `../results/gds/fir_sensitivity_guided.gds` | **GDS-II layout** — sensitivity_guided (4.5 MB, KLayout export) |
| `../results/pareto/stress_test.csv` | Per-signal empirical error and separate analytical worst-case bound for all three headline designs |
| `../results/pareto/headline_configs.json` | Precision configuration for each of the three headline designs |
| `../results/sweeps/*_synth.csv` | Every accuracy-passing configuration with its synthesized cell count (raw data behind the frontier plots) |

**Power/energy is not measured anywhere in this project** — see section 9 and
section 12 of the notebook.

## Physical implementation summary

All three headline designs were placed and routed on SKY130A using LibreLane
3.0.14 at a 14.6 ns clock period (68.5 MHz, `nom_tt_025C_1v80` signoff corner):

| Design | Area (µm²) | TT setup slack | Placed cells |
|---|---|---|---|
| conservative_uniform | 145,389 | +1.976 ns | 27,600 |
| best_uniform | 96,137 | +4.392 ns | 18,097 |
| sensitivity_guided | 94,870 | +4.238 ns | 17,773 |

Area ordering confirmed to match the generic-cell sweep. The GDS-II layouts
are committed under `results/gds/`.
