# Phase 4 — RTL synthesis and area comparison (45 nm substitute for 28 nm)

**English** | [中文](README_zh.md)

## 0. Consistency check: were the two runs the same Verilog?

| Check | baseline | ExpMul | Result |
|---|---|---|---|
| Top-level wrapper | `fa_lane_b_top` (`.VARIANT(0)`) | `fa_lane_e_top` (`.VARIANT(1)`) | different |
| Cells after Yosys elaboration | 1 242 | 604 | different |
| Instances in `6_final.v` | **18 776** | **7 436** | different |
| `FA_X1` cells in `6_final.v` | **2 142** | **43** | different |
| Gate-level VCD size | 33.8 MB | 10.2 MB | different |
| GDS | **16.8 MB** | **7.2 MB** | both present |

Note: the first attempt used the configurations `fa_lane_top` and `fa_lane_b_top`, whose
`DESIGN_NAME` overlapped. ORFS reused the synthesised database and both sides ended up with
18 776 instances — **that run did compare a netlist with itself**. After switching to two
independent top-level modules and clearing `objects/results`, the fingerprints above were obtained.
Both designs complete down to `6_final.gds` (KLayout), at
`$HOME/orfs-src/flow/results/nangate45/fa_lane_{b,e}_top/base/6_final.gds`.

## 1. Toolchain and substitution

| Paper | This reproduction | Difference |
|---|---|---|
| Catapult HLS → Verilog | hand-written synthesizable Verilog (`rtl/`), C++ model as golden reference | same algorithm, different front end |
| 28 nm commercial library | **nangate45** (45 nm, open Nangate OpenCellLibrary, 1.1 V) | no open 28 nm PDK exists; areas scale by (45/28)² ≈ 2.6, so **only relative savings are claimed** |
| Cadence implementation + PowerPro | ORFS: Yosys 0.68 + OpenROAD P&R + `6_report` / gate-level VCD power | see §5 |

Commands: `scripts/synth_units.sh` (area), `scripts/setup_orfs_*.sh` + `run_orfs.sh` (P&R).

## 2. RTL contents

| File | Contents | Verification |
|---|---|---|
| `rtl/fp32_funcs.vh` | `fmul32` / `fadd32`: IEEE-754 binary32 multiply/add, RNE, FTZ | **bit-exact against NumPy on 4 000 random vectors** |
| `rtl/fp32_mul.v`, `rtl/fp32_add.v` | module wrappers around those functions | same |
| `rtl/expmul.v` | Algorithm 3: Q6.10 clip → shift-and-add → exponent subtraction (MODE=0) / mantissa interpolation (MODE=1) | 4 999 / 4 996 of 5 000 bit-exact (remainder are Q6.10 half-way ties) |
| `rtl/exp_pwl.v` | baseline exponential: `x·log2e` → Q6.10 → 8-segment PWL → exponent restore; includes `rcp_pwl` | maximum relative error **0.52 %**, mean 0.063 % |
| `rtl/fa_kernel.v` | single query block: D lanes, pipelined adder tree (registered per level, II=1), single-cycle m/l/o update, final `o·rcp(l)` | see §6 |

The two variants of `fa_kernel` share the same code and driver; only the update datapath differs
(`VARIANT=0` baseline, `VARIANT=1` ExpMul), mirroring the C++ comparison of Phase 2.

## 3. Primitive area (nangate45, µm²)

| Primitive | Area | Notes |
|---|---|---|
| FP32 multiplier | **4069.5** | 24×24 mantissa multiply, normalisation, RNE |
| FP32 adder | **1519.7** | 33-bit alignment, leading-zero count, RNE |
| `exp_pwl` | **4320.9** | one FP32 multiply + LUT multiply-add + exponent restore |
| `rcp_pwl` (1/x) | **1668.4** | 8-segment PWL reciprocal |
| **ExpMul (Alg. 3, exponent-only)** | **699.6** | pure integer shift-and-add |
| ExpMul (mantissa-interpolated) | 856.0 | one extra integer addition |

**Per-lane update datapath**:

- baseline: `2×FP32 mul + 1×FP32 add = 9658.7` (the two exponential units are shared by the block
  and counted once each)
- ExpMul: `2×ExpMul + 1×FP32 add = 2918.9` → **69.8 % saving per lane**

## 4. Block-level area (composed from the primitives, Fig. 1/2 structure)

Block = dot-product tree (D multipliers + D−1 adders) + update (D lanes) + final division
(1 reciprocal + D multipliers). The dot product and the division are identical in both versions;
only the update differs.

| d | baseline (µm²) | ExpMul (µm²) | Saving | Paper Fig. 3 (FP32) |
|---|---|---|---|---|
| 16 | 317 870 | 206 395 | **35.07 %** | 23.6 % |
| 32 | 626 949 | 412 640 | **34.18 %** | — |
| 64 | 1 245 107 | 825 132 | **33.73 %** | 29.7 % |
| 256 | 4 954 058 | 3 300 081 | **33.39 %** | 33.1 % |

Average **34.1 %** against the reported 28.8 %. Sources of the gap (see §7):

- The paper's block contains fixed overheads (control, multiplexing, register files): its d = 16
  saving is only 23.6 %, which shows that those overheads dominate at small d. The composed model
  omits them, so it over-estimates at small d.
- The baseline exponential of the paper may be relatively more expensive, and Catapult may map the
  exponential LUT to a distributed ROM, which changes the area accounting.

## 5. Power (post-route + gate-level VCD activity)

Flow: `gen_cell_models.py` (Liberty → 114 behavioural cells) → 300 random cycles on the post-route
netlist (Icarus Verilog) → VCD → `read_vcd -scope tb/dut` + `report_power` with SPEF.

