# flow/: RTL to GDS on SKY130 with LibreLane

Every design here goes through the same flow: LibreLane 3.0.16 (Docker image
`ghcr.io/librelane/librelane:3.0.16`), PDK sky130A from ciel, cell library
`sky130_fd_sc_hd`, run from `.venv` with `--docker-no-tty --dockerized`. The
clock is 30 ns (`spec/spec.yaml`), storage flip-flops are clock-gated
(`CLK_GATE=1`, `rtl/icg.v`), and one set of settings applies to all designs.
The final design is `sidecarcim_top_ff_pipe_s3`, the SidecarCIM build with a
merge register (`PIPE_MERGE=1`) and a 3-bit shift (`SBITS=3`). The scripts
find the repository root from their own location, so they run from any
checkout.

## Shared settings

`flow/common_settings.json` holds these, and `flow/sync_clock.py` writes them
into every config (`runflow.sh` calls it first).

| Setting | Value | Why |
| --- | --- | --- |
| `CLOCK_PERIOD` | 30 ns, from `spec/spec.yaml` | one clock for every design, so energies are iso-clock |
| `SYNTH_STRATEGY` | `DELAY 4` | closes the slow corner; the default AREA strategy failed `max_ss` at 30 ns |
| `MAX_FANOUT_CONSTRAINT` | 24 (default 10) | closes the gated 8-bit array; see below |
| `FP_CORE_UTIL` | 40 | the default; no other placement settings |
| `FALLBACK_SDC` | `flow/common.sdc` | the default LibreLane SDC plus one multicycle exception that only applies to latch storage; a no-op for the final designs |
| `SYNTH_PARAMETERS` | per design | for example `USE_LATCH=0`, `K=2`, `PARALLEL=0`; see each `config.json` |

All other variables are LibreLane defaults: IO delay 20 %, derate 5 %,
uncertainty 0.25 ns, and all 9 corners signed off.

We raised the fanout limit because, with clock gating, `dcim_8bit_ff` failed
`max_ss` by 1.21 ns. The worst path started at an x-lane flop
(`u_core.xs[127]`, that is `xbit[15]`), not at weight storage. That flop
drives 64 AND gates through about 10 buffers, roughly 10 ns at the slow corner
with fanout limit 10, before the adder tree, and launch and capture sit on the
same ungated clock tree. A setup margin of 1.0 or 2.0 ns had no effect and
`FP_CORE_UTIL` 35 helped little. Fanout 24 closed it with +1.70 ns. The try
configs (`gtry*.json`) stay in the full repository.

## Designs and their final runs

These are the `run_dir` values of `results/ppa.csv`.

| Design | What it is | Final run | Reproduce |
| --- | --- | --- | --- |
| `sidecarcim_top_ff_pipe_s3` | final SidecarCIM: K=2, VB=12, `PIPE_MERGE=1`, `SBITS=3` | `RUN_2026-10-15_02-30-36` | `bash flow/runs3.sh`, then `bash flow/posts3.sh` |
| `sidecarcim_top_ff_pipe` | `PIPE_MERGE=1`, 4-bit S | `RUN_2026-10-14_04-14-01` | `librelane --docker-no-tty --dockerized flow/sidecarcim_top_ff_pipe/config.json` |
| `sidecarcim_top_ff` | first build, no merge register | `RUN_2026-10-13_01-21-51` | `bash flow/runflow.sh sidecarcim_top_ff` |
| `sidecarcim_top_ff_par` | first build with `PARALLEL=1` | `RUN_2026-10-13_01-42-04` | `bash flow/runflow.sh sidecarcim_top_ff_par` |
| `dcim_core_ff` | dense W4A4 | `RUN_2026-10-13_01-05-23` | `bash flow/runflow.sh dcim_core_ff` |
| `dcim_w6a4_ff`, `dcim_w8a4_ff` | dense W6A4, W8A4 | `RUN_2026-10-13_15-08-22`, `RUN_2026-10-13_14-40-05` | `bash flow/runw.sh` |
| `dcim_w7a4_ff`, `dcim_w4a8_ff` | dense W7A4, W4A8 | `RUN_2026-10-15_08-46-26`, `RUN_2026-10-15_09-21-00` | `bash flow/runw2.sh`, then `bash flow/pownew2.sh` |
| `dcim_8bit_ff` | dense W8A8 | `RUN_2026-10-12_zz_gtry4_final` (the `gtry4` try; config identical to `config.json`) | `bash flow/runflow.sh dcim_8bit_ff` |
| `mac_baseline` | register file and one MAC | `RUN_2026-10-13_02-08-30` | `bash flow/runflow.sh mac_baseline` |

