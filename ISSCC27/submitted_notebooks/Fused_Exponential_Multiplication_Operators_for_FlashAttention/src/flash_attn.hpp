// ============================================================================
//  flash_attn.hpp -- public entry points of the two FlashAttention-2 kernels
//
//  Both are instantiated for P in {1,4}, D in {16,32,64} and T in
//  {FP32Policy, BF16Policy} (see the .cpp files).  They share fa2_driver()
//  from flash_attn_kernel.hpp, i.e. the exact same FlashAttention-2 order.
// ============================================================================
#ifndef FA_FLASH_ATTN_HPP
#define FA_FLASH_ATTN_HPP

#include "flash_attn_kernel.hpp"

namespace fa {

// (a) baseline: independent PWL exp unit + standard FP multiply
template <int P, int D, class T>
void fa2_baseline(const typename T::storage* Q, const typename T::storage* K,
                  const typename T::storage* V, int N, typename T::storage* O);

// (b) ExpMul version; variant 0 = Alg.3 exponent-only, 1 = mantissa-interp
template <int P, int D, class T>
void fa2_expmul(const typename T::storage* Q, const typename T::storage* K,
                const typename T::storage* V, int N, typename T::storage* O,
                int variant);

}  // namespace fa

#endif  // FA_FLASH_ATTN_HPP
