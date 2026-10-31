# RTL verification log

This file collects the sign-off runs of the RTL in the order they happened. Each section names the RTL and vector commits it tested, the commands and the results: every case checked against `python/golden.py`, the protocol tests, and the injected bugs (mutants) that show the tests can fail. The newest runs of the measured builds are the PIPE_MERGE + SBITS=3 sign-off for the final SidecarCIM build, the W8A4 / W6A4 and W7A4 / W4A8 sign-offs for the dense baselines, and the clock-gating re-sign-off for all other designs. Older sections name older commits, widths and clock periods than the current files.

---

# Test report: rtl/dcim_core.v
Date: 2026-10-11. RTL `rtl/dcim_core.v` @ cc78c1e. Reference `python/golden.py` `dcim_dot`. cocotb 2.1.0, Icarus 12.0, Python 3.12.3, 20 ns clock. Command `make -C tests` -> exit 0.

## Verdict
dcim_core passes every test on both storage variants. No failures.

## Vector tests (every case vs golden; stored y also == golden)
| Test | Row order | USE_LATCH=1 | USE_LATCH=0 |
|---|---|---|---|
| corners | natural | 34/34 PASS | 34/34 PASS |
| random_10k | new random order per load (seed 1234) | 10,000/10,000 PASS | 10,000/10,000 PASS |
| real_layer | reverse | 4,096/4,096 PASS | 4,096/4,096 PASS |

Weights are reloaded only when w changes (corners: 29 loads for 34 cases). start comes the cycle after the last load_en. busy/valid are checked after each of the 4 edges in every dot product.

## Protocol tests (PASS on both variants)
latency_and_hold, back_to_back, start_with_load_ignored, load_while_busy_ignored, start_while_busy_ignored, reset_mid_compute, partial_reload. Counter: PASS.

## Runtime
dcim_latch 484 s · dcim_ff 585 s · vcd 11 s · total 1090 s. About 38 cycles per case, 19 to 29 cases/s.

## VCD
results/vcd/dcim_core.vcd: 100 real-layer cases, USE_LATCH=1, 74,050 ns, 4.2 MB (`make -C tests vcd`).

## Mutation check
m1 (load not blocked while busy) caught by load_while_busy_ignored. m2 (latch open in clock-high phase) caught by all tests. m3 (one AND bit forced to 0) caught by the 3 vector tests and 4 protocol tests.

## First failing case
None.

## Behaviour the header did not state (no failures)
1. busy goes to 1 at the start edge k itself and stays 1 through edge k+ABITS-1.
2. Rows written before `rst` survive it (tested); the header did not say so.
3. With start held high, valid is high for exactly one cycle per dot product (only implied).
4. Reset landing during a load (load at k, rst at k+1) is unspecified and untested.

---

# Test report: rtl/mac_baseline.v
Date: 2026-10-11. Latency N_IN*N_OUT = 256. Reference `golden.dcim_dot`. cocotb 2.1.0, Icarus 12.0, 20 ns clock. Shared testbench `tests/core_tb.py`, wrapper `tests/test_mac_baseline.py`. `make -C tests mac` -> exit 0.

## Verdict
mac_baseline passes every test. No failures.

## Vector tests (every case vs golden; stored y also == golden)
| Test | Row order | Result |
|---|---|---|
| corners | natural | 34/34 PASS |
| random_10k | new random order per load (seed 1234) | 10,000/10,000 PASS |
| real_layer | reverse | 4,096/4,096 PASS |

Exact latency checked on every dot product: (busy, valid) = (1, 0) after edge k+255 and (0, 1) after edge k+256.

## Protocol tests (all PASS; every edge checked)
latency_and_hold (256-edge latency, 20-cycle hold), back_to_back (8 dot products at 257 cycles each), start_with_load_ignored (LOAD and DONE), load_while_busy_ignored (junk on all 256 compute edges), start_while_busy_ignored, reset_mid_compute (k+1, k+128, k+255; weights kept), partial_reload.

## Runtime
mac target 97 s (random 69 s at 144 cases/s; real 26 s). vcd_mac 1.1 s. Full `make -C tests` (all 6 targets) 2197 s under concurrent flow load. dcim_core re-run after testbench refactor: all pass (34/34, 10,000/10,000, 4,096/4,096, 7/7, both variants).

## VCD
`results/vcd/mac_baseline.vcd`: 6.1 MB, same first 100 real-layer cases as dcim_core.vcd, 578,050 ns (dcim_core: 74,050 ns). Compare energy per dot product, not average power.

## Mutation check
k1 (register-file write not blocked while busy) -> load_while_busy_ignored. k2 (y[j] drops last product), k3 (acc not cleared between columns), k4 (DONE one column early) -> all 10 tests.

## First failing case
None.

## Behaviour the header did not state
busy goes to 1 at the start edge k; weights survive `rst` (tested, not stated); y mid-COMPUTE not checked (header: meaningful only when valid=1). MAC writes the register file at the load edge, dcim_core registers the write first , invisible at the ports, both tested.

---

# Sidecar and 8-bit sign-off (2026-10-11)
RTL e55ac99, vectors 393eb8c. `make -C tests` (13 targets, sequential) -> rc=0, 6801 s. A failing test makes rc≠0.

## dcim_core re-sign-off (xbit port)
| Test | USE_LATCH=1 | USE_LATCH=0 |
|---|---|---|
| corners | 34/34 PASS | 34/34 PASS |
| random | 10,000/10,000 PASS | 10,000/10,000 PASS |
| real_layer | 4,096/4,096 PASS | 4,096/4,096 PASS |
| protocol + directed (8, incl. full_scale) | 8/8 PASS | 8/8 PASS |

xbit checked on every dot product (after edge k+c, xbit = bit-plane ABITS-1-c of x). Mutants (wrong plane, rows swapped) caught.

## dcim_8bit (W8A8, latency 8)
| Test | USE_LATCH=1 | USE_LATCH=0 |
|---|---|---|
| dense8_corners | 42/42 PASS | 42/42 PASS |
| dense8_random | 10,000/10,000 PASS | 10,000/10,000 PASS |
| dense8_real_layer | 4,096/4,096 PASS | 4,096/4,096 PASS |
| protocol + directed | 8/8 PASS | 8/8 PASS |

Runtime 1957 s / 1608 s. VCD `results/vcd/dcim_8bit.vcd` (100 real-layer cases, 8.8 MB).

## sidecarcim_top (K=2), reference `golden.sidecarcim_dot`, signed 30-bit output
| Test | PARALLEL=0, latch | PARALLEL=1, latch | PARALLEL=0, flop (spot) |
|---|---|---|---|
| sidecar_corners | 22/22 PASS | 22/22 PASS | 22/22 PASS |
| sidecar_random | 10,000/10,000 PASS | 10,000/10,000 PASS | 500/500 PASS |
| sidecar_real_layer | 4,096/4,096 PASS | 4,096/4,096 PASS | 500/500 PASS |
| protocol tests | 11/11 PASS | 11/11 PASS | 11/11 PASS |

