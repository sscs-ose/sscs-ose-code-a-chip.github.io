#include "utils.h"
#include <string>
#include <vector>
#include <unordered_map>
#include <random>
#include <cctype>
#include <stdexcept>
#include <cstdint>

extern std::mt19937 rng;

int rint(int l, int r, std::mt19937& eng) {
    if (r < l) r = l;
    std::uniform_int_distribution<int> d(l, r);
    return d(eng);
}

int rint(int l, int r) {
    return rint(l, r, rng);
}

std::string trim(const std::string& s) {
    size_t i = 0, j = s.size();
    while (i < j && std::isspace(static_cast<unsigned char>(s[i]))) ++i;
    while (j > i && std::isspace(static_cast<unsigned char>(s[j - 1]))) --j;
    return s.substr(i, j - i);
}

std::string strip_tail_semicolon(std::string s) {
    while (!s.empty() && (s.back() == ';')) s.pop_back();
    return s;
}

int safe_stoi_anywhere(const std::string& s) {
    size_t i = 0;
    while (i < s.size() &&
           !(s[i] == '+' || s[i] == '-' || std::isdigit(static_cast<unsigned char>(s[i])))) {
        ++i;
    }
    if (i >= s.size()) throw std::invalid_argument("no digits: '" + s + "'");
    size_t j = i + 1;
    while (j < s.size() && std::isdigit(static_cast<unsigned char>(s[j]))) ++j;
    return std::stoi(s.substr(i, j - i));
}

int index_in_brackets(const std::string& s) {
    size_t l = s.find('[');
    size_t r = s.find(']', l == std::string::npos ? 0 : l + 1);
    if (l == std::string::npos || r == std::string::npos || r <= l + 1)
        throw std::invalid_argument("bad bracket token: '" + s + "'");
    return safe_stoi_anywhere(s.substr(l + 1, r - (l + 1)));
}

Ref ref_from_token(const std::string& tok,
                          const std::unordered_map<std::string, Ref>& sym) {
    if (tok.size() >= 2 && tok[0] == 'A' && tok[1] == '[') {
        int i = index_in_brackets(tok); if (i < 0 || i > 7) throw std::invalid_argument("A index");
        return Ref{true, i, 0};
    } else if (tok.size() >= 2 && tok[0] == 'B' && tok[1] == '[') {
        int i = index_in_brackets(tok); if (i < 0 || i > 7) throw std::invalid_argument("B index");
        return Ref{true, 8 + i, 0};
    } else {
        auto it = sym.find(tok);
        if (it == sym.end()) throw std::invalid_argument("unknown net: " + tok);
        return it->second;
    }
}
