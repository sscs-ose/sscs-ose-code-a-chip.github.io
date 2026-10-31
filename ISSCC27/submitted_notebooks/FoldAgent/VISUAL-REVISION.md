# Visual revision notes

The revision follows the original [Wrøngm VLSI 2026 notebook](https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/VLSI26/accepted_notebooks/Wr%C3%B8ngm/Wr%C3%B8ngm.ipynb): explain the circuit behavior before interpreting plots, and provide explicit instructions for reading a figure. The source notebook's circuit/settling discussion (cells 7–13) and plot-reading guide (cell 45) were inspected. These are editorial references; all figures here are newly drawn from our own circuit and evidence.

| Question | Design mechanism | Implementation / case | Measured result | Scope |
|---|---|---|---|---|
| Can a fixed footprint retain throughput after partitioning? | Keep arithmetic concurrency and the same-cycle return | Control/storage tier + compute tier, 32 signed products | 162 matched workloads retain throughput | Recorded workloads, 100 ns target |
| What cleared the last physical conflict? | Move diode contacts onto an accessible existing signal route | Two diodes on one return net | +8.16 µm, final native DRC and antenna counts 0 | Mechanism shown schematically |
| Does data meet the capture window? | Connect both extracted tiers and model vertical links | Light/nominal/heavy RC at typical library corner | Positive setup and hold margins | Local hold 2.448 ps remains a robustness follow-up |
| What is the physical cost of a same-cycle return? | A real combinational round trip crosses the boundary twice | Compute-enable → selected input → arithmetic → output bank | Arrival 19.692 ns; required 100.720 ns | Representative nominal path; full-design worst margins in Figure 5 |

Reader-facing names describe circuit responsibilities. Source filenames, JSON fields and archived IDs are retained. The authoring chain remains tools/build_notebook.py → executed notebook → embedded HTML. Figure sources remain review.py. No new packages or EDA experiments are required.

Figure 4 uses schematic geometry and measured move/check annotations. Figure 5 separates a conceptual timing guide from measured margins. Figure 6 derives segment times and the arrival/deadline comparison directly from the accepted timing report; a regression check verifies timing accounting.