Protocol: reset_after_load_y, latency_and_hold (exactly 4 edges), start_ignored_during_loads, loads_while_busy_ignored, start_while_busy_ignored, back_to_back (5 cycles/dot), reset_mid_compute, column_reload. Runtime 515 s / 505 s / 36 s. VCD `results/vcd/sidecarcim_top.vcd` (PARALLEL=0, 5.8 MB).

Mutants caught: start ignoring s_load_en; merge zero-extends sidecar; S written while busy; second slot dropped (PARALLEL=0 and 1).

Open at this point: the header said y=0 after reset, but per-column S registers are not reset -> y is X in simulation after power-up until every S is loaded (`powerup_reset_y`, expect_fail). After S is loaded, reset gives y=0. The next section has the fix.

## sidecarcim_top S-reset fix re-verification (7f67ae4)
RTL now resets per-column S to 0 on rst (weights and slots survive rst; S does not; reload every sidecar column after rst). y = 0 after power-up reset (was X in simulation).

| Config | Corners | Random | Real-layer | Protocol |
|---|---|---|---|---|
| K=2, PARALLEL=0, USE_LATCH=1 | 22/22 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 12/12 PASS |
| K=2, PARALLEL=1, USE_LATCH=1 | 22/22 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 12/12 PASS |
| K=2, PARALLEL=0, USE_LATCH=0 (spot) | 22/22 PASS | 500/500 PASS | 500/500 PASS | 12/12 PASS |

`powerup_reset_y` passes (no expect_fail). `reset_mid_compute` checks golden with S=0 before reload, then full golden after reloading every sidecar column.

## sidecarcim_top on flip-flop storage (PRIMARY), RTL 7f67ae4
| Config | Corners | Random | Real-layer | Protocol |
|---|---|---|---|---|
| K=2, PARALLEL=0, USE_LATCH=0 | 22/22 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 12/12 PASS |
| K=2, PARALLEL=1, USE_LATCH=0 | 22/22 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 12/12 PASS |

Replaces the 500-case spot run. No failing case. 540 s / 483 s. VCDs `results/vcd/sidecarcim_top_ff_p0.vcd`, `_p1.vcd` (first 100 real-layer cases, 74,050 ns; `make -C tests vcd_top_ff_p0` / `vcd_top_ff_p1`).

---

# VB=12 re-sign-off (2026-10-11)
Spec f61d10e: `outlier.weight_bits` 16 -> 12. RTL: uncommitted VB default 12 in `rtl/sidecar.v`, `rtl/sidecarcim_top.v` (protocol unchanged). Vectors: uncommitted `sidecar_corners.npz` (26 cases), `sidecar_random.npz` (10,000), `sidecar_real_layer.npz` (4,096), all at VB=12; stored y == golden in all three. Reference `golden.sidecarcim_dot`. cocotb 2.1.0, Icarus 12.0. Widths at VB=12: slot 17 b, sidecar acc 17 b signed, merged y 26 b signed, legal S 0..11.

Testbench widths: `tests/top_tb.py` takes VB from `spec.yaml` and YTW from `golden.merged_width`, and `setup()` checks the port widths (y = 8×26 = 208, s_load_slots = 2×17 = 34). No 16 or 30 is hard-coded in `tests/`, so the testbench needed no width fix.

## Results (sidecarcim_top, K=2)
| Config | Corners | Random | Real-layer | Protocol (existing 12) | vb_extremes (new) |
|---|---|---|---|---|---|
| PARALLEL=0, USE_LATCH=0 (primary) | 26/26 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 12/12 PASS | 33/33 PASS |
| PARALLEL=1, USE_LATCH=0 | 26/26 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 12/12 PASS | 33/33 PASS |
| PARALLEL=0, USE_LATCH=1 (spot) | 26/26 PASS | 500/500 PASS | 500/500 PASS | 12/12 PASS | 33/33 PASS |

Commands: `make -C tests top_ff`, `top_p1_ff`, `DCIM_RANDOM_LIMIT=500 TOP_REAL_LIMIT=500 make -C tests top_p0`. Each returned rc=0 with TESTS=14 PASS=13 SKIP=1 (the skip is the VCD-only test). No failing case.

## New directed test `vb_extremes` (`tests/top_tb.py`)
33 cases on one reset: y_max (w=15, x=15, every slot +2047, S=11 -> 7200·2^11 + 2·2047·15 = 14,807,010), y_min (w=0, every slot −2048 -> −61,440), dense max with side min, both slots on the same row at −2048, x=0, MSB-only x, mixed +2047/−2048 with S = 11..4, an S sweep covering 0..11 with slot values at ±extremes, and 24 random cases with values drawn from {−2048, −2047, −1, 0, 1, 2046, 2047}. Expected values come from golden. The 6 closed-form cases are also checked against formulas built only from the spec widths, so golden and RTL are both checked against the formula.

## Mutation check (PARALLEL=0, USE_LATCH=0; random and real limited to 500 cases)
| Mutant (copy of rtl/sidecarcim_top.v; rtl/ untouched) | Result |
|---|---|
| y25z: merged y kept to 25 bits, bit 25 forced to 0 | CAUGHT. 8 tests fail: corners 17/26, random 245/500, vb_extremes, and 5 protocol tests. First fail: corners `val_min_x_max`, x all 15, every val −2048, S=0, expected −61,440, got 33,492,992. real_layer 500/500 still passes (no negative y in the real-layer vectors). |
| y25s: merged y kept to 25 bits, sign-extended from bit 24 | NOT CAUGHT (13/13 pass). This is an equivalent mutant: every legal y fits in 25 bits signed (max 14,807,010 < 2^24, min −61,440), so no legal input can tell it apart. |

Note (no failure): YTW = 26 has one unneeded bit. The "+1 for the signed add" in the YTW formula is never used, because the dense term 7200·2^11 stays below 2^24 even after adding ±61,440. The same was true at VB=16 (30 b used where 29 b were enough). A port narrowed to 25 bits would fail the width assertion in `setup()` on every test (not run as a mutant).

## Runtime
top_ff 597 s · top_p1_ff 498 s · top_p0 spot 59 s · vcd_top_ff_p0 8 s · vcd_top_ff_p1 7 s · mutants 61 s + 62 s · total 1292 s (run one after another while a LibreLane run was active). Logs are in `tests/sim_build/vb12_*.log`.

## VCD (regenerated at VB=12)
`results/vcd/sidecarcim_top_ff_p0.vcd` (5.5 MB) and `_p1.vcd` (5.5 MB): the first 100 real-layer cases, 100/100 equal to golden, 74,050 ns each. `results/vcd/sidecarcim_top.vcd` (latch, P=0) is still the VB=16 version; it was not asked for, so it was not regenerated.

## Note
`tests/core_tb.py` has `CLK_NS = 20` hard-coded, but `spec.yaml` now says 30 ns. Functional results and the edge-based gate-level stimulus (`flow/gl_stim.py`) do not depend on it. Only VCD timestamps change: 20 ns per cycle. It was left unchanged so the dense VCDs, which were not rerun, stay consistent.

---

