#pragma once
#include <vector>
#include <array>
#include <cstdint>
#include "main.h"

struct Problem {
    std::vector<std::array<uint8_t, NUM_IN>>  inputs;
    std::vector<std::array<uint8_t, NUM_OUT>> targets;
    int max_true_abs;
};

Problem build_problem_unsigned();
Problem build_problem_signed();

static inline uint8_t getb(uint32_t x, int i) { return (x >> i) & 1u; }
static inline uint16_t setb(uint16_t w, int i, uint8_t b){ if(b&1) return (uint16_t)(w | (uint16_t(1u)<<i)); return (uint16_t)(w & ~(uint16_t(1u)<<i)); }