The runs live under `flow/<design>/runs/`. `flow/runflow.sh <design>` logs to
`flow/logs/flow_<design>.log`. `bash flow/chaincg.sh` runs a list of designs
one after another and stops at the first one with setup violations; the
sidecar configs also get a synthesis-only run with the hierarchy kept
(`hier.json`, run tag `hier`) for the per-module area split. Run one LibreLane
job at a time, because the larger layouts need several GB of memory.
`bash flow/postcg.sh` derives everything after the runs: power, CSVs, cell
mix, gating slack and renders.

## Results at 30 ns

Post-layout estimates from `results/ppa.csv`. Energy is per 32x8 MVM with
real GPT-2 activity.

| Design | Area (um2) | Worst setup (ns) | fmax slow / tt (MHz) | Power (mW) | pJ per MVM | Cycles |
| --- | --- | --- | --- | --- | --- | --- |
| sidecarcim_top_ff_pipe_s3 | 204,432 | +7.16 | 43.8 / 87.5 | 8.753 | 1,312.9 | 5 |
| sidecarcim_top_ff_pipe | 209,427 | +6.24 | 42.1 / 85.1 | 8.67 | 1,300.6 | 5 |
| sidecarcim_top_ff | 203,391 | +2.55 | 36.4 / 60.0 | 10.61 | 1,273.8 | 4 |
| sidecarcim_top_ff_par | 257,795 | +2.71 | 36.6 / 60.5 | 10.07 | 1,208.4 | 4 |
| dcim_core_ff | 136,311 | +9.13 | 47.9 / 94.3 | 8.055 | 966.6 | 4 |
| dcim_w6a4_ff | 198,518 | +6.67 | 42.9 / 85.5 | 10.63 | 1,275.6 | 4 |
| dcim_w7a4_ff | 227,227 | +4.83 | 39.7 / 77.3 | 12.28 | 1,474.1 | 4 |
| dcim_w8a4_ff | 255,628 | +3.08 | 37.1 / 72.6 | 13.50 | 1,619.6 | 4 |
| dcim_w4a8_ff | 153,466 | +7.69 | 44.8 / 90.6 | 7.117 | 1,708.0 | 8 |
| dcim_8bit_ff | 282,794 | +1.70 | 35.3 / 71.8 | 13.82 | 3,317.4 | 8 |
| mac_baseline | 58,816 | +13.38 | 60.2 / 117.1 | 1.125 | 8,636.9 | 256 |

All of them meet setup and hold in all 9 corners, with DRC 0 (Magic and
KLayout), LVS 0 and antenna 0. The worst setup corner is always
`max_ss_100C_1v60`. `wns_ns` in the CSV is that slack, `fmax_mhz_est` is
1000 / (30 - slack) at that corner and `fmax_mhz_est_tt` the same at
`nom_tt_025C_1v80`. These are single-run estimates, not reruns at a faster
clock. Area is standard-cell area including taps and excluding fill
(`design__instance__area__stdcell`); core and die area are extra columns.
The two merge-register builds use a 5-cycle energy window, the 4 compute
cycles plus the cycle that updates the y register. Against the ungated runs
in `results/*_nocg.csv`, clock gating changed area by -17.3, -14.7, -10.7,
-15.7 and -29.0 % and energy by -32, -30, -29, -32 and -67 % (dcim_core_ff,
sidecarcim_top_ff, sidecarcim_top_ff_par, dcim_8bit_ff, mac_baseline).

## How power and energy are measured