# Clock-gating re-sign-off (2026-10-12)
RTL: uncommitted `rtl/icg.v` (behavioral latch + AND in simulation) and `CLK_GATE` (default 1) in dcim_core, dcim_8bit, mac_baseline, sidecar and sidecarcim_top. Flip-flop storage is on gated clocks: one ICG per weight row (32), per register-file row (MAC, 32), per sidecar slot column (8) and per S column (8, enable `ld_j | rst`). Latch builds: RTL unchanged. Reference `golden.py`. cocotb 2.1.0, Icarus 12.0, 20 ns clock. Every run used CLK_GATE=1, the default, which is now passed explicitly as `-P...CLK_GATE=$(CLK_GATE)`.

`tests/Makefile`: `$(RTL)/icg.v` is in every source list except counter (SRCS of dcim_latch/dcim_ff/vcd/mac/vcd_mac/vcd8/vcd_top, D8SRC, TOPSRC, TOPVSRC). The new variable `CLK_GATE ?= 1` goes to the flip-flop targets (dcim_ff, mac, vcd_mac, dcim8_ff, top_ff, top_p1_ff, vcd_top_ff_p0/p1). `tests/core_tb.py`: `DCIM_REAL_LIMIT=N` limits real_layer for spot runs.

## Verdict
Every configuration passes every test. No failing case. Port behavior with CLK_GATE=1 matches golden and the header protocol. The new directed tests also pass with CLK_GATE=0 (`make <t> CLK_GATE=0`, 5 flip-flop targets), so they encode the original protocol.

## Results, flip-flop builds, CLK_GATE=1 (all vectors)
| Config | Corners | Random | Real-layer | Protocol (existing) | Clock-gating directed (new) |
|---|---|---|---|---|---|
| dcim_core FF (USE_LATCH=0) | 34/34 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 8/8 PASS | 6/6 PASS |
| dcim_8bit FF | 42/42 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 8/8 PASS | 6/6 PASS |
| mac_baseline | 34/34 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 7/7 PASS | 6/6 PASS |
| sidecarcim_top FF, K=2, PARALLEL=0 | 26/26 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 9/9 + vb_extremes 33/33 PASS | 5/5 PASS |
| sidecarcim_top FF, K=2, PARALLEL=1 | 26/26 PASS | 10,000/10,000 PASS | 4,096/4,096 PASS | 9/9 + vb_extremes 33/33 PASS | 5/5 PASS |

Each target returned rc=0: dcim TESTS=18 PASS=17 SKIP=1, mac 17/16/1, top 19/18/1 (the skip is the VCD-only test). Counter: PASS. The top protocol tests are powerup_reset_y, reset_after_load_y, latency_and_hold, start_ignored_during_loads, loads_while_busy_ignored, start_while_busy_ignored, back_to_back, reset_mid_compute and column_reload. Earlier sections counted 12 because they also included the 3 vector tests.

## Latch targets (RTL unchanged; icg.v added to the source list; 500-case spot runs)
| Config | Corners | Random | Real-layer | Protocol + directed |
|---|---|---|---|---|
| dcim_core latch | 34/34 PASS | 500/500 PASS | 500/500 PASS | 14/14 PASS |
| dcim_8bit latch | 42/42 PASS | 500/500 PASS | 500/500 PASS | 14/14 PASS |
| sidecarcim_top latch, P=0 | 26/26 PASS | 500/500 PASS | 500/500 PASS | 15/15 PASS (9 protocol, vb_extremes, 5 new) |
| sidecarcim_top latch, P=1 | 26/26 PASS | 500/500 PASS | 500/500 PASS | 15/15 PASS |

The new directed tests also pass on the latch builds, including the white-box write-edge check: with latches the row is written in the clock-low phase after edge a, so it is still old right after edge a and new after edge a+1.

## New directed tests
Storage is read back through the ports. In core_tb, x one-hot at row i (value 1) gives y[j] = w[i][j], so 32 dots read back the whole array. In top_tb, the one-hot dots give (w[i][j] << S[j]) + the slots on row i; they are checked against golden, plus one dot with x all-max. The top states use w ≥ 1, val ≠ 0 and S ≥ 1, so a lost row, slot or S always shows.

| Test (core_tb / top_tb) | What it checks |
|---|---|
| cg_rst_idle / cg_top_rst_idle | rst while loaded with no load pending (in DONE for 1 and 3 edges, and in LOAD after an idle edge). Core: every row survives. Top: every S[j] -> 0, dense rows and slots survive; S is then reloaded and the full state rechecked. |
| cg_load_before_rst / cg_top_load_before_rst | A load on the edge right before rst (rows 0, 13, 31; in top, a same-cycle row and column load: (0,0), (17,5), (31,7)) is written, and in top S is then cleared by rst. All rows and columns streamed back to back up to the rst edge. A load on the first edge after rst is kept (top: S = that value, the other columns 0). |
| cg_single_row_write / cg_top_single_write | Each of the 32 rows is written in turn, shuffled, with a new value in every column, and the whole array is read back after each write: every other row is unchanged. In top, each of the 8 sidecar columns is also written (new slot rows, values and S). |
| cg_enable_glitch / cg_top_enable_glitch | load_en pulses (top: w_load_en, s_load_en, rst, and rst+s_load_en) that start and end inside one clock phase, high and low, for every row and column, with junk data. No edge sees them, so nothing may change; in top, rst must not clear S. |
| cg_back_to_back_loads / cg_top_back_to_back | Every row loaded on consecutive edges with the patterns random, max, checker, complement and zero, in both orders (top: rows and columns in the same cycles, 3 states, both orders). Then every row and column written twice on consecutive edges (junk, then final): the last write wins. |
| cg_write_edge_whitebox (core only) | White-box check of the header write edge: the internal row `g_row[r].row` must still be old right after the load edge a and new after a+1 (dcim_core, dcim_8bit: registered port). For mac_baseline it must be new right after edge a (header: written at its load_en edge). |

## Mutation check (copies in /tmp, rtl/ untouched; random and real limited to 500 cases; logs `tests/sim_build/mut_*.log`)
| Mutant | Config | Result |
|---|---|---|
| s_norst: S gate en = ld_j (rst dropped, S never resets) | top FF P0 | CAUGHT, 4 tests: powerup_reset_y (y = X after power-up rst), reset_mid_compute (rst at k+1: expected S=0, got the old S), cg_top_rst_idle, cg_top_load_before_rst |
| s_en1: S gate en stuck at 1 (S follows s_load_shift on every edge) | top FF P0 | CAUGHT, 17 of 18 tests (all except powerup_reset_y). First fail: corners `empty_slots` case 0 (12/26 fail) |
| icg_and: icg.v without its latch, gclk = clk & en | dcim_core FF | CAUGHT only by cg_write_edge_whitebox (row 26 already new right after load edge a: got 0xe352e00c, old 0x98170f8e). All 17 port-level tests PASS (see the note below). |
| icg_and | mac_baseline | CAUGHT by load_while_busy_ignored and cg_enable_glitch (high-phase pulses: all 32 rows overwritten with junk) |
| icg_and | top FF P0 | CAUGHT by loads_while_busy_ignored and cg_top_enable_glitch (row 0 readback wrong after high-phase pulses) |
| row_next_dcim: weight row i gated by row i+1's write (mod 32) | dcim_core FF | CAUGHT, all 17 tests. First fail: corners `alt_checker` case 18 (5/34 fail) |
| row_next_mac: register-file row i gated by i+1 | mac_baseline | CAUGHT, all 16 tests. First fail: corners `alt_checker` case 18 |
| col_next_side: slot column j gated by j+1 | top FF P0 | CAUGHT, 17 of 18 tests (all except powerup_reset_y). First fail: corners `dup_rows` case 2 (12/26 fail) |

