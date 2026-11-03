#!/usr/bin/env bash
# Bounded model checking of the session service of the signed-off chip (hsm_session_props.sv states the properties P1 to P6).
# SymbiYosys with Bitwuzla on hsm_shell.sv of the chip's RTL root (rtl/make_root.sh), revision C define on, with the rejection limit reduced
# from 16 to 2 so that the lock is reachable within the bound and the HMAC outside the shell, so that its timing and digests are free inputs.
#   session_props: P2 to P6, bounded to 48 cycles; the cover task shows that the bound, the seal, the receive and the lock are reachable
#   session_miter: P1, two copies that differ only in K must give identical host responses, bounded to 48 cycles (about an hour)
#   prove tasks:   k-induction, depth 12. They do not close; the result records that.
# usage: run_formal.sh <chip RTL root> <work dir> <result.json>
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${1:?chip RTL root}"; W="${2:?work dir}"; JSON="${3:?result json}"
mkdir -p "$W"
cp "$ROOT/rtl/hsm/hsm_shell.sv" "$HERE/hsm_session_props.sv" "$HERE/session_props.sby" "$HERE/session_miter.sby" "$W/"
cd "$W"
for t in cover bmc prove; do sby -f session_props.sby $t > "props_$t.log" 2>&1; echo "props $t: $(tail -1 "props_$t.log" | cut -c1-90)"; done
sby -f session_miter.sby prove > miter_prove.log 2>&1; echo "miter prove: $(tail -1 miter_prove.log | cut -c1-90)"
sby -f session_miter.sby bmc > miter_bmc.log 2>&1; echo "miter bmc: $(tail -1 miter_bmc.log | cut -c1-90)"
python3 "$HERE/formal_collect.py" "$W" "$JSON"
