#pragma once
#include <vector>
#include <string>
#include <cstdint>

enum class GateName { AND, NAND, OR, XOR, XNOR, INV, CONST0, CONST1 };

std::string gname(GateName g);
int         arity_in(GateName g);
int         arity_out(GateName g);
int         gate_mos(GateName g);

struct Ref {
    bool is_input;
    int  idx;
    int  slot;
};

struct Node {
    GateName           gate;
    std::vector<Ref>   inputs;
};

struct Circuit {
    std::vector<Node>  nodes;
    std::vector<Ref>   outputs;

    std::vector<int> out_arity() const;
};

long long circuit_area_mos(const Circuit& c);

std::vector<std::vector<uint8_t>> eval_gate(GateName name, const std::vector<std::vector<uint8_t>>& ins);