Note on icg_and. In zero-delay RTL simulation a latchless gate is a functional problem only when its enable can rise while clk is high. In mac_baseline, the sidecar and the S gates the enable is combinational from the ports. A port change in the high phase therefore makes a gclk edge in the middle of the cycle, and the flops write data that no edge sampled, which the glitch tests catch. In dcim_core the enable `sel` is registered on clk and changes only right after the rising edge. In zero-delay simulation the mutant then writes the row one delta after edge a with the same wd_q value (one edge early) and again at a+1. Nothing reads a row in that half cycle: loads are blocked while busy, and start can come no earlier than a+1. So the ports cannot tell the mutant apart, and only the white-box check of the header write edge sees it. In silicon the same latchless gate would make a runt or early gclk pulse right after every clk edge, racing wd_q (a hold or glitch failure). RTL simulation has no delays, so it cannot show that; it is a matter for STA clock-gating checks on the real dlclkp cell.

## VCD (regenerated, CLK_GATE=1, first 100 real-layer cases, 100/100 equal to golden)
| File | Size | Gated-clock nets | gclk rising edges |
|---|---|---|---|
| `results/vcd/mac_baseline.vcd` (578,050 ns) | 6.2 MB | 32 (`g_row[i].g_cg.gclk` = `u_icg.gclk`) | 100 per row, 3,200 total (one per row write; clk 28,903) |
| `results/vcd/sidecarcim_top_ff_p0.vcd` (74,050 ns) | 5.6 MB | 48: 32 `u_dense.g_row[i].g_cg`, 8 `u_side.g_col[j].g_cg`, 8 `g_sh[j].g_cg` | 100 per row/slot column, 101 per S column (+1 power-up rst edge), 4,808 total (clk 3,703) |
| `results/vcd/sidecarcim_top_ff_p1.vcd` (74,050 ns) | 5.6 MB | 48 (same) | same |

There are no dcim_core FF or dcim_8bit FF VCD targets: `vcd` and `vcd8` dump the latch builds, which have no gate. The flow uses the RTL VCDs only for port stimulus (`flow/gl_stim.py`), so the gated-clock activity for power must come from the gate-level simulation. `results/vcd/dcim_core.vcd`, `dcim_8bit.vcd` and `sidecarcim_top.vcd` (latch) were not regenerated.

## Runtime
Four streams in parallel, alongside a LibreLane dcim_core_ff run (load average about 20): 2,085 s wall. dcim8_ff 2,085 s · dcim_ff 1,137 s · top_ff 1,173 s · top_p1_ff 1,141 s · mac 195 s · latch spots 71 / 170 / 78 / 74 s · VCDs 7 / 7 / 5 s. CLK_GATE=0 directed check: 169 s. Mutants: 785 s (8 runs, concurrent with the streams). Logs: `tests/sim_build/cg_<target>.log`, `cg0_*.log`, `mut_*.log`.

---

# W8A4 / W6A4 sign-off (2026-10-13)
RTL `rtl/dcim_core.v` @ 0964777 (`git diff f1cb2ba 0964777`, f1cb2ba = clock-gating sign-off: comment lines only), `rtl/icg.v`. Reference `python/golden.py` `dcim_dot(w, x, wbits, 4)`. Vectors @ 5259e17: `python/vectors/w8a4_{corners,random,real_layer}.npz`, `w6a4_*.npz`; stored y == golden in all six (checked by `load_set` before every run). cocotb 2.1.0, Icarus 12.0, Python 3.12.3, 20 ns testbench clock. Build: dcim_core with `-Pdcim_core.WBITS=8|6 -Pdcim_core.ABITS=4 -Pdcim_core.USE_LATCH=0 -Pdcim_core.CLK_GATE=1` (primary build), `rtl/icg.v` in the source list. Contract: the dcim_core.v header port table (W8A4 load_row 64 b, y 8×17 = 136 b; W6A4 load_row 48 b, y 8×15 = 120 b; x_in 128 b; start to valid 4 edges).

## Verdict
dcim_core passes every test at both points. No failing case.

## Results
| Test | W8A4 (WBITS=8, ABITS=4) | W6A4 (WBITS=6, ABITS=4) |
|---|---|---|
| corners (natural row order) | 38/38 PASS | 36/36 PASS |
| random (shuffled rows, seed 1234) | 10,000/10,000 PASS | 10,000/10,000 PASS |
| real_layer (reverse row order) | 4,096/4,096 PASS | 4,096/4,096 PASS |
| protocol + directed (8: latency_and_hold, back_to_back, start_with_load_ignored, load_while_busy_ignored, start_while_busy_ignored, reset_mid_compute, full_scale, partial_reload) | 8/8 PASS | 8/8 PASS |
| clock-gating directed (6: cg_rst_idle, cg_load_before_rst, cg_single_row_write, cg_enable_glitch, cg_back_to_back_loads, cg_write_edge_whitebox) | 6/6 PASS | 6/6 PASS |

Commands `make -C tests dcim_w8a4_ff` and `dcim_w6a4_ff`: rc=0, TESTS=18 PASS=17 SKIP=1 each (the skip is the VCD-only test). 28,268 vector cases in total (14,134 per point). busy/valid checked after every edge of every dot product (start to valid = 4 edges), and the xbit bit-plane tap on every dot product. Port widths (load_row, x_in, y) and the DUT parameters WBITS/ABITS are asserted in `setup()`. The protocol tests take their cases from `w8a4_random` / `w6a4_random` (full-width weights, 0..255 / 0..63), and the clock-gating tests draw random rows at WBITS, so the upper weight bits are exercised there too.

## Testbench change
`tests/core_tb.py` reads WBITS/ABITS from `DCIM_WBITS`/`DCIM_ABITS` (else the spec dense widths, as before) and the vector family from `DCIM_VEC_PREFIX` (default ""), which also selects the protocol-test cases. `tests/Makefile` passes the same numbers to `-P` and to the env (`wpar`/`wenv`), and `setup()` checks the DUT parameters against them when the env is set. `test_dcim_core.py` passes the prefix to the vector tests. If the env is not set, nothing changes. Spot check after the change: dcim_ff 34/34 + 200/200 + 200/200 + 14/14, dcim8_ff 42/42 + 200/200 + 200/200 + 14/14, mac 34/34 + 200/200 + 200/200 + 13/13, all rc=0. The four new targets are also in `make all`.