- A gate-level simulation of the final netlist (`final/nl`, iverilog with the
  sky130 cell models including `dlclkp_1`) runs the same stimulus for every
  design, and y, busy and valid are checked against the reference at every
  valid edge, with 0 mismatches. A latch netlist needs `GL_UD=0.01` (cell
  delay in ns) because of a zero-delay race; the gated flip-flop netlists
  match at 0.
- `vcd_window.py` keeps only the `busy=1` window (compute cycles, no weight
  load or idle). OpenROAD/OpenSTA then reads the VCD and the nominal SPEF and
  reports power at tt, 1.80 V, 25 C, with every pin annotated.
- Energy per MVM is power x compute cycles x clock period (mW x ns = pJ), with
  4 compute cycles for the 4-bit-input arrays, 8 for the 8-bit-input arrays
  and 256 for the MAC. Energy per MAC is that divided by 256.
- `report_power -digits 6` gives the power. `ppa.csv` and
  `energy_activity.csv` store it with 4 significant figures and compute the
  energy from the unrounded value. `flow/repower.sh` reruns only the OpenSTA
  step on the saved VCDs.
- `gl_stim_npz.py` builds the stimulus from `python/vectors/*.npz`: the first
  100 cases, real = `*real_layer.npz`, random = `*random.npz`, and per case
  load the 32 rows (and sidecar columns), start and wait. For merge-register
  builds (`PIPE=1`) it expects valid one edge later. The MAC uses the RTL
  testbench VCD (`gl_stim.py`, first 7,400 edges = 25 MVMs). `gl_npz.sh`,
  `gl_all.sh` and `pow_all.sh` run the chain, and `extract_ppa.py` and
  `extract_activity.py` write `results/ppa.csv` and
  `results/energy_activity.csv`.
- Every real set is the migrated encoding of its accuracy row. For the 4-bit
  array that is `w4a4_real_layer.npz` (W4A4 + migration + clip, alpha 0.95),
  run by `flow/pow_w4a4mig.sh` on the existing layout: 868.4 pJ per MVM, input
  toggle rate 0.48. Until Oct 17 it used the naive `real_layer.npz` (no
  migration, codes 7 to 15, 76 % of them at the zero point 9, so bit-planes 0
  and 3 are nearly all ones): 966.6 pJ, toggle rate 0.16. That run is kept as
  the `real_nomig` row of `energy_activity.csv` and as `power_real_nomig.rpt`.
- Random inputs use 5 to 8 % less power than real activity on the 4-bit,
  SidecarCIM and 8-bit arrays (0.8 % on W4A8). With the naive 4-bit vectors
  the gap was 15 %.

## Weight-reload energy

`flow/extract_load.py` writes `results/load_energy.csv` from the power runs
`flow/loadpow.sh` and `loadall32.sh` (32 rows) and the second half of
`pow128c.sh` (128 rows). The gate-level simulation loads real weights, and
the power window is the time `load_en` (`w_load_en` for the sidecar) is high.
Energy per reload is power x N_IN cycles x clock, and per row it is that
divided by N_IN. A full 32-row reload costs 2,096.9 pJ for the final build,
2,025.0 for the first sidecar build, and 1,272.2, 1,606.2, 1,749.3, 1,974.0 and
1,685.2 pJ for W4A4, W6A4, W7A4, W8A4 and W4A8 (post-layout estimates; W4A4
with the `w4a4_real_layer.npz` weights, 1,297.6 pJ with the naive ones).
Compute plus reload is the sum of the `ppa.csv` and `load_energy.csv` rows of
the same design, counting one reload per weight set.

## 128-row layouts

`flow/p128/` holds 128-row layouts of the final SidecarCIM build with K=4 and
of dense W6A4 and W4A4, all at a 35 ns clock and otherwise with the shared
settings (DELAY 4, fanout 24, util 40). Their configs hold their own clock, so
`sync_clock.py` leaves them alone; the `c40_*` configs are for a 40 ns clock
and were not run. Power runs with `bash flow/pow128c.sh 35` (compute: 50 cases of
`r128_*_real_layer.npz`, a 5-cycle window for SidecarCIM and 4 for the
others; reload as above), which also runs `extract_ppa128.py` and
`extract_load.py`.

