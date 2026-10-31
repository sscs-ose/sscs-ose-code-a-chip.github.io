# Preview assets

The root-level PNGs are retained as intentional documentation examples, not
runtime inputs or golden-image tests. The application regenerates its own figures.
These snapshots predate final documentation polish; notebook output is authoritative
for current labels and state.

| Asset | Purpose |
| --- | --- |
| [Pipeline](../pipeline_view_preview.png) | Stage occupancy and pending memory access |
| [Array](../array_view_preview.png) | Row/column selection and stored values |
| [6T cell](../cell_view_preview.png) | Conceptual schematic and logical state |
| [Comparison](../comparison_view_preview.png) | Existing 6T model beside abstract 8T |
| [Waveform](../waveform_view_preview.png) | Cycle observations and event ordering |

To make a new snapshot, execute the relevant notebook section and use its view's
`figure.savefig("artifacts/preview.png", dpi=120)` after creating `artifacts/`.
That directory is ignored so transient outputs do not enter source control.
Only deliberately selected documentation images should be retained outside it.