## Mutation check (copy in /tmp/vfy/mut/drop_wtop, rtl/ untouched; diff and source in `tests/sim_build/mut/` (git-ignored); random and real limited to 500 cases)
| Mutant | Config | Result |
|---|---|---|
| drop_wtop: top weight bit-column (b = WBITS-1) left out of the shift-add (`if (b != WBITS-1) part = part + (pc << b)`) | W8A4 (bit 7 dropped) | CAUGHT, 17 of 17 tests. Passing cases: corners 11/38, random 0/500, real_layer 0/500. First fail: corners `all_max`, expected 122,400 per column, got 60,960 (= 32·127·15) |
| drop_wtop (same copy) | W6A4 (bit 5 dropped) | CAUGHT, 17 of 17 tests. Passing cases: corners 9/36, random 0/500, real_layer 0/500. First fail: corners `all_max`, expected 30,240, got 14,880 (= 32·31·15) |

## VCD (CLK_GATE=1, first 100 real-layer cases, natural row order, 100/100 equal to golden)
| File | Size | Sim time | Gated-clock nets | gclk rising edges |
|---|---|---|---|---|
| `results/vcd/dcim_w8a4_ff.vcd` (`make -C tests vcd_w8a4_ff`) | 7,845,682 B (7.8 MB) | 74,050 ns | 32 (`g_row[i].g_cg.gclk`) | 100 per row, 3,200 total (one per row write; clk 3,702) |
| `results/vcd/dcim_w6a4_ff.vcd` (`make -C tests vcd_w6a4_ff`) | 6,035,476 B (6.0 MB) | 74,050 ns | 32 | 100 per row, 3,200 total (clk 3,702) |

Same format as the other FF VCDs: `tests/vcd_dump.v` dumps every signal of the top (dcim_core) from t = 0, timescale 1 ps, 20 ns per cycle, one full 32-row load plus one dot product per case. The other VCDs in `results/vcd/` were not touched.

## Runtime
Four streams in parallel (two targets, two mutants), then the two VCD targets: 1,139 s wall. dcim_w8a4_ff 1,119 s · dcim_w6a4_ff 862 s · mutants 119 / 89 s · VCDs 11 / 9 s. About 12 to 20 cases/s. Spot check of the old targets: 110 s. Logs: `tests/sim_build/w_<target>.log`, `mut_dropw_w8a4.log`, `mut_dropw_w6a4.log`, `wreg_*.log`.

---

# PIPE_MERGE sign-off (2026-10-13)
RTL `rtl/sidecarcim_top.v` @ 507b043 (parameter `PIPE_MERGE`; header sections PARAMETERS, "PROTOCOL, PIPE_MERGE=1", FLOW NOTE, STORAGE). `rtl/dcim_core.v`, `rtl/sidecar.v` and `rtl/icg.v` are unchanged. Reference `python/golden.py` `sidecarcim_dot`. Vectors `python/vectors/sidecar_{corners,random,real_layer}.npz`; stored y == golden (checked by `load_set` before every run). cocotb 2.1.0, Icarus 12.0, 20 ns testbench clock. New build: K=2, PARALLEL=0, USE_LATCH=0, CLK_GATE=1, PIPE_MERGE=1, the configuration of the flow run `sidecarcim_top_ff_pipe`. The header specifies:
- start to valid = ABITS+1 = 5 edges;
- one dot product per 5 cycles back to back, with valid=1 overlapping busy=1 of the next dot;
- valid and y equal the PIPE_MERGE=0 valid and y one edge later;
- y holds while cv=0;
- rst clears y and valid.

## Verdict
The PIPE_MERGE=1 build passes every test, with no failing case. The PIPE_MERGE=0 regression (top_ff, top_p1_ff) also passes every test. The mutant that skips the pipeline register, the one this change can break, is caught by 22 of 23 tests.

## Results (all vectors)
| Test | top_ff_pipe (PIPE_MERGE=1) | top_ff (P0, regression) | top_p1_ff (P0, PARALLEL=1, regression) |
|---|---|---|---|
| corners (natural row order) | 26/26 PASS | 26/26 PASS | 26/26 PASS |
| random (shuffled rows) | 10,000/10,000 PASS | 10,000/10,000 PASS | 10,000/10,000 PASS |
| real_layer (reverse row order) | 4,096/4,096 PASS | 4,096/4,096 PASS | 4,096/4,096 PASS |
| vb_extremes | 33/33 PASS | 33/33 PASS | 33/33 PASS |
| protocol (9, adapted to LAT = ABITS + PIPE_MERGE) | 9/9 PASS | 9/9 PASS | 9/9 PASS |
| clock-gating directed (5) | 5/5 PASS | 5/5 PASS | 5/5 PASS |
| new pipeline directed (5, every edge vs a model) | 5/5 PASS | 5/5 PASS | 5/5 PASS |

Commands: `make -C tests top_ff_pipe`, `top_ff` and `top_p1_ff`. Each returned rc=0 with TESTS=24 PASS=23 SKIP=1; the skip is the VCD-only test. Before this change the count was 19/18/1; the 5 new tests make the difference.

busy and valid are checked after every edge of every dot product. In the vector tests that means:
- after k+1, k+2, k+3: (1,0);
- after k+4: (0,0);
- after k+5: (0,1).

The DUT parameter PIPE_MERGE is checked against the testbench latency in `setup()` on every test of every top target.

Spot runs of the other PIPE_MERGE=1 storage options use 500 random and 500 real-layer cases, with everything else run in full (build dirs `sim_build/pipe_spot_*`):
- CLK_GATE=0 flip-flop build (y register on a hold mux): 23/23 PASS.
- Latch build: 23/23 PASS.

The PIPE_MERGE=0 latch targets top_p0 and top_p1 were also spot-run with the new tests, at 30 random and 30 real-layer cases: 23/23 PASS each.

## Testbench change
`tests/top_tb.py`:
- `LAT = ABITS + PIPE`. `PIPE` comes from the env `TOP_PIPE_MERGE`, default 0, so the existing targets are unchanged.
- `bv_expect(c)` gives the header's busy/valid after edge k+c: (1,0) for c < ABITS, then (0,0) until LAT, then (0,1), or (1,1) when the next start is accepted at k+LAT.

Adapted tests. Each is identical to the old version when PIPE=0.

| Test | Change |
|---|---|
| `wait_valid` | Checks every edge up to LAT. |
| `start_ignored_during_loads` | After a load in DONE, PIPE=1 expects valid=1 with the finished y, then valid=0 one edge later while y holds. |
| `loads_while_busy_ignored` | Drives junk loads on exactly the busy edges k+1..k+ABITS. |
| `start_while_busy_ignored` | Holds start through k+ABITS. |
| `back_to_back` | With PIPE=1, the valid edge is also the next start, so busy=1 and valid=1. |
| `reset_mid_compute` | Resets at the busy edges k+1..k+ABITS-1. The pipeline-stage edges are covered by the new test `pipe_rst_mid_pipeline`. |

