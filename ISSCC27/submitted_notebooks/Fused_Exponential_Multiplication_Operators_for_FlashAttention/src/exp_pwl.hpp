// ============================================================================
//  exp_pwl.hpp -- baseline exponential unit: piecewise-linear approximation
//  after range reduction, input range [-15, 0] (same range as ExpMul).
//
//  This is the "state-of-the-art" exp operator the paper compares against
//  (ref. [25]: Koca et al., ISCAS 2023 -- PWL after range reduction):
//
//      y = x * log2(e)          FP multiply (range reduction)
//      k = floor(y), f = y - k  integer + fraction
//      2^f ~= c_i + s_i * f     SEG-segment PWL over [0,1)
//      e^x  = 2^k * 2^f         exponent-field add (bit exact)
//
//  SEG = 8 gives a max relative error of ~0.09% (see results/phase2).
//  The unit is combinational; in hardware it is a LUT + FP mul + FP add.
// ============================================================================
#ifndef FA_EXP_PWL_HPP
#define FA_EXP_PWL_HPP

#include <cmath>
#include <cstdint>
#include <cstring>

namespace fa {

template <int SEG = 8>
struct ExpPwl {
  // c_i = 2^(i/SEG), s_i = 2^((i+1)/SEG) - 2^(i/SEG), evaluated once at compile
  // time; in RTL these are two constant LUTs indexed by the segment number.
  float c[SEG];
  float s[SEG];

  ExpPwl() {
    for (int i = 0; i < SEG; ++i) {
      float a = std::exp2((float)i / (float)SEG);
      float b = std::exp2((float)(i + 1) / (float)SEG);
      c[i] = a;
      s[i] = b - a;
    }
  }

  inline float operator()(float x) const {
    if (!(x < 0.0f)) return 1.0f;             // x == 0 -> exact 1
    if (x < -15.0f) x = -15.0f;               // same clip as ExpMul
    float y = x * 1.4426950408889634f;        // x * log2(e)
    float kf = std::floor(y);                 // kf <= 0
    float f = y - kf;                         // [0,1)
    int idx = (int)(f * (float)SEG);
    if (idx >= SEG) idx = SEG - 1;            // guard f == 1.0 rounding
    float t = f * (float)SEG - (float)idx;    // [0,1)
    float p = c[idx] + s[idx] * t;            // 2^f
    // 2^k * p  (k <= 0): exponent field += k
    int32_t k = (int32_t)kf;
    uint32_t bits;
    std::memcpy(&bits, &p, 4);
    int32_t e = (int32_t)((bits >> 23) & 0xFF) + k;
    if (e <= 0) return 0.0f;
    bits = (bits & 0x807FFFFFu) | ((uint32_t)e << 23);
    float r;
    std::memcpy(&r, &bits, 4);
    return r;
  }
};

// one shared, statically initialised instance (zero run-time cost in HLS)
template <int SEG = 8>
inline const ExpPwl<SEG>& exp_pwl_unit() {
  static const ExpPwl<SEG> u;
  return u;
}

template <int SEG = 8>
inline float exp_pwl(float x) {
  return exp_pwl_unit<SEG>()(x);
}

}  // namespace fa

#endif  // FA_EXP_PWL_HPP
