#!/usr/bin/env bash
# Build the C++ reference models with g++ (Linux build host).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$root/build"
CXX="${CXX:-g++}"
FLAGS="-std=c++17 -O2 -Wall -Wextra -Wno-unused-parameter -I$root/src"

$CXX $FLAGS -o "$root/build/expmul" "$root/src/expmul.cpp"
$CXX $FLAGS -o "$root/build/tb" "$root/src/tb.cpp" \
     "$root/src/flash_attn_baseline.cpp" "$root/src/flash_attn_expmul.cpp"
echo "built $root/build/expmul, $root/build/tb"