| Design (128 rows, 35 ns) | Area (um2) | Setup WNS (ns) | Hold violations | Power (mW) | pJ per MVM | Reload (pJ) |
| --- | --- | --- | --- | --- | --- | --- |
| SidecarCIM, K=4, hold-repair margins | 627,623 | +0.31 | 0 | 23.39 | 4,093.1 | 17,243 |
| W6A4 | 705,255 | +2.62 | 0 | 35.22 | 4,930.4 | 16,720 |
| W4A4 | 502,531 | +5.30 | 0 | 23.74 | 3,324.2 | 13,627 |

The first SidecarCIM layout at 35 ns had 2 hold violations (worst -0.065 ns,
`max_ff_n40C_1v95` only), so we reran it with the hold-repair margins raised:
`PL_RESIZER_HOLD_SLACK_MARGIN` 0.2 (default 0.1) and
`GRT_RESIZER_HOLD_SLACK_MARGIN` 0.15 (default 0.05), config
`flow/p128/c35h_s3k4/config.json`, queue `bash flow/p128q.sh 35h s3k4`, power
`bash flow/pow128h.sh`. That is the only setting that differs from the other
35 ns layouts; W6A4 and W4A4 were hold-clean and were not rerun. The rerun is
hold-clean, its area grew by 0.7 % and its setup slack fell from +1.64 to
+0.31 ns. `ppa_128.csv` keeps the first run, tagged as superseded.

The older 128-row runs at 30 ns (`flow/scale/<name>/runs/layoutcg`, configs
from `scaling.py`) used the first SidecarCIM build. Several of them violate
setup at 30 ns, and dense W8A4 did not route (OpenROAD global routing aborted
with GRT-0183 at util 25, and util 30 never finished), so only its synthesis
area exists. Those rows stay in `ppa_128.csv`, tagged "first build, 30 ns".
`flow/pow128a.sh` ran their power on the first 50 cases of
`python/vectors/r128_*_real_layer.npz`, with 0 mismatches.

## Other outputs

- `results/area_breakdown.csv` (`flow/extract_area.py`): synthesis area per
  module of the sidecar top (dense, sidecar, merge) from the run with the
  hierarchy kept. It is pre-layout, so do not mix it with the flattened
  layout area.
- `results/scaling.csv` (`flow/scaling.py`, `scalecg.sh`): synthesis area
  against N_IN = 32, 64, 128 and 256 for dcim_core, sidecarcim_top (fixed K=2,
  K scaled with rows, and the fewest K that hold accuracy) and dcim_8bit, plus
  full layouts at 128 rows. The `cg` column is 0 for the old ungated rows and
  1 for gated ones. The gated sidecar-to-dense synthesis area ratio at K=2 is
  1.41, 1.27, 1.17 and 1.10, and the 128-row layout gives 1.155. The gated
  dcim_core 128-row layout needed `FP_CORE_UTIL` 30 (see the known issues).
- Clock gating: `rtl/icg.v` instantiates `sky130_fd_sc_hd__dlclkp_1` under
  `SYNTHESIS`. CTS builds a tree for every gated clock net, and OpenSTA infers
  a clock-gating setup and hold check on every `dlclkp` GATE pin.
  `flow/cgcheck.sh <design>` reports the worst gating slack per corner
  (`results/cg_slack.csv`). Over the 9 corners the gating setup slack is 20.5
  to 24.8 ns (at `max_ss`) and the gating hold slack +0.50 to +0.76 ns (at
  `min_ff`). RTL simulation cannot check these gates; the gating checks and
  the gate-level simulation do. The gated cell mix of
  `sidecarcim_top_ff` (`results/cell_mix.csv`, `flow/cell_mix.py`) has 48
  dlclkp, 4 mux2_1 and 171 dlygate4sd3_1 cells.
- Layout images (`flow/finalrender.sh`; the submission ships only the final
  build's zoom and module views): `results/gds/<design>_full.png` (black
  background, met1 to met5 stipple, power grid and rows visible),
  `<design>_zoom.png` (a 30 um crop) and `<design>_modules.png`, a module
  overlay on the real layout. `modrender.sh` runs `dump_inst.tcl`, then
  `modules.py` classifies cells by netlist net name (`u_dense.*`, `u_side.*`
  and the combinational cone that drives `y`), and `klayout_full.py` and
  `add_legend.py` draw the image. `extract_ppa.py` refreshes
  `results/gds/<design>.gds.gz` and the flow's own `<design>.png`.

