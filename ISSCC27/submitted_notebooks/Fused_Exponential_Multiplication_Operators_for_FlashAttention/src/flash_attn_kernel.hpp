// ============================================================================
//  flash_attn_kernel.hpp -- FlashAttention-2 kernel, shared by both versions
//
//  Algorithm 2 (FlashAttention-2, delayed softmax division):
//      s_i = dot(q, k_i)
//      m_i = max(m_{i-1}, s_i)
//      l_i = l_{i-1} e^{m_{i-1}-m_i} + e^{s_i-m_i}
//      o_i = o_{i-1} e^{m_{i-1}-m_i} + v_i e^{s_i-m_i}
//  with the Eq.(2)(3) merge  sigma* = [l, o],  v* = [1, v]:
//      sigma*_i = sigma*_{i-1} e^{m_{i-1}-m_i} + v*_i e^{s_i-m_i}
//  and the Eq.(5) ExpMul form used by the ExpMul version:
//      sigma*_i = ExpMul(m_{i-1}-m_i, sigma*_{i-1}) + ExpMul(s_i-m_i, v*_i)
//
//  The *only* difference between the two versions is the update functor:
//  BaselineUpdate  : exp PWL unit  + FP32 multiplies  + FP32 add
//  ExpMulUpdate    : ExpMul        + integer add
//  The loop order, the max subtraction and the final division are identical,
//  so the numerical comparison is apples-to-apples.
//
//  Fig.1/Fig.2 block structure: P query vectors are pre-loaded, K/V vectors are
//  streamed once and broadcast to all P blocks (see fa2_driver).
// ============================================================================
#ifndef FA_FLASH_ATTN_KERNEL_HPP
#define FA_FLASH_ATTN_KERNEL_HPP

#include <cstddef>
#include <cstdint>

#include "exp_pwl.hpp"
#include "expmul.hpp"

