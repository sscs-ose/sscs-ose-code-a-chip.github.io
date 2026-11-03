#!/usr/bin/env bash
# Build the RTL of HSKEM-2 revision C (the synthesized root of the signed-off chip) from the published sources:
#   1. hskem_rtl/ (the published HSKEM sources, public placeholder credential) plus the files of this folder that
#      hskem_rtl/ does not carry: the ASIC wrapper that binds the 18 SRAM macros (asic/rtl/) and the board top (rtl/);
#   2. scripts/make_packed_system.py: the redesigned system of Section 8 with the revision-B edits (scripts/t3_*_edit.py),
#      every one behind its TRUSTEDGE_T3_* define;
#   3. the two chip edits: the NTT store bound to its 24 x 128 macro and the one-round Keccak as the core's default;
#   4. the session edits of revision C (revc_edit.py) and their testbench checks (revc_tb_edit.py), every one
#      behind TRUSTEDGE_REVC.
# The chip was synthesized from this root with the defines of flow/chip_rev_c/README.md.
# usage: flow/chip_rev_c/rtl/make_root.sh <out dir>        (out dir gets hskem_full/ and root/)
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; CAC="$(cd "$HERE/../../.." && pwd)"
OUT="${1:?out dir}"
if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then echo "refusing to overwrite the non-empty $OUT"; exit 2; fi
mkdir -p "$OUT"
cp -r "$CAC/hskem_rtl" "$OUT/hskem_full"; rm -f "$OUT/hskem_full/PUBLICATION_PATCH.diff" "$OUT/hskem_full/UPSTREAM_SHA256.txt"
cp "$HERE"/asic/rtl/*.sv "$OUT/hskem_full/asic/rtl/"; cp "$HERE"/rtl/*.v "$HERE"/rtl/files.f "$OUT/hskem_full/rtl/"
python3 "$CAC/scripts/make_packed_system.py" "$OUT/hskem_full" "$OUT/root" "$CAC/rtl" "$OUT/root.diff"
cp "$HERE/rtl/kyber/ntt_pair_sram_chip.sv" "$OUT/root/rtl/kyber/ntt_pair_sram_chip.sv"
sed -i "s/    parameter bit ASIC_KECCAK_SERIAL_ROUND = 1'b1,/    parameter bit ASIC_KECCAK_SERIAL_ROUND = 1'b0,   \/\/ the one-round Keccak core/" \
    "$OUT/root/asic/rtl/trustedge_asic_core.sv"
python3 "$HERE/revc_edit.py" "$OUT/root"
python3 "$HERE/revc_tb_edit.py" "$OUT/root"   # the system testbench's rev C checks, also behind TRUSTEDGE_REVC
echo "revision C root: $OUT/root"
# the synthesized root of the chip, file by file (results/fullchip/rev_c/root_sha256.txt)
(cd "$OUT/root" && sha256sum -c --quiet "$CAC/results/fullchip/rev_c/root_sha256.txt") && echo "ROOT_MATCHES_CHIP: every file identical to the synthesized root"
