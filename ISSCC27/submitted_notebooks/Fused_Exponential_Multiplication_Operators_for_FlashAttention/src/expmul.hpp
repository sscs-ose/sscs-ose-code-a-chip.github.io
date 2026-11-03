// ============================================================================
//  expmul.hpp -- ExpMul(x, V) = e^x * V  (x <= 0)
//
//  Reproduction of Algorithm 3 of:
//    K. Alexandridis, V. Titopoulos, G. Dimitrakopoulos,
//    "Low-Cost FlashAttention with Fused Exponential and Multiplication
//     Hardware Operators", arXiv:2505.14314 [cs.AR], May 2025.
//    (IEEE, 2025)  DOI: 10.1109/... (see paper/ for the PDF snapshot)
//
//  The operator is bit-accurate with the RTL in rtl/fa_expmul.v:
//    X_hat = Fixed(Clip(X, -15, 0))            Q6.10, 16-bit, value = raw/1024
//    S     = X_hat + (X_hat >> 1) - (X_hat >> 4)      [-x*log2(e), Q6.10]
//    L     = round(-S / 2^10)                 integer number of 2^-1 steps
//    Out   = Float(S_V, E_V - L, M_V)          exponent domain subtraction,
//                                             underflow (E_V - L <= 0) -> 0
//
//  No dequantisation step: Out is produced directly in the target FP format.
//
//  Two rounding modes for Log2Exp are provided:
//    * LOG2EXP_NEAREST : Eq.(6)/(7) of the paper, "rounded negative value"
//                        (default, used for all reported results)
//    * LOG2EXP_CEIL    : literal -floor(S) reading of Alg.3 line 6, i.e.
//                        ceil(-x*log2(e)); kept as an ablation (biases all
//                        weights low, never above e^x)
//    * LOG2EXP_TRUNC   : truncation of the Q6.10 product (ablation)
// ============================================================================
#ifndef FA_EXPMUL_HPP
#define FA_EXPMUL_HPP

#include <cstdint>
#include <cmath>
#include <cstring>

