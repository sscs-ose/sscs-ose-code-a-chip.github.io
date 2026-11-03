#!/usr/bin/env bash
# The session testbench of revision C (tb_revc_session.sv, next to this script) on a root built by rtl/make_root.sh,
# without the define (revision B's behaviour) or with -DTRUSTEDGE_REVC (revision C's); check_seal_log.py then recomputes
# every sealed tag with Python's hmac module. Takes seconds; with the define the log ends in
# "TB_REVC_SESSION_RESULT: ALL PASS (16 checks, 0 errors)", as results/fullchip/rev_c/tb_revc_session.log.
# usage: flow/chip_rev_c/revc/run_session_tb.sh <root dir> [-DTRUSTEDGE_REVC]     (Icarus Verilog of the OSS CAD Suite)
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$(cd "${1:?root dir, e.g. <out>/root of rtl/make_root.sh}" && pwd)"; shift
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
iverilog -g2012 "$@" -s tb_revc_session -o "$W/tb.vvp" "$R/rtl/hsm/sha256_compress.sv" \
  "$R/rtl/hsm/hmac_sha256_fixed.sv" "$R/rtl/hsm/hsm_shell.sv" "$HERE/tb_revc_session.sv" 2>&1 | grep -v sorry | head -20
vvp -n "$W/tb.vvp" > "$W/session.log" 2>&1
grep -E "PASS|FAIL|RESULT" "$W/session.log"
python3 "$HERE/check_seal_log.py" "$W/session.log"
