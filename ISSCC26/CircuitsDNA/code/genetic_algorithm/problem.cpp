#include "problem.h"
using namespace std;

// ============= Unsigned 8-bit × 8-bit =============
Problem build_problem_unsigned() {
    Problem p;
    p.inputs.resize(B);
    p.targets.resize(B);
    int idx = 0;
    int max_abs = 0;

    for (int a = 0; a < 256; ++a) {
        for (int b = 0; b < 256; ++b) {
            array<uint8_t, NUM_IN> xi{};
            for (int i = 0; i < 8; ++i) xi[i]     = getb((uint32_t)a, i);
            for (int i = 0; i < 8; ++i) xi[8 + i] = getb((uint32_t)b, i);
            p.inputs[idx] = xi;

            uint32_t prod = (uint32_t)a * (uint32_t)b;
            array<uint8_t, NUM_OUT> yi{};
            for (int i = 0; i < 16; ++i) yi[i] = getb(prod, i);
            p.targets[idx] = yi;

            max_abs = max(max_abs, (int)prod);
            ++idx;
        }
    }

    p.max_true_abs = max(1, max_abs);
    return p;
}

// ============= Signed 8-bit × 8-bit =============
Problem build_problem_signed() {
    Problem p;
    p.inputs.resize(B);
    p.targets.resize(B);

    int idx = 0;
    int max_abs = 0;

    for (int a = -128; a <= 127; ++a) {
        const uint8_t au = static_cast<uint8_t>(static_cast<int8_t>(a));
        for (int b = -128; b <= 127; ++b) {
            const uint8_t bu = static_cast<uint8_t>(static_cast<int8_t>(b));

            array<uint8_t, NUM_IN> xi{};
            for (int i = 0; i < 8; ++i) xi[i]     = getb(au, i);
            for (int i = 0; i < 8; ++i) xi[8 + i] = getb(bu, i);
            p.inputs[idx] = xi;

            const int16_t prod  = static_cast<int16_t>(static_cast<int8_t>(a)) *
                                  static_cast<int16_t>(static_cast<int8_t>(b));
            const uint16_t prou = static_cast<uint16_t>(prod);

            array<uint8_t, NUM_OUT> yi{};
            for (int i = 0; i < 16; ++i) yi[i] = getb(prou, i);
            p.targets[idx] = yi;

            int mag = (prod >= 0) ? prod : -prod;
            max_abs = max(max_abs, mag);
            ++idx;
        }
    }

    p.max_true_abs = max(1, max_abs);
    return p;
}