namespace fa {

#if defined(__SYNTHESIS__)
#define FA_HLS(x) _Pragma(#x)
#else
#define FA_HLS(x)
#endif

// ---------------------------------------------------------------------------
//  rounding modes for the integer exponent L
// ---------------------------------------------------------------------------
enum Log2ExpMode : int {
  LOG2EXP_NEAREST = 0,  // paper Eq.(6)/(7)  : L = round(-x*log2 e)
  LOG2EXP_CEIL    = 1,  // literal -floor() : L = ceil (-x*log2 e)
  LOG2EXP_TRUNC   = 2   // truncation       : L = trunc(-x*log2 e)
};

// ---------------------------------------------------------------------------
//  bit-level helpers
// ---------------------------------------------------------------------------
inline uint32_t f2u(float f) {
  uint32_t u;
  std::memcpy(&u, &f, sizeof(u));
  return u;
}
inline float u2f(uint32_t u) {
  float f;
  std::memcpy(&f, &u, sizeof(f));
  return f;
}

// IEEE-754 binary32 constants
static constexpr int FP32_EXP_BITS  = 8;
static constexpr int FP32_MANT_BITS = 23;
static constexpr uint32_t FP32_EXP_MAX  = 0xFFu;
static constexpr uint32_t FP32_MANT_MSK = 0x007FFFFFu;
static constexpr uint32_t FP32_SIGN_MSK = 0x80000000u;

// bfloat16 constants
static constexpr int BF16_EXP_BITS  = 8;
static constexpr int BF16_MANT_BITS = 7;
static constexpr uint16_t BF16_EXP_MAX  = 0xFFu;
static constexpr uint16_t BF16_MANT_MSK = 0x007Fu;
static constexpr uint16_t BF16_SIGN_MSK = 0x8000u;

// ---------------------------------------------------------------------------
//  float <-> bfloat16 (round-to-nearest-even, NaN preserved)
// ---------------------------------------------------------------------------
inline uint16_t f2bf(float f) {
  uint32_t u = f2u(f);
  if ((u & 0x7FFFFFFFu) > 0x7F800000u) {           // NaN
    return (uint16_t)((u >> 16) | 0x0040u);
  }
  uint32_t lsb = (u >> 16) & 1u;
  u += 0x7FFFu + lsb;                              // RNE
  return (uint16_t)(u >> 16);
}
inline float bf2f(uint16_t b) {
  return u2f(((uint32_t)b) << 16);
}

// ---------------------------------------------------------------------------
//  Q6.10 fixed point of the clipped log-domain input
//    raw in [-15360, 0], value = raw / 1024
// ---------------------------------------------------------------------------
struct q6_10 {
  int16_t raw;
};

static constexpr int32_t Q_FRAC_BITS = 10;
static constexpr int32_t Q_ONE       = 1 << Q_FRAC_BITS;   // 1024
static constexpr int32_t Q_MIN_RAW   = -15 * Q_ONE;        // -15360  (Clip -15)
static constexpr int32_t Q_MAX_RAW   = 0;                  // Clip 0

// Fixed(Clip(X,-15,0)) with round-half-up; exact in binary32 for |x| <= 15
inline q6_10 to_q6_10(float x) {
  float xc = x;
  if (!(xc <= 0.0f)) xc = 0.0f;      // also maps +0/-0 and NaN to 0
  if (xc < -15.0f)   xc = -15.0f;
  float s = xc * (float)Q_ONE;       // exact (power of two scaling)
  int32_t r = (int32_t)std::floor(s + 0.5f);
  if (r > Q_MAX_RAW) r = Q_MAX_RAW;
  if (r < Q_MIN_RAW) r = Q_MIN_RAW;
  q6_10 q;
  q.raw = (int16_t)r;
  return q;
}

// Arithmetic right shift with floor semantics (identical to RTL >>> on signed)
inline int32_t asr(int32_t v, int n) {
  const int32_t d = (int32_t)1 << n;
  int32_t q = v / d;
  if ((v % d) != 0 && v < 0) --q;
  return q;
}

// ---------------------------------------------------------------------------
//  Log2Exp(x) : integer L with e^x ~ 2^-L  (paper Eq.(6),(7))
// ---------------------------------------------------------------------------
inline int32_t log2exp_q(const q6_10& q, Log2ExpMode mode = LOG2EXP_NEAREST) {
  const int32_t xh = (int32_t)q.raw;                    // Q6.10, <= 0
  const int32_t s  = xh + asr(xh, 1) - asr(xh, 4);      // ~ -x*log2(e), Q6.10
  const int32_t p  = -s;                                // >= 0, Q6.10
  int32_t L;
  switch (mode) {
    case LOG2EXP_CEIL:  L = (p + (Q_ONE - 1)) >> Q_FRAC_BITS; break;  // ceil
    case LOG2EXP_TRUNC: L = p >> Q_FRAC_BITS;                 break;  // trunc
    case LOG2EXP_NEAREST:
    default:            L = (p + (Q_ONE / 2)) >> Q_FRAC_BITS; break;  // round
  }
  return L;
}
inline int32_t log2exp(float x, Log2ExpMode mode = LOG2EXP_NEAREST) {
  return log2exp_q(to_q6_10(x), mode);
}

// 2^-L as binary32 (diagnostics only -- hardware uses exponent subtraction)
inline float weight_from_L(int32_t L) {
  if (L <= 0)   return 1.0f;
  if (L > 126)  return 0.0f;
  return u2f(((uint32_t)(127 - L)) << 23);  // (127-L) is the biased exponent
}

// ---------------------------------------------------------------------------
//  Variant 2: fractional residual folded into the mantissa ("mantissa
//  interpolation").  This is what the released HLS implementation
//  (github.com/ic-lab-duth/Fused-ExpMul, ref. [15]) actually does: the
//  integer representation of V is offset by (-x*log2e)*2^M, so the integer
//  part shifts the exponent and the fractional part interpolates 2^-f
//  linearly in the mantissa.  Still pure integer shift-add, still no
//  dequantisation; one 32-bit (resp. 16-bit) integer subtract instead of a
//  field extract/insert.
// ---------------------------------------------------------------------------
inline int32_t q_residual_q610(float x) {
  const int32_t xh = (int32_t)to_q6_10(x).raw;
  return -(xh + asr(xh, 1) - asr(xh, 4));   // p >= 0, Q6.10 of -x*log2e
}

inline float expmul_mi_fp32(float x, float v) {
  const int32_t p = q_residual_q610(x);          // Q6.10
  const uint32_t D = ((uint32_t)p) << (FP32_MANT_BITS - Q_FRAC_BITS);  // ulp of M
  uint32_t b = f2u(v);
  const int32_t e = (int32_t)((b >> FP32_MANT_BITS) & FP32_EXP_MAX);
  if (e == (int32_t)FP32_EXP_MAX) return v;      // inf / NaN
  if (e == 0)                     return 0.0f;   // zero / subnormal
  const uint32_t mag = b & 0x7FFFFFFFu;
  if (D >= mag)                   return 0.0f;   // underflow
  const uint32_t mag2 = mag - D;
  if ((mag2 >> FP32_MANT_BITS) == 0) return 0.0f;  // subnormal result
  return u2f((b & FP32_SIGN_MSK) | mag2);
}

inline uint16_t expmul_mi_bf16(float x, uint16_t vb) {
  const int32_t p = q_residual_q610(x);          // Q6.10
  const uint32_t D = (uint32_t)((p + (1 << (Q_FRAC_BITS - BF16_MANT_BITS - 1)))
                                >> (Q_FRAC_BITS - BF16_MANT_BITS));   // rounded
  const uint16_t e = (uint16_t)((vb >> BF16_MANT_BITS) & BF16_EXP_MAX);
  if (e == BF16_EXP_MAX) return vb;
  if (e == 0)            return 0;
  const uint32_t mag = vb & 0x7FFFu;
  if (D >= mag)          return 0;               // underflow
  const uint32_t mag2 = mag - D;
  if ((mag2 >> BF16_MANT_BITS) == 0) return 0;   // subnormal result
  return (uint16_t)((vb & BF16_SIGN_MSK) | mag2);
}

// ---------------------------------------------------------------------------
//  The fused exponent update: Out = Float(S_V, E_V - L, M_V)
//  (pure bit manipulation; one integer subtract per element)
// ---------------------------------------------------------------------------
inline float shift_fp32(int32_t L, float v) {
  uint32_t b = f2u(v);
  uint32_t sign = b & FP32_SIGN_MSK;
  int32_t  e    = (int32_t)((b >> FP32_MANT_BITS) & FP32_EXP_MAX);
  uint32_t mant = b & FP32_MANT_MSK;

  if (e == (int32_t)FP32_EXP_MAX) return v;   // inf/NaN: leave untouched
  if (e == 0)                    return 0.0f;  // zero or subnormal input
  int32_t ne = e - L;
  if (ne <= 0)                   return 0.0f;  // underflow -> flush to zero
  return u2f(sign | ((uint32_t)ne << FP32_MANT_BITS) | mant);
}

inline uint16_t shift_bf16(int32_t L, uint16_t vb) {
  uint16_t sign = vb & BF16_SIGN_MSK;
  int32_t  e    = (vb >> BF16_MANT_BITS) & BF16_EXP_MAX;
  uint16_t mant = vb & BF16_MANT_MSK;

  if (e == (int32_t)BF16_EXP_MAX) return vb;  // inf/NaN
  if (e == 0)                     return 0;    // zero / subnormal
  int32_t ne = e - L;
  if (ne <= 0)                    return 0;    // underflow
  return (uint16_t)(sign | (ne << BF16_MANT_BITS) | mant);
}

// ---------------------------------------------------------------------------
//  Scalar reference models
// ---------------------------------------------------------------------------
inline float expmul_fp32(float x, float v, Log2ExpMode mode = LOG2EXP_NEAREST) {
  return shift_fp32(log2exp(x, mode), v);
}
inline uint16_t expmul_bf16(float x, uint16_t v, Log2ExpMode mode = LOG2EXP_NEAREST) {
  return shift_bf16(log2exp(x, mode), v);
}

// ---------------------------------------------------------------------------
//  Vector form (one L per ExpMul call, d lanes of pure exponent subtraction)
//  This mirrors the hardware: a shared shift-and-add unit feeding d lanes.
// ---------------------------------------------------------------------------
template <int D>
inline void expmul_vec_fp32(float x, const float* V, float* Out,
                            Log2ExpMode mode = LOG2EXP_NEAREST) {
  FA_HLS(HLS inline)
  const int32_t L = log2exp(x, mode);
  FA_HLS(HLS ARRAY_PARTITION variable=V complete)
  FA_HLS(HLS ARRAY_PARTITION variable=Out complete)
  for (int i = 0; i < D; ++i) {
    FA_HLS(HLS UNROLL)
    Out[i] = shift_fp32(L, V[i]);
  }
}

template <int D>
inline void expmul_vec_bf16(float x, const uint16_t* V, uint16_t* Out,
                            Log2ExpMode mode = LOG2EXP_NEAREST) {
  FA_HLS(HLS inline)
  const int32_t L = log2exp(x, mode);
  FA_HLS(HLS ARRAY_PARTITION variable=V complete)
  FA_HLS(HLS ARRAY_PARTITION variable=Out complete)
  for (int i = 0; i < D; ++i) {
    FA_HLS(HLS UNROLL)
    Out[i] = shift_bf16(L, V[i]);
  }
}

}  // namespace fa

#endif  // FA_EXPMUL_HPP
