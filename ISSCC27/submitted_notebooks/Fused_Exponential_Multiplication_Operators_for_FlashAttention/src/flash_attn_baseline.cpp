// ============================================================================
//  flash_attn_baseline.cpp -- (a) baseline FlashAttention-2 kernel
//
//  Independent exponential hardware unit (8-segment piecewise-linear
//  approximation after range reduction) followed by standard floating-point
//  multiply-accumulate.  Same loop order as the ExpMul version.
// ============================================================================
#include "flash_attn.hpp"

namespace fa {

template <int P, int D, class T>
void fa2_baseline(const typename T::storage* Q, const typename T::storage* K,
                  const typename T::storage* V, int N, typename T::storage* O) {
  fa2_driver<P, D, T>(Q, K, V, N, O, BaselineUpdate<D, T, 8>{});
}

// ---- explicit instantiations: P = 1,4 ; D = 16,32,64 ; FP32 / BF16 --------
#define FA_INST_BASE(P, D, T)                                              \
  template void fa2_baseline<P, D, T>(const T::storage*, const T::storage*, \
                                      const T::storage*, int, T::storage*);

#define FA_INST_ALL_D(T) \
  FA_INST_BASE(1, 16, T) FA_INST_BASE(4, 16, T) \
  FA_INST_BASE(1, 32, T) FA_INST_BASE(4, 32, T) \
  FA_INST_BASE(1, 64, T) FA_INST_BASE(4, 64, T)

FA_INST_ALL_D(FP32Policy)
FA_INST_ALL_D(BF16Policy)

#undef FA_INST_ALL_D
#undef FA_INST_BASE

}  // namespace fa
