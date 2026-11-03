# Phase 2 — Integrating ExpMul into the FlashAttention-2 kernel

**English** | [中文](README_zh.md)

Corresponds to **Algorithms 2 and 4, Eqs. (2)(3)(5)**, and the block-parallel structure of
**Figs. 1 and 2**.

## 1. Implementation structure (fair comparison)

`src/flash_attn_kernel.hpp` contains a single driver shared by both versions:

```
fa2_driver<P, D, T>(Q, K, V, N, O, updater)
    ├─ P query vectors pre-loaded (the query block of Fig. 1)
    ├─ for i in 0..N-1:  k_i, v_i broadcast to the P blocks
    │      s = dot(q, k_i)            # FP32 accumulation
    │      updater(state, s, v_i)     # ← the only difference
    └─ attn = o / l                   # delayed softmax division
```

| | baseline (`flash_attn_baseline.cpp`) | ExpMul (`flash_attn_expmul.cpp`) |
|---|---|---|
| Update | two `exp_pwl` units for `m_prev-m` and `s-m` | two `ExpMul` operators, one `L` each |
| Multiplies | 2 FP32 multiplies per lane | none |
| Adds | 2 FP32 multiplies + 1 FP32 add per lane | 1 integer exponent update + 1 FP32 add per lane |
| Loop order | identical | identical |

- `sigma* = [l, o]` and `v* = [1, v]` are built explicitly (`ExpMulUpdate`), so `l` and `o` share
  the same ExpMul pipeline (Eqs. 3 and 5).
- The baseline exponential is an 8-segment piecewise-linear approximation after range reduction,
  with the same [-15, 0] clipping; measured **maximum relative error 0.094 %, mean 0.063 %**
  (`exp_unit_error.csv`).
- The BF16 version follows `ac::bfloat16` semantics: every storage element and operation is
  rounded to bf16, as in the paper's HLS code.

## 2. Functional correctness (against a double-precision reference, same loop order)

Metric: per-query `||o − ref||₂ / ||ref||₂`, averaged over N queries; random q, k, v
(seed 20250520), with `q` scaled so that the score standard deviation equals the temperature.

| d=64, T=1 | N=16 | N=64 | N=128 | N=512 |
|---|---|---|---|---|
| baseline FP32 | 0.05 % | 0.07 % | 0.07 % | **0.08 %** |
| ExpMul exponent-only (Alg. 3) | 12.3 % | 19.7 % | 18.6 % | 22.5 % |
| ExpMul mantissa-interpolated | 3.28 % | 4.47 % | 4.62 % | **5.06 %** |
| baseline BF16 | 0.69 % | 1.16 % | 1.70 % | 14.4 % |
| ExpMul exponent-only BF16 | 13.3 % | 18.0 % | 18.9 % | 34.3 % |
| ExpMul mantissa-interpolated BF16 | 2.68 % | 4.38 % | 4.49 % | 12.0 % |

For d = 16 and 32 see `errors_matrix.csv`; the trend is the same (11–22 % exponent-only,
2.3–5.1 % mantissa-interpolated).

Observations:

1. **The exponent-only error stabilises at 12–22 % as N grows**, consistent with the operator-level
   RMS of 21 % from Phase 1; the `o/l` normalisation absorbs only a common scaling, not
   element-wise weight error.
2. **The mantissa-interpolated variant stays at 2–5 %**: most of its error comes from repeatedly
   applying ExpMul to the `o` accumulator (multiplicative accumulation), not from the single-
   operator error (3.3 % RMS).
3. At N = 512 the BF16 baseline is **worse** than ExpMul-MI (14.4 % vs. 12.0 %): rounding each PWL
   exponential to bf16 is **random noise**, whereas the logarithmic quantisation of ExpMul is a
   **smooth bias** that partially cancels in `o/l`.
4. Numerical stability (FP32, d = 64): with scores scaled to 1e3/1e6 the maximum absolute error of
   all three implementations stays around 1e-5, while a **naive softmax without max subtraction
   overflows** (`naive_exp_overflow=1`); no NaN or infinity occurs.
   The `uniform` and `single_key` cases cover equal weights and N = 1.

![Error versus N](phase2_error_vs_N.png)

![Per-query error distribution](phase2_error_hist.png)

## 3. Numerical-stability cases (excerpt, FP32)

| Case | Condition | baseline | ExpMul exponent-only | ExpMul MI | Naive exp overflow |
|---|---|---|---|---|---|
| random | σ_score = 1 | 7.4e-4 | 2.7e-1 | 4.2e-2 | no |
| huge_scores | σ_score = 1e3 | 4.8e-6 | 3.2e-6 | 4.8e-6 | **yes** |
| huge_scores | σ_score = 1e6 | 3.4e-6 | 2.3e-6 | 3.4e-6 | **yes** |
| uniform | all scores = 0 | 1.5e-7 | 1.5e-7 | 1.5e-7 | no |
| single_key | N = 1 | 0 | 0 | 0 | no |
| dominant_key | key 0 dominates | 2.7e-4 | 1.2e-2 | 7.7e-3 | no |

All cases have `nonfinite = 0`. Under huge scores the three implementations are almost bit-identical
because the softmax is extremely peaked and ExpMul is exact for the largest weight (`x = 0`,
`L = 0`).

## 4. Block-parallel structure

`P=4` (four queries in parallel with broadcast K/V) is **bit-identical** to processing one query at
a time with `P=1` (0 differing lanes, `blocking_check.csv`), confirming that broadcast and
pre-loading introduce no numerical difference.

## 5. Conclusions

- The operator-level conclusion of Phase 1 carries over to the kernel: literal Algorithm 3
  (exponent-only) produces about 15–20 % output error inside FlashAttention, **which cannot
  support the "same as FP32" result of Table I**; the mantissa-interpolated form used by the
  official repository gives 2–5 % and is the candidate for Phase 3.
- Phase 3 attaches both ExpMul variants to the Flan-T5 attention and measures GLUE to decide which
  one is the equivalent of the paper's method.
- In hardware the two differ by one integer addition; Phase 4 reports area and power for both.

## 6. Reproduction

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
.\build\tb.exe results\phase2
python model\plot_phase2.py
```

Artifacts: `errors_matrix.csv` (3 variants × 2 dtypes × 3 d × 4 N × 2 temperatures),
`detail_d64_N512_fp32.csv` (per-query error), `stability.csv`, `exp_unit_error.csv`,
`blocking_check.csv`, `phase2_stats.json`, `tb.log`.
