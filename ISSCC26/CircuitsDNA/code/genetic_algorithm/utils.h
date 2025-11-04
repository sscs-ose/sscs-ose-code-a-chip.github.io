#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <random>
#include <cstdint>
#include "gate.h"

extern std::mt19937 rng;

int  rint(int l, int r, std::mt19937& eng);
int  rint(int l, int r);                    

std::string trim(const std::string& s);
std::string strip_tail_semicolon(std::string s);
int  safe_stoi_anywhere(const std::string& s);
int  index_in_brackets(const std::string& s);

Ref  ref_from_token(const std::string& tok,
                    const std::unordered_map<std::string, Ref>& sym);

template<class T>
inline const T& choice(const std::vector<T>& v) {
    return v[rint(0, static_cast<int>(v.size()) - 1)];
}