`tests/Makefile`: new targets `top_ff_pipe` and `vcd_top_ff_pipe`. Both pass `-Psidecarcim_top.PIPE_MERGE=1` and `TOP_PIPE_MERGE=1`, and both are in `make all`. The existing recipes are unchanged.

New directed tests (`test_sidecarcim_top.py`, run on every top build) use `PipeModel`, a cycle-level model of the header protocol with two parts:
- The P0 FSM: LOAD, BUSY and DONE; cv; loads and start ignored while busy; a load or start in DONE clears cv; rst sets S=0 and keeps the weights and slots.
- The PIPE_MERGE=1 output register: valid <= cv; y <= result if cv, else y holds; rst clears both.

On every edge the tests check busy, valid and y. With PIPE=1, y is checked on every edge, including while valid=0. x_in is random junk on every edge that does not accept a start. With PIPE=0 the same tests check the same model without the register, which cross-checks the model against the established protocol.

| Test | What it checks | PIPE_MERGE=1 |
|---|---|---|
| pipe_b2b_overlap | 18 dots back to back, first with start held high, then with start pulsed only on the accepting edges. Expected: one valid pulse per dot, exactly 5 edges apart; latency 5; valid=1 with busy=1 of the next dot; y holds the last result between pulses. | 18 dots in 90 edges in each mode, 17 valid&busy cycles each (P0: 0) |
| pipe_load_in_done | Loads in DONE of four kinds: sidecar column with new S, dense row, both, and both + start. Each lands on the edge valid rises (k+5) or 1..3 edges later. Expected: after the load edge, valid=1 and y = the finished result (old S and accumulators); one edge later, valid=0 and y keeps the result. Then a dot on the new state. | 16/16 cases |
| pipe_rst_mid_pipeline | rst at every edge k+1..k+6 of one dot: the busy edges, the merge-stage edge k+4, the valid edge k+5 and idle DONE at k+6. Also rst at the overlap edges k+4..k+7 of back-to-back dots. Expected after rst: (0,0), y=0, and no stale valid for 10 idle edges. Then a dot with S=0, all columns reloaded, and a dot again. | 10 rst points |
| pipe_start_on_valid_edge | A second start pulse at k+1..k+8 after a single dot, with a different x per dot. Expected: pulses at k+1..k+4 are ignored (k+4 shows (0,0) but has busy=1 before it); k+5, the exact edge valid rises, is accepted with (busy,valid) = (1,1); k+6..k+8 are accepted in DONE. | 8 start points |
| pipe_protocol_fuzz | 3,000 random edges in every state: start 60 %; dense and sidecar loads 10 % each, with new values and extreme slot values; rst 0.5 %, never with a load. | 496 dots, 484 valid pulses, 349 valid&busy cycles, 14 rst |

## Mutation check
Setup: copies in /tmp/vfy/mut, rtl/ untouched. Diffs and sources are in `tests/sim_build/mut/pipe_*.diff` and `top_pipe_*.v` (git-ignored). PIPE_MERGE=1 build; random and real-layer limited to 500 cases.

| Mutant | Result |
|---|---|
| pipe_skip: output register bypassed (`assign y = ym; assign valid = cv;`), so the result comes 1 edge early | CAUGHT by 22 of 23 tests (all except powerup_reset_y). First fail in every vector test: `edge k+4: busy,valid=(0, 1) expected (0, 0)` |
| pipe_yen1: y-register clock gate always on (`.en(1'b1)`), so y follows the merge on every edge instead of holding while cv=0 | CAUGHT only by the 5 new pipe_* tests, e.g. `b2b held step 2: y=[115, 30768, ...]` while the next dot is busy. All 18 vector, protocol and clock-gating tests PASS because they read y only while valid=1. The "y holds" part of the header therefore depends on the new model tests. |

## VCD
Command `make -C tests vcd_top_ff_pipe`: CLK_GATE=1, first 100 real-layer cases, natural row order, 100/100 equal to golden.

| File | Size | Sim time | Gated-clock nets | Rising edges |
|---|---|---|---|---|
| `results/vcd/sidecarcim_top_ff_pipe.vcd` | 5,506,279 B (5.5 MB) | 76,050 ns | 49: 32 dense rows, 8 slot columns, 8 S columns, 1 y register (`g_pipe.g_cg.gclk`) | clk 3,803 (P0 VCD 3,703, one extra cycle per case); busy 100; valid 100; y-register gclk 200; all gates 5,008 |

Same stimulus and format as `sidecarcim_top_ff_p0.vcd`: `tests/vcd_dump.v` dumps every signal of sidecarcim_top from t = 0, timescale 1 ps, 20 ns per cycle, one full load and one dot per case.

The y-register gate opens on every edge with cv=1. In this stimulus that is 2 edges per dot: the result edge and the following load edge, which rewrites the same value. In back-to-back use it opens once per dot, as the header says. The gate-level stimulus and power windows must allow for valid one edge later. No other VCD was touched.

## Runtime
1,326 s wall. Three full targets and the two mutants (run one after the other) ran in parallel, then the VCD. A Python study (about 7 cores) and a LibreLane run were active at the same time, with load average about 20.

| Run | Time |
|---|---|
| top_ff_pipe | 1,313 s |
| top_ff | 1,309 s |
| top_p1_ff | 1,292 s |
| mutants | 17 s + 155 s |
| VCD | 13 s |
| spot runs (CLK_GATE=0, latch, top_p0/p1, smoke) | about 7 min more |

Throughput was about 11 cases/s. Logs: `tests/sim_build/pipe_<target>.log`, `mut_pipe_skip.log`, `mut_pipe_yen1.log`, `pipe_spot_*.log`, `smoke_*.log`; run table `tests/sim_build/pipe_runs.txt`.

# PIPE_MERGE + SBITS=3 sign-off (2026-10-14)
RTL `rtl/sidecarcim_top.v` @ 5095d82 (md5 9a28eb6a…; parameter `SBITS`, header sections PARAMETERS, DERIVED WIDTHS, PORTS, FLOW NOTE, STORAGE). Reference `python/golden.py` `sidecarcim_dot(..., sbits=3)`, `merged_width(..., sbits=3)` = 22. Vectors `python/vectors/sidecar_s3_{corners,random,real_layer}.npz` (26 / 10,000 / 4,096); stored y == golden with sbits=3 (checked by `load_set` before every run). cocotb 2.1.0, Icarus 12.0, 20 ns testbench clock. Build: K=2, PARALLEL=0, USE_LATCH=0, CLK_GATE=1, PIPE_MERGE=1, SBITS=3 = the final build, flow config `sidecarcim_top_ff_pipe_s3`. Contract: S 3 bits (0..7, every code legal), s_load_shift 3 bits, YTW 22, y 176 bits; protocol identical to PIPE_MERGE=1 (start to valid 5 edges, one dot per 5 cycles).

## Verdict
The SBITS=3 build passes every test with no failing case. The mutant that truncates the S register to 2 bits, the one this change can break, is caught by 22 of 23 tests. The SBITS=4 builds top_ff_pipe and top_ff are unchanged (500-case regression, all PASS, same directed counts as their full sign-offs).

