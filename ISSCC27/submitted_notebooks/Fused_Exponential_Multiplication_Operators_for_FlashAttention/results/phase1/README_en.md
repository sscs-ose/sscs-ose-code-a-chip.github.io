# Phase 1 — ExpMul operator implementation and error characterisation

**English** | [中文](README_zh.md)

Corresponds to **Algorithm 3 / Eqs. (4)–(9)** of the paper:
`ExpMul(x, V) = e^x · V`, with `x ≤ 0`.

## 1. Mathematical definition (as specified)

```
x_clip = Clip(x, -15, 0)                    # e^-15 = 3.06e-7; smaller values are irrelevant
x_hat  = Fixed(x_clip)                       # 16-bit fixed point: 6 integer + 10 fractional bits (Q6.10)
S      = x_hat + (x_hat >> 1) - (x_hat >> 4) # ≈ -x·log2(e), Q6.10 (1.4375 ≈ log2 e)
L      = -S / 2^10   (rounded)               # integer number of binary steps
Out[i] = Float(S_V, E_V - L, M_V)            # exponent field only; E_V - L <= 0 → 0
```

`L` must be an **integer**, because Eq. (9) applies it as an exponent offset. Since `x_hat` is
Q6.10, `S` is Q6.10 as well and `−S/2^10` is what counts binary steps. The implementation uses
`L = (p + 512) >> 10` with `p = -S ≥ 0`, i.e. round-to-nearest; the paper states that the operator
"returns its **rounded** negative value".

> Note: line 6 of Algorithm 3 is written as `−⌊x̂ + x̂≫1 − x̂≫4⌉`, where `⌊·⌉` denotes rounding.
> Reading `⌊·⌋` literally as floor and then dividing by 2^10 gives `ceil(−x·log2 e)`, which is the
> `LOG2EXP_CEIL` variant of this repository; it systematically lowers every weight by −0.49 binary
> steps on average (see the table below). Both readings are implemented; round-to-nearest is the
> default.

Fixed-point range check: `x_hat ∈ [-15360, 0]` (16-bit signed), `S ∈ [-22080, 0]`,
`p ≤ 22080 → L ≤ 22`, which fits exactly the `x·log2 e ∈ [-21.64, 0]` range covered by 6 integer
bits.

## 2. Three implementation variants (one testbench)

| Variant | Definition | Notes |
|---|---|---|
| `exp_only_near` | Algorithm 3 as written, `L` rounded | **primary implementation**; the result is determined by the exponent field alone |
| `exp_only_ceil` | `L = ceil(-x·log2 e)` | literal reading of `⌊·⌋`, ablation only |
| `mantissa_int` | `bits(V) − round(p·2^M/2^10)` (`M` = 23/7) | integer-add form used by the paper's **official repository** [15]: the integer part shifts the exponent, the fractional part interpolates the mantissa; still pure integer shift-and-add, no dequantisation |

The third variant is not an additional accuracy patch: it is what the released HLS code
(`fused_operators.h::mitchExpMul`) actually does, adding `x_eff` directly to the integer
representation of `V`. Algorithm 3 in the paper describes only the exponent field and omits this
mantissa carry; the hardware cost of the two is almost identical (one integer subtract versus
field extraction and insertion).

## 3. Error results (2 000 000 random pairs, seed 20250520)

`x ~ 0.45·U[-4,0] + 0.30·U[-10,0] + 0.25·U[-15,0]`; `V` has random sign, exponent ∈ [60,190] and
random mantissa.

| Variant | mean | RMS | p50 | p90 | p99 | max | fraction with error ≤ 5 % |
|---|---|---|---|---|---|---|---|
| `exp_only_near` | +0.0000 | **0.2117** | 0.1749 | 0.3412 | 0.4298 | 0.4925 | 14.1 % |
| `exp_only_ceil` | +0.0003 | 0.3091 | 0.2897 | 0.4572 | 0.4913 | 0.4998 | 9.1 % |
| `mantissa_int` | −0.0000 | **0.0331** | 0.0221 | 0.0547 | 0.0855 | 0.1202 | 86.7 % |

- The error of the exponent-only variant comes from quantising the weight to an integer power of
  two; the ratio lies in `[2^-0.5, 2^0.5]`, so an RMS of 21 % is the lower bound of the method,
  not an implementation bug.
- The mantissa-interpolated variant reduces the error to 3.3 % (theoretical sawtooth error of a
  piecewise-linear approximation of 2^−f, maximum about 11 %).
- `L` equals the ideal value `round(-x·log2 e)` in **97.79 %** of the cases; mean `|ΔL| = 0.022`.
- The weight equals 1 (`L = 0`) for 5.5 % of the cases, i.e. `x ∈ (-0.35, 0]` is not scaled.

### Breakdown by |x| (`exp_only_near`)

