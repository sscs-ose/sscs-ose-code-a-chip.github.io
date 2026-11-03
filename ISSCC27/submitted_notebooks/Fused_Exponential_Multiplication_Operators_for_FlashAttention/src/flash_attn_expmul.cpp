// ============================================================================
//  flash_attn_expmul.cpp -- (b) FlashAttention-2 with fused ExpMul operators
//
//  Alg.4 of the paper:
//      sigma*_i = ExpMul(m_{i-1}-m_i, sigma*_{i-1}) + ExpMul(s_i-m_i, v*_i)
//  i.e. the two exponentials *and* the two vector multiplications of the
//  baseline are replaced by two ExpMul operators (one shared L per operator,
//  D+1 integer exponent updates).
//
//  variant 0 : Algorithm 3 as written (exponent-field subtraction only)
//  variant 1 : released implementation (fractional residual folded into the
//              mantissa, one extra integer add)
// ============================================================================
#include "flash_attn.hpp"

namespace fa {

template <int P, int D, class T>
void fa2_expmul(const typename T::storage* Q, const typename T::storage* K,
                const typename T::storage* V, int N, typename T::storage* O,
                int variant) {
  if (variant == 0) {
    fa2_driver<P, D, T>(Q, K, V, N, O, ExpMulUpdate<D, T, 0>{});
  } else {
    fa2_driver<P, D, T>(Q, K, V, N, O, ExpMulUpdate<D, T, 1>{});
  }
}

#define FA_INST_EXP(P, D, T)                                              \
  template void fa2_expmul<P, D, T>(const T::storage*, const T::storage*, \
                                    const T::storage*, int, T::storage*, int);

#define FA_INST_ALL_D(T) \
  FA_INST_EXP(1, 16, T) FA_INST_EXP(4, 16, T) \
  FA_INST_EXP(1, 32, T) FA_INST_EXP(4, 32, T) \
  FA_INST_EXP(1, 64, T) FA_INST_EXP(4, 64, T)

FA_INST_ALL_D(FP32Policy)
FA_INST_ALL_D(BF16Policy)

#undef FA_INST_ALL_D
#undef FA_INST_EXP

}  // namespace fa
