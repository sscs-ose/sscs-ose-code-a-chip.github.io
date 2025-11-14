#include "gate.h"
#include "main.h"
#include <unordered_map>
#include <stdexcept>

using namespace std;

static const unordered_map<GateName,int> ARITY_IN_tbl = {
    {GateName::AND,2},{GateName::NAND,2},{GateName::OR,2},{GateName::XOR,2},{GateName::XNOR,2},
    {GateName::INV,1},{GateName::CONST0,0},{GateName::CONST1,0}
};
static const unordered_map<GateName,int> ARITY_OUT_tbl = {
    {GateName::AND,1},{GateName::NAND,1},{GateName::OR,1},{GateName::XOR,1},{GateName::XNOR,1},
    {GateName::INV,1},{GateName::CONST0,1},{GateName::CONST1,1}
};
static const unordered_map<GateName,int> GATE_MOS_tbl = {
    {GateName::INV,   2},
    {GateName::NAND,  4},
    {GateName::AND,   6},
    {GateName::OR,    6},
    {GateName::XOR,  10},
    {GateName::XNOR, 10},
    {GateName::CONST0,0},
    {GateName::CONST1,0}
};

string gname(GateName g){
    switch(g){
        case GateName::AND:   return "AND";
        case GateName::NAND:  return "NAND";
        case GateName::OR:    return "OR";
        case GateName::XOR:   return "XOR";
        case GateName::XNOR:  return "XNOR";
        case GateName::INV:   return "INV";
        case GateName::CONST0:return "CONST0";
        case GateName::CONST1:return "CONST1";
    }
    return "?";
}

int arity_in(GateName g) {
    return ARITY_IN_tbl.at(g);
}
int arity_out(GateName g) {
    return ARITY_OUT_tbl.at(g);
}
int gate_mos(GateName g){
    auto it = GATE_MOS_tbl.find(g);
    return (it == GATE_MOS_tbl.end()) ? 6 : it->second;
}

std::vector<int> Circuit::out_arity() const {
    std::vector<int> v; v.reserve(nodes.size());
    for (const auto& n : nodes) v.push_back(arity_out(n.gate));
    return v;
}

long long circuit_area_mos(const Circuit& c){
    long long a=0;
    for(const auto& n: c.nodes) a += gate_mos(n.gate);
    return a;
}

std::vector<std::vector<uint8_t>> eval_gate(GateName name, const std::vector<std::vector<uint8_t>>& ins){
    std::vector<std::vector<uint8_t>> outs;
    switch(name){
        case GateName::AND:{
            outs.assign(1, std::vector<uint8_t>(B,0));
            for(int i=0;i<B;++i) outs[0][i] = (ins[0][i]&1)&(ins[1][i]&1);
            return outs;
        }
        case GateName::NAND:{
            outs.assign(1, std::vector<uint8_t>(B,0));
            for(int i=0;i<B;++i){ uint8_t t=(ins[0][i]&1)&(ins[1][i]&1); outs[0][i]=(uint8_t)((~t)&1); }
            return outs;
        }
        case GateName::OR:{
            outs.assign(1, std::vector<uint8_t>(B,0));
            for(int i=0;i<B;++i) outs[0][i] = (ins[0][i]|ins[1][i])&1;
            return outs;
        }
        case GateName::XOR:{
            outs.assign(1, std::vector<uint8_t>(B,0));
            for(int i=0;i<B;++i) outs[0][i] = (ins[0][i]^ins[1][i])&1;
            return outs;
        }
        case GateName::XNOR:{
            outs.assign(1, std::vector<uint8_t>(B,0));
            for(int i=0;i<B;++i) outs[0][i] = (uint8_t)((~(ins[0][i]^ins[1][i]))&1);
            return outs;
        }
        case GateName::INV:{
            outs.assign(1, std::vector<uint8_t>(B,0));
            for(int i=0;i<B;++i) outs[0][i] = (uint8_t)((~ins[0][i])&1);
            return outs;
        }
        case GateName::CONST0:{ outs.assign(1, std::vector<uint8_t>(B,0)); return outs; }
        case GateName::CONST1:{ outs.assign(1, std::vector<uint8_t>(B,1)); return outs; }
    }
    return outs;
}