## Results
| Test | top_ff_pipe_s3 (all vectors) | top_ff_pipe (SBITS=4, 500-case regression) | top_ff (SBITS=4, P0, 500-case regression) |
|---|---|---|---|
| corners (natural row order) | 26/26 PASS | 26/26 PASS | 26/26 PASS |
| random (shuffled rows) | 10,000/10,000 PASS | 500/500 PASS | 500/500 PASS |
| real_layer (reverse row order) | 4,096/4,096 PASS | 500/500 PASS | 500/500 PASS |
| vb_extremes | 32/32 PASS (SMAX 7, y max 983,010, y min -61,440) | 33/33 PASS (SMAX 11) | 33/33 PASS |
| protocol (9) | 9/9 PASS | 9/9 PASS | 9/9 PASS |
| clock-gating directed (5) | 5/5 PASS | 5/5 PASS | 5/5 PASS |
| pipeline directed (5, every edge vs model) | 5/5 PASS | 5/5 PASS | 5/5 PASS |
| cocotb total | TESTS=24 PASS=23 SKIP=1, rc=0 | 24/23/1, rc=0 | 24/23/1, rc=0 |

Pipeline directed counts at SBITS=3 equal the SBITS=4 PIPE_MERGE=1 sign-off: b2b 18 dots every 5 edges, 17 valid&busy cycles (held and pulsed); 16 load-in-DONE cases; 10 rst points; second start at k+1..k+8; fuzz 3,000 edges, 496 starts, 484 valid pulses, 349 valid&busy cycles, 14 rst. setup() checks on every test: y width = 8 × 22, s_load_shift width = 3, DUT SBITS = 3, DUT PIPE_MERGE = 1.

vb_extremes at SMAX=7 includes the S=7 + dense-max corners: y_max = 7200·2^7 + 2·2047·15 = 983,010 and dense_max_side_min = 921,600 − 61,440 = 860,160 (closed form from spec widths and golden agree). One S-sweep case covers S 0..7 across the 8 columns, so 32 cases instead of 33 (SMAX 11 needs two sweeps).

## Testbench change
`tests/top_tb.py` (existing targets get the same values as before):
- `TOP_SBITS` env (default unset = sbits None): `SB` goes to golden as `sbits`; `SBW` = SB or clog2(VB) (= 4); `YTW = golden.merged_width(..., sbits=SB)`; `SMAX = golden.s_max(VB, SB)` (11 by default, 7 at SBITS=3). `gold()` and `load_set()` pass `sbits=SB`.
- `TOP_VEC_PREFIX` env (default `sidecar_`): every vector file and protocol-test case comes from `<prefix>{corners,random,real_layer}.npz`.
- Uses of VB as the S range changed to SMAX+1: junk S in `loads_while_busy_ignored`, the vb_extremes S sweep and `mixed_S_down`. Identical at SBITS=4 (SMAX+1 = VB).
- setup(): new checks `len(s_load_shift) == SBW` and DUT `SBITS == SBW`.

`tests/Makefile`: new targets `top_ff_pipe_s3` and `vcd_top_ff_pipe_s3` (`-Psidecarcim_top.SBITS=3` with `TOP_SBITS=3 TOP_VEC_PREFIX=sidecar_s3_`, otherwise the top_ff_pipe parameters), both in `make all`. Existing recipes unchanged.

## Mutation check
Copy in /tmp/vfy/mut_s2, rtl/ untouched; diff and source in `tests/sim_build/mut/s3_mut_s2.diff` and `top_s3_mut_s2.v` (git-ignored). Random and real-layer limited to 500 cases.

| Mutant | Result |
|---|---|
| mut_s2: S register truncated to 2 bits (`s_r <= {1'b0, s_load_shift[SBW-2:0]}` in both the gated and the hold-mux branch), so S 4..7 loads as 0..3 | CAUGHT by 22 of 23 tests (all except powerup_reset_y). Passing cases: corners 9/26, random 3/500, real_layer 0/500 (real-layer S is 3..7). First fail: `sidecar_s3_corners [empty_slots] case 0`, S = [4, 1, 5, 4, 4, 3, 6, 4], expected y[0] 31,936, got 1,996 (= 31,936 >> 4). |

## VCD
Command `make -C tests vcd_top_ff_pipe_s3`: CLK_GATE=1, first 100 sidecar_s3 real-layer cases, natural row order, 100/100 equal to golden.

| File | Size | Sim time | Gated-clock nets | Rising edges |
|---|---|---|---|---|
| `results/vcd/sidecarcim_top_ff_pipe_s3.vcd` | 5,469,435 B (5.5 MB) | 76,050 ns | 49 (32 dense rows, 8 slot columns, 8 S columns, 1 y register) | clk 3,802 0-to-1 transitions (same count on sidecarcim_top_ff_pipe.vcd); busy 100; valid 100; y-register gclk 200; all gates 5,008 |

Same stimulus and format as `sidecarcim_top_ff_pipe.vcd`; y is 176 bits and each `s_r` is 3 bits. The gate-level stimulus for this config must use SBW = 3 and YTW = 22.

## Runtime
556 s wall for everything: five runs in parallel on 5 cores, nothing else running.

| Run | Time |
|---|---|
| top_ff_pipe_s3 (full) | 556 s (random 384 s, real 151 s, about 26 cases/s) |
| vcd_top_ff_pipe_s3 | 7 s |
| mutant mut_s2 | 49 s |
| top_ff_pipe 500-case regression | 68 s |
| top_ff 500-case regression | 67 s |

Logs: `tests/sim_build/s3_full.log`, `s3_vcd.log`, `s3_mut_s2.log`, `s3_reg_pipe.log`, `s3_reg_ff.log`; run table `tests/sim_build/s3_times.txt`. The regressions used build dirs `sim_build/reg500_top_ff_pipe` and `reg500_top_ff`, so the full-run results.xml of top_ff_pipe and top_ff are untouched.

---

# W7A4 / W4A8 sign-off (2026-10-15)
RTL `rtl/dcim_core.v` (md5 95dec26a…, unchanged since 0964777 = the W8A4/W6A4 sign-off) and `rtl/icg.v` (md5 5f543835…), HEAD 39ca3b2. Reference `python/golden.py` `dcim_dot(w, x, wbits, abits)`. Vectors @ 39ca3b2: `python/vectors/w7a4_{corners,random,real_layer}.npz` (37 / 10,000 / 4,096) and `w4a8_*.npz` (38 / 10,000 / 4,096); stored y == golden in all six (checked by `load_set` before every run). cocotb 2.1.0, Icarus 12.0, Python 3.12.3, 20 ns testbench clock. Build: dcim_core with `-Pdcim_core.WBITS=7 -Pdcim_core.ABITS=4` / `WBITS=4 ABITS=8`, `USE_LATCH=0 CLK_GATE=1` (primary build), `rtl/icg.v` in the source list. Contract: the dcim_core.v header (all widths follow WBITS/ABITS): W7A4 load_row 56 b, x_in 128 b, y 8×16 = 128 b, start to valid 4 edges; W4A8 load_row 32 b, x_in 256 b, y 8×17 = 136 b, start to valid 8 edges, 9 cycles per dot back to back.