| Data type | Variant | Area (µm²) | Area saving | Internal | Switching | Leakage | **Power (mW)** | Power saving |
|---|---|---|---|---|---|---|---|---|
| FP32 | baseline | 30 539 | — | 1.31 | 1.47 | 0.646 | **3.42** | — |
| FP32 | ExpMul | 9 362 | **−69.3 %** | 0.356 | 0.447 | 0.221 | **1.02** | **−70.2 %** |
| BF16 | baseline | 9 041 | — | 0.331 | 0.394 | 0.206 | **0.931** | — |
| BF16 | ExpMul | 5 092 | **−43.7 %** | 0.195 | 0.238 | 0.121 | **0.554** | **−40.5 %** |

![Area and power](phase4_power.png)

Observations:

1. The FP32 gain is the largest (area −69 %, power −70 %) because six FP32 multipliers and two PWL
   exponentials (two multipliers each) are removed.
2. BF16 gains less (−44 % / −40 %): bf16 multipliers are already small, so replacing them with
   integer shift-and-add yields a smaller marginal benefit; the absolute area of the BF16 ExpMul
   lane (5 092 µm²) is nevertheless one sixth of the FP32 baseline.
3. All four designs complete to `6_final.gds`; post-route area and power come from the same
   ORFS + VCD methodology.

**Block-level extrapolation (estimate)**: at d = 64 the update path accounts for about 50 % of the
baseline block area (626.8k / 1245.1k µm²). If the power density were similar, the block-level
saving would be ≈ 0.50 × 70.2 % ≈ **35 %**, above the 17.6 % reported in the paper. The reason is
the same as for area: the paper's block also contains control, registers and shared exponential
logic, and its exponential unit is relatively cheaper; the measured lane contains only the part
that ExpMul replaces, so the ratio is higher.

## 5.1 BF16 RTL

Added (same structure as the FP32 version, 16-bit datapath):

| File | Contents |
|---|---|
| `rtl/bf16_funcs.vh` | `fmul16` / `fadd16` (1-8-7, RNE, FTZ) |
| `rtl/bf16_ops.v` | `expmul_bf16` (Alg. 3, MODE 0/1) + `exp_pwl_bf16` (8-segment PWL with bf16 LUT) |
| `rtl/fa_lane_bf16.v` | single sigma* lane (VARIANT 0/1) |
| `rtl/tb_bf16.v` | numerical sanity: one step with x = −1, V = 1 gives o ≈ e⁻¹+1 and l ≈ 1.37 |
| `rtl/tb_lane_gate16.v` | bf16 gate-level stimulus (VCD) |
| `scripts/setup_orfs_bf16.sh`, `power_bf16.sh` | P&R and power |

The two BF16 designs also use **distinct top-level module names** (`fa_bf16_b_top` /
`fa_bf16_e_top`) to prevent ORFS from reusing a synthesised database; `6_final.v` has 6 448 vs.
3 972 instances and 286 vs. 157 `MUX2_X1` cells, and the GDS files are 5.8 MB and 3.6 MB.

## 6. Functional verification status

- FP32 multiply/add: **bit-exact against NumPy float32 on 4 000 random vectors**
  (`scripts/check_fp32_rtl.py`).
- ExpMul MODE0: 4 999/5 000 bit-exact; MODE1: 4 996/5 000. The mismatches are cases where `x·1024`
  falls on a .5 rounding boundary (C++ evaluates in double, RTL shifts a 24-bit mantissa); the
  quantisation step is 2^-10 and the impact on the result is below 0.1 %.
- `exp_pwl`: maximum relative error 0.52 %, mean 0.063 % over 5 000 points (the theoretical value
  of an 8-segment PWL is about 0.09 %; the maximum occurs near integer transitions of `|y|`).
- `fa_kernel` has not yet been compared end-to-end bit-for-bit against the C++ model (differences
  should come only from FP rounding); it elaborates and synthesises correctly, and end-to-end
  co-simulation is the first item of the next phase.

## 7. Differences from the paper

1. **Process**: nangate45 vs. 28 nm. Absolute areas differ by about 2.6×, but both versions use
   the same library, so the ratio is comparable. The paper reports 5.3×10⁵ µm² for the d = 64
   FP32 baseline at 28 nm, i.e. about 1.38×10⁶ µm² at 45 nm; the composed model gives
   1.245×10⁶ µm², **the same order of magnitude** (10 % difference).
2. **The saving is higher (34 % vs. 29 %)**: fixed overheads (control, registers, multiplexing)
   are not included; the paper's HLS code also contains the max tree and shared exponential
   scaling.
3. **Trend with d**: the paper's saving grows with d (23.6 % → 33.1 %) because fixed overheads are
   amortised; the composed model is almost flat (35 % → 33 %), which confirms the absence of a
   fixed-overhead term.
4. **Power**: the single lane is measured (post-route + VCD + SPEF): FP32 3.42 → 1.02 mW
   (−70.2 %), BF16 0.931 → 0.554 mW (−40.5 %). Only the **full-kernel** figure remains an
   extrapolation: ≈ −35 % from the area share of the update path, because only the lane has been
   taken through P&R so far and the dot-product tree, divider and control logic are not yet in the
   same netlist. An earlier statement quoting an estimate of 20.6 % was produced before switching
   activity was available and has been superseded by the measurements above.

## 8. Reproduction

```bash
# inside the container
bash scripts/synth_units.sh          # primitive areas → syn/units/*.stat
python3 model/area_model.py          # composed block area → results/phase4/area_model.csv
```

Artifacts: `results/phase4/area_model.csv`, `lane_pnr.json`, `power_*.log`,
`syn/units/*.stat|*.log` (in the remote work directory).