## Queue scripts and the AREA sweep

128-row routing takes hours and more than 6 GB, and the WSL memory was
shared with the accuracy runs. `flow/p128q.sh <clk> <name...>` runs the
`flow/p128/c<clk>_<name>` layouts one after another. It waits for 7 GB of free
memory before each, retries up to 3 times on a crash, switches to
`FP_CORE_UTIL` 30 only when the log shows the CTS "disconnected pin" bug, and
appends one line per layout and a final "clk<clk> done" to
`flow/logs/p128.status`. `q6.sh`, `queue*.sh`, `p128run*.sh` and `p128rest.sh`
are earlier chains of the same idea. `flow/areasweep.sh` swept the
`SYNTH_STRATEGY` AREA 0 and AREA 2 variants over the 32-row designs with
fanout 24. The 8-bit array then fails setup, so we kept DELAY 4 and fanout 24
for every design and did not study other setting combinations.

## Known issues

- OpenROAD CTS can drop one input pin of a gated-clock net at `FP_CORE_UTIL`
  40, and `Checker.DisconnectedPins` then fails after routing. It hit the
  latch design and the gated dcim_core 128-row scaling layout; both were
  rerun at 30. The final 32-row designs did not trigger it.
- Files written through the `\\wsl.localhost` path can end up owned by root;
  chown them before running flows.

## Latch storage variant (dcim_core, 20 ns only)

`flow/dcim_core/config.json` builds the latch version (`USE_LATCH=1`). Its
only signed-off result is a 20 ns first pass,
`flow/dcim_core/runs/RUN_2026-10-11_15-48-25`: 109,493 um2, 13,542 cells,
9.88 mW and 790 pJ per MVM with real activity. Setup was met at tt and ff and
violated by 1.70 ns at the slow corner, with the default AREA strategy and
before the shared settings and clock gating existed. It needed
`FP_CORE_UTIL` 30 and `CTS_SINK_CLUSTERING_ENABLE=false` (CTS dropped a latch
enable sink at 40), plus the multicycle exception in `common.sdc` for
latch-to-flop paths, whose real budget is 1.5 cycles while STA gives only 0.5.
We did not rerun it at 30 ns or with the final settings, so `extract_ppa.py`
skips it. That 20 ns layout (`results/gds/dcim_core.*`) and its row
(`results/ppa_clk20.csv`) are in the full repository only.

## Script index

- Flows: `runflow.sh`, `chaincg.sh`, `runs3.sh`, `runw.sh`, `runw2.sh`,
  `try.sh`, `tryseq.sh`.
- Settings: `sync_clock.py`, `common_settings.json`, `common.sdc`.
- Power: `powpipe.sh`, `pows3.sh`, `pownew2.sh`, `loadpow.sh`, `loadall32.sh`,
  `pow128c.sh`, `pow128h.sh`, `gl_stim.py`, `gl_stim_npz.py`, `gl_sim.py`,
  `gl_all.sh`, `gl_npz.sh`, `pow_all.sh`, `pownew.sh`, `power.sh`,
  `power.tcl`, `vcd_window.py`.
- CSVs: `extract_ppa128.py`, `extract_load.py`, `extract_ppa.py`,
  `extract_activity.py`, `extract_area.py`, `cell_mix.py`, `cgcheck.sh`,
  `cgcheck.tcl`, `cgcsv.py`.
- Scaling and 128 rows: `scaling.py`, `scalecg.sh`, `p128q.sh`,
  `areasweep.sh`.
- Images: `render.sh`, `renderfull.sh`, `modrender.sh`, `finalrender.sh`,
  `klayout_render.py`, `klayout_full.py`, `modules.py`, `dump_inst.tcl`,
  `add_legend.py`.
- Everything after the runs: `postcg.sh`, `postnew.sh`, `posts3.sh`.
