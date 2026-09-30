# OpenRAM macro views for the `ntt_macro` design point

`sky130_sram_1rw_16x256_wpr8` is the single-port 256 × 16-bit OpenRAM SKY130 macro that holds the NTT
coefficients on the HSKEM chip. The files here are the views used by the chip's place-and-route:

| File | Content |
|---|---|
| `sky130_sram_1rw_16x256_wpr8.lef` | LEF abstract (database unit 1000) |
| `sky130_sram_1rw_16x256_wpr8_TT_1p8V_25C.lib` | Liberty view, typical corner |
| `sky130_sram_1rw_16x256_wpr8_TT_1p8V_25C.adapter.diff` | the one change made to OpenRAM's Liberty file: the spare data bit of the 17-bit ports is declared, so that the view matches the LEF pins |

The GDS used for stream-out is not included (set `CAC_SRAM_GDS` in `flow/config.mk`); it is only needed
for the final layout merge, not for the metrics.

OpenRAM's timing views are produced by its analytical models, and its power views were found to be
non-physical on the chip (see the notebook, Section 7); the `ntt_macro` point is therefore compared on
area and timing only. OpenRAM is BSD-3-Clause licensed; the macro was generated for this project.
