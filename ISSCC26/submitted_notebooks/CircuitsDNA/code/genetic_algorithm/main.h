#pragma once
#include <bits/stdc++.h>
#include "gate.h"

inline constexpr int NUM_IN  = 16;          // A0..A7, B0..B7
inline constexpr int NUM_OUT = 16;          // OUT0[0..15]
inline constexpr int B       = 256 * 256;   // 65536 patterns

extern bool         LOAD_FROM_FILE;
extern bool         SIGNED_MULT;
extern std::string  NETLIST_FILE;
extern int          GENERATIONS;
extern int          POP_SIZE;
extern double       TOP_K_RATIO;

extern double         EPS_START;
extern double         EPS_END;
extern double         EPS_TAU;
extern double         eps_th;
extern uint32_t SEED;

extern std::array<double,6> MUT_WEIGHTS;

extern const double   HUGE_PENALTY;
extern const bool     USE_HEAT_BIASED;


extern int            MAX_TRUE_ABS;
extern std::mt19937   rng;

inline std::vector<std::array<uint8_t, NUM_IN>>  ALL_INPUTS;
inline std::vector<std::array<uint8_t, NUM_OUT>> ALL_TARGETS;

extern std::string logfile;

struct ErrorStats{
    double NMED=0, MRE=0, sMAPE=0, ER=0, WCE=0;
};


Circuit prune_inactive(const Circuit& c);
Circuit random_initial_circuit(int min_nodes=2,int max_nodes=6);