| \|x\| | Samples | mean | RMS | max | E\|ΔL\| |
|---|---|---|---|---|---|
| 10–15 | 166 651 | −0.00033 | 0.2284 | 0.4925 | 0.0703 |
| 7–10 | 280 335 | −0.00031 | 0.2159 | 0.4626 | 0.0400 |
| 4–7 | 279 497 | +0.00033 | 0.2047 | 0.4471 | 0.0265 |
| 2–4 | 636 912 | +0.00012 | 0.2108 | 0.4333 | 0.0161 |
| 1–2 | 318 794 | +0.00022 | 0.2155 | 0.4226 | 0.0097 |
| 0.5–1 | 158 964 | −0.00003 | 0.1688 | 0.3591 | 0.0000 |
| 0–0.5 | 158 847 | −0.00019 | 0.2322 | 0.4164 | 0.0031 |

`|ΔL|` grows with |x|; it is caused by the difference between the constant 1.4375 and
log2 e = 1.4427 (0.005·|x| binary steps).

## 4. Boundary cases

| Case | x | V | Out | Result |
|---|---|---|---|---|
| identity | 0 | 1.0 | 1.0 | `x = 0 → Out ≡ V` (bit-exact) |
| negative zero | −0.0 | 1.0 | 1.0 | same |
| tiny negative | −1e-9 | 1.0 | 1.0 | `L = 0` |
| lower clip | −15 | 1.0 | 2.384e-7 | `L = 22`, `2^-22/e^-15 = 0.78` |
| beyond clip | −20 | 1.0 | 2.384e-7 | identical to −15, never smaller |
| positive (illegal) | +3 | 1.0 | 1.0 | clipped to 0, **no positive exponent overflow** |
| NaN | NaN | 1.0 | 1.0 | clip maps NaN to 0, output stays finite |
| fixed-point underflow | −1 | `FLT_MIN` | 0 | `E_V − L = 0` → subnormal → flushed to 0 |
| subnormal input | 0 | 1e-40 | 0 | subnormal input returns 0 |
| largest normal | −15 | `FLT_MAX` | 8.11e31 | exponent 254−22 = 232, no overflow |
| Inf | 0 | +Inf | +Inf | passed through |

Invariants (asserted): bit-exact identity at `x = 0`; `|Out| ≤ |V|`; `L(x)` is monotone on
[−15, 0] (non-increasing as x grows); **no NaN or infinity** was produced in any random test.

## 5. Verification

- **C++ ↔ Python bit-exactness**: for 100 000 pairs (x, V) both `L` and the output bit pattern
  agree (`python model/expmul_ref.py --check results/phase1/expmul_pairs.csv`).
- The two implementations were written independently (C++ with `int16_t` and bit fields, Python
  with vectorised NumPy), so shift-sign and rounding-direction errors would surface as mismatches.
- Reproduction commands, seeds and compiler versions are in `expmul_run.log` in this directory and
  in the top-level `README.md`.

## 6. Figures

![Weight and relative error](phase1_weight_ratio.png)

![Error distribution](phase1_error_hist.png)

![Error versus x](phase1_error_vs_x.png)

## 7. From operator error to attention error (NumPy probe)

With the same random `q, k, v` (`d = 64`, `N = 128/512`), using `2^-L` as softmax weights and
`o/l` normalisation (`tools/probe_attention_error.py`):

| Configuration | Exponent-only ExpMul | Mantissa-interpolated ExpMul | Mean peak weight |
|---|---|---|---|
| d=64, N=128, temperature 1× | 15.8 % | **2.50 %** | 0.074 |
| d=64, N=512 | 17.4 % | **2.25 %** | 0.026 |
| d=64, N=128, temperature 2× | 11.8 % | **2.92 %** | 0.242 |

The `o/l` normalisation absorbs a significant part of the error (21 % → 16 %), but the
exponent-only variant still leaves about 16 % error on the attention output, whereas the
mantissa-interpolated variant leaves about 2.5 %. This explains how Table I of the paper can be
essentially identical to FP32: **the released implementation carries the mantissa**. Phase 2
re-checks both numbers with a synthesizable kernel.

## 8. Conclusions / input to Phase 2

1. The exponent-only ExpMul (literal Algorithm 3) has an RMS of 21 % on a **single element**,
   which is the inherent cost of logarithmic weight quantisation. After `o/l` normalisation the
   error drops to about 16 % on the attention output and must be re-checked with the full kernel
   in Phase 2.
2. The mantissa-interpolated form of the official repository has an RMS of 3.3 % and about 2.5 %
   at the attention output, at the cost of one extra integer addition. Phases 2 and 3 evaluate it
   as the "paper-equivalent" variant.
3. Phase 2 compares `baseline (exp_pwl + FP mul)`, `exp_only` and `mantissa_int` on the same
   (q, k, v) and reports the distribution of the attention-output relative error.