## Verdict
dcim_core passes every test at both points. No failing case. No RTL problem found.

## Elaboration
| Check | W7A4 | W4A8 |
|---|---|---|
| `verilator --lint-only -Wall -GUSE_LATCH=0 -GCLK_GATE=1 -GWBITS=… -GABITS=… rtl/dcim_core.v rtl/icg.v` (Verilator 5.020) | rc=0, no warnings | rc=0, no warnings |
| `iverilog -g2005 -Wall -s dcim_core -P… rtl/dcim_core.v rtl/icg.v` | rc=0, no warnings | rc=0, no warnings |

## Results
| Test | W7A4 (WBITS=7, ABITS=4) | W4A8 (WBITS=4, ABITS=8) |
|---|---|---|
| corners (natural row order) | 37/37 PASS | 38/38 PASS |
| random (shuffled rows, seed 1234) | 10,000/10,000 PASS | 10,000/10,000 PASS |
| real_layer (reverse row order) | 4,096/4,096 PASS | 4,096/4,096 PASS |
| protocol + directed (8: latency_and_hold, back_to_back, start_with_load_ignored, load_while_busy_ignored, start_while_busy_ignored, reset_mid_compute, full_scale, partial_reload) | 8/8 PASS | 8/8 PASS |
| clock-gating directed (6: cg_rst_idle, cg_load_before_rst, cg_single_row_write, cg_enable_glitch, cg_back_to_back_loads, cg_write_edge_whitebox) | 6/6 PASS | 6/6 PASS |

Commands `make -C tests dcim_w7a4_ff` and `dcim_w4a8_ff`: rc=0, TESTS=18 PASS=17 SKIP=1 each (the skip is the VCD-only test). 28,267 vector cases in total (14,133 W7A4 + 14,134 W4A8). The latency is checked exactly at each point. busy/valid are checked after every edge of every dot product: (1,0) after k+1..k+LAT-1 and (0,1) after k+LAT, with LAT = ABITS = 4 (W7A4) and 8 (W4A8). EDGE_CHECK_MAX is 8, so the W4A8 vector runs are also checked edge by edge. back_to_back checks that the next start is accepted at k+LAT+1 (5 / 9 cycles per dot). The xbit tap is checked on every dot product for all 4 / 8 bit-planes. reset_mid_compute resets at k+1, k+2, k+3 (W7A4) and k+1, k+4, k+7 (W4A8). Port widths (load_row, x_in, y) and the DUT parameters WBITS/ABITS are asserted in `setup()` on every test. The protocol tests take their cases from `w7a4_random` / `w4a8_random` (weights 0..127 / x 0..255). full_scale uses all-max w and x (y = 60,960 / 122,400).

## Testbench change
`tests/Makefile`: new targets `dcim_w7a4_ff`, `dcim_w4a8_ff`, `vcd_w7a4_ff` and `vcd_w4a8_ff`. They use the existing `wpar`/`wenv` mechanism (`$(call wpar,7,4)` etc., `DCIM_VEC_PREFIX=w7a4_` / `w4a8_`) and are all in `make all`. The help text is updated; existing recipes are unchanged. `tests/core_tb.py`: comment only (lists the new prefixes). No test logic changed, because core_tb already derives YW, LAT, x packing and the xbit planes from DCIM_WBITS/DCIM_ABITS.

## Mutation check (copies in /tmp/vfy7/mut, rtl/ untouched; diff and source in `tests/sim_build/mut/w7w4_*` (git-ignored); random and real limited to 500 cases)
| Mutant | Config | Result |
|---|---|---|
| drop_wtop: top weight bit-column (b = WBITS-1) left out of the shift-add (`if (b != WBITS-1) part = part + (pc << b)`) | W7A4 (bit 6 dropped) | CAUGHT, 17 of 17 tests. Passing cases: corners 11/37, random 0/500, real_layer 0/500. First fail: corners `all_max`, expected 60,960 per column, got 30,240 (= 32·63·15) |
| drop_xtop: top input bit-plane (a = ABITS-1, i.e. the first compute edge, `cnt == CNT0`) left out of the AND array (`one[0] = w & x & (cnt != CNT0)`); xbit tap unchanged | W4A8 (bit 7 dropped) | CAUGHT, 11 of 17 tests: corners (14/38 cases pass), random (0/500 pass), real_layer (0/500 pass) and all 8 protocol and directed tests. First fail: corners `all_max`, expected 122,400, got 60,960 (= 32·15·127). The 6 clock-gating tests pass, as expected: they read storage back with one-hot x = 1, which uses only bit-plane 0 |

## VCD (CLK_GATE=1, first 100 real-layer cases, natural row order, 100/100 equal to golden)
| File | Size | Sim time | Gated-clock nets | Rising edges |
|---|---|---|---|---|
| `results/vcd/dcim_w7a4_ff.vcd` (`make -C tests vcd_w7a4_ff`) | 6,938,836 B (6.9 MB) | 74,050 ns | 32 (`g_row[i].g_cg.gclk`) | gclk 100 per row, 3,200 total (one per row write); clk 3,702; busy 100; valid 100 |
| `results/vcd/dcim_w4a8_ff.vcd` (`make -C tests vcd_w4a8_ff`) | 4,791,393 B (4.8 MB) | 82,050 ns | 32 | gclk 100 per row, 3,200 total; clk 4,102 (8-cycle compute: 4 more cycles per case); busy 100; valid 100 |

Same format as the other FF VCDs: `tests/vcd_dump.v` dumps every signal of the top (dcim_core) from t = 0, timescale 1 ps, 20 ns per cycle, one full 32-row load plus one dot product per case. The gate-level stimulus for W4A8 must allow 8 compute cycles and a 256-bit x_in. No other VCD was touched.

## Runtime
2,159 s wall in total. The two full targets and the two mutants ran in parallel, then the two VCD targets. The machine was shared: two wholemodel.py GPT-2 runs (about 7 cores) and a LibreLane run were active, with load average about 30 on 16 cores.

| Run | Time |
|---|---|
| dcim_w7a4_ff | 2,142 s (random 1,683 s, real 418 s) |
| dcim_w4a8_ff | 1,617 s (random 1,146 s, real 406 s) |
| mutants | 304 s / 301 s |
| VCDs | 10 s / 7 s |

Throughput was about 6 to 10 cases/s. Logs: `tests/sim_build/w_dcim_w7a4_ff.log`, `w_dcim_w4a8_ff.log`, `w_vcd_w7a4_ff.log`, `w_vcd_w4a8_ff.log`, `mut_dropw_w7a4.log`, `mut_dropx_w4a8.log`; run table `tests/sim_build/w7w4_times.txt`.

The "DENSE COMPARISON POINTS" table in the dcim_core.v header now also lists:
- W7A4: load_row 56, y 128, YW 16, max 60,960, 1,792 weight FFs.
- W4A8: x_in 256, y 136, YW 17, max 122,400, start to valid 8 edges, 9 cycles back to back.