namespace fa {

// ---------------------------------------------------------------------------
//  storage / arithmetic policies (FP32 and BF16)
// ---------------------------------------------------------------------------
struct FP32Policy {
  using storage = float;
  static constexpr bool is_bf16 = false;
  static inline storage from_float(float x) { return x; }
  static inline float   to_float(storage x) { return x; }
  static inline storage add(storage a, storage b) { return a + b; }
  static inline storage mul(storage a, storage b) { return a * b; }
};

struct BF16Policy {
  using storage = uint16_t;
  static constexpr bool is_bf16 = true;
  static inline storage from_float(float x) { return f2bf(x); }
  static inline float   to_float(storage x) { return bf2f(x); }
  static inline storage add(storage a, storage b) { return f2bf(bf2f(a) + bf2f(b)); }
  static inline storage mul(storage a, storage b) { return f2bf(bf2f(a) * bf2f(b)); }
};

// ---------------------------------------------------------------------------
//  per-query state:  m (running max), l (sum of exponents), o[D]
// ---------------------------------------------------------------------------
template <int D, class T>
struct AttnState {
  typename T::storage o[D];
  typename T::storage l;
  typename T::storage m;
};

// ---------------------------------------------------------------------------
//  q . k  (FP32 accumulation, result rounded to the storage type)
// ---------------------------------------------------------------------------
template <int D, class T>
inline typename T::storage dot_qk(const typename T::storage* a,
                                  const typename T::storage* b) {
  float acc = 0.0f;
  for (int i = 0; i < D; ++i) acc += T::to_float(a[i]) * T::to_float(b[i]);
  return T::from_float(acc);
}

// ---------------------------------------------------------------------------
//  ExpMul over an N-element vector, dispatched on dtype and variant
//    VARIANT 0 = Alg.3 exponent-only (nearest rounding)
//    VARIANT 1 = mantissa interpolation (released implementation)
// ---------------------------------------------------------------------------
template <int N, class T, int VARIANT>
inline void expmul_vec_t(typename T::storage x, const typename T::storage* v,
                         typename T::storage* o) {
  const float xf = T::to_float(x);
  if constexpr (T::is_bf16) {
    if constexpr (VARIANT == 0) {
      const int32_t L = log2exp(xf, LOG2EXP_NEAREST);
      for (int i = 0; i < N; ++i) o[i] = shift_bf16(L, v[i]);
    } else {
      for (int i = 0; i < N; ++i) o[i] = expmul_mi_bf16(xf, v[i]);
    }
  } else {
    if constexpr (VARIANT == 0) {
      const int32_t L = log2exp(xf, LOG2EXP_NEAREST);
      for (int i = 0; i < N; ++i) o[i] = shift_fp32(L, v[i]);
    } else {
      for (int i = 0; i < N; ++i) o[i] = expmul_mi_fp32(xf, v[i]);
    }
  }
}

// ---------------------------------------------------------------------------
//  Baseline update: independent exp unit + standard FP multiply + FP add
// ---------------------------------------------------------------------------
template <int D, class T, int SEG = 8>
struct BaselineUpdate {
  inline void operator()(AttnState<D, T>& st, typename T::storage s,
                         const typename T::storage* v) const {
    FA_HLS(HLS inline)
    const float mp = T::to_float(st.m);
    const float sf = T::to_float(s);
    const float mn = (mp > sf) ? mp : sf;
    const typename T::storage e1 = T::from_float(exp_pwl<SEG>(mp - mn));
    const typename T::storage e2 = T::from_float(exp_pwl<SEG>(sf - mn));
    st.l = T::add(T::mul(st.l, e1), e2);
    FA_HLS(HLS UNROLL)
    for (int j = 0; j < D; ++j) {
      st.o[j] = T::add(T::mul(st.o[j], e1), T::mul(v[j], e2));
    }
    st.m = T::from_float(mn);
  }
};

// ---------------------------------------------------------------------------
//  ExpMul update: Eq.(3)(5) merged sigma* = [l, o],  v* = [1, v]
// ---------------------------------------------------------------------------
template <int D, class T, int VARIANT>
struct ExpMulUpdate {
  inline void operator()(AttnState<D, T>& st, typename T::storage s,
                         const typename T::storage* v) const {
    FA_HLS(HLS inline)
    const float mp = T::to_float(st.m);
    const float sf = T::to_float(s);
    const float mn = (mp > sf) ? mp : sf;

    typename T::storage sig[D + 1], vs[D + 1], a[D + 1], b[D + 1];
    sig[0] = st.l;
    vs[0] = T::from_float(1.0f);
    FA_HLS(HLS UNROLL)
    for (int j = 0; j < D; ++j) {
      sig[j + 1] = st.o[j];
      vs[j + 1] = v[j];
    }

    // two ExpMul operators, each one L for D+1 lanes
    expmul_vec_t<D + 1, T, VARIANT>(T::from_float(mp - mn), sig, a);
    expmul_vec_t<D + 1, T, VARIANT>(T::from_float(sf - mn), vs, b);

    st.l = T::add(a[0], b[0]);
    FA_HLS(HLS UNROLL)
    for (int j = 0; j < D; ++j) st.o[j] = T::add(a[j + 1], b[j + 1]);
    st.m = T::from_float(mn);
  }
};

// ---------------------------------------------------------------------------
//  Block-parallel driver (Fig.1/Fig.2): P query vectors pre-loaded, K/V
//  streamed and broadcast to all P blocks; one final division per query.
// ---------------------------------------------------------------------------
template <int P, int D, class T, class Upd>
void fa2_driver(const typename T::storage* Q, const typename T::storage* K,
                const typename T::storage* V, int N, typename T::storage* O,
                Upd upd) {
  AttnState<D, T> st[P];
  for (int b = 0; b < P; ++b) {
    st[b].l = T::from_float(0.0f);
    st[b].m = T::from_float(-1e30f);
    for (int j = 0; j < D; ++j) st[b].o[j] = T::from_float(0.0f);
  }
  for (int i = 0; i < N; ++i) {
    const typename T::storage* k = K + (size_t)i * D;
    const typename T::storage* v = V + (size_t)i * D;
    for (int b = 0; b < P; ++b) {
      const typename T::storage s = dot_qk<D, T>(Q + (size_t)b * D, k);
      upd(st[b], s, v);
    }
  }
  for (int b = 0; b < P; ++b) {
    const float l = T::to_float(st[b].l);              // lazy softmax division
    for (int j = 0; j < D; ++j) {
      O[(size_t)b * D + j] = T::from_float(T::to_float(st[b].o[j]) / l);
    }
  }
}

}  // namespace fa

#endif  // FA_FLASH_ATTN_KERNEL_HPP
