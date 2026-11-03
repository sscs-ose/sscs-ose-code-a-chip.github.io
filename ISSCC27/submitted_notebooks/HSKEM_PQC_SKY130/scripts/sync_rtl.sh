#!/usr/bin/env bash
# Copy the audited RTL blocks from the HSKEM tree into this self-contained
# submission and apply the single portability patch needed by Icarus 12.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="${HSKEM_ROOT:-$ROOT/..}"
D="$ROOT/rtl"; mkdir -p "$D"
cp "$SRC/rtl/kyber/kyber_pkg.sv" "$SRC/rtl/kyber/kyber_ntt_engine.sv" \
   "$SRC/rtl/math/barrett_reduce.v" "$SRC/rtl/mlkem512/keccak_f1600_iter.sv" "$D/"
cp "$SRC/asic/rtl/sram_models.sv" "$D/te_sram_models.sv"
(cd "$D" && sha256sum kyber_pkg.sv kyber_ntt_engine.sv barrett_reduce.v \
   keccak_f1600_iter.sv te_sram_models.sv > UPSTREAM_SHA256.txt)
# Icarus does not resolve wildcard-imported package functions at $unit scope;
# an explicit package scope is semantically identical for every other tool.
sed -i 's/kyber_zeta(k)/kyber_pkg::kyber_zeta(k)/' "$D/kyber_ntt_engine.sv"
diff <(cd "$SRC/rtl/kyber" && cat kyber_ntt_engine.sv) "$D/kyber_ntt_engine.sv" > "$D/PORTABILITY_PATCH.diff" || true
echo "synced from $SRC"
