#!/usr/bin/env bash
# ACVP encapsulation/decapsulation of the RTL of the signed-off chip (HSKEM-2 revision C), byte for byte against the
# golden model (scripts/acvp_rtl_encdec.py). Builds the revision-C RTL from the published sources
# (flow/chip_rev_c/rtl/make_root.sh), adds the case loop to a copy of the full-system testbench, simulates it with
# Icarus Verilog (OSS CAD Suite) in the chip's configuration and writes results/acvp_rtl/encdec_rev_c.json.
# About ten minutes for 25 cases.   usage: scripts/acvp_rtl_encdec.sh [N cases, default 25]
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; N="${1:-25}"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT; mkdir -p "$W/run"
bash "$ROOT/flow/chip_rev_c/rtl/make_root.sh" "$W/rtl" > /dev/null
SRC="$W/rtl/root"
python3 "$ROOT/scripts/acvp_rtl_encdec.py" prepare "$W/run" "$N"
python3 "$ROOT/scripts/acvp_rtl_encdec.py" patch "$SRC/sim/tb/tb_trustedge_spi.sv" "$N"
# the chip's configuration: SRAM store and the reset branches of the ASIC, milestone H (Section 8), the two (chip)
# defines of revision A, the fourteen of revision B and the session changes of revision C (flow/chip_rev_c/README.md)
DEFS="-DFUNCTIONAL -DUNIT_DELAY=#0 -DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS"
for d in PACKED_NTT HASH_OVERLAP STREAM_IO FAST_BASEMUL FAST_FEED STREAM_OUT FOLD_READBACK PREFETCH TIGHT_LOOPS FAST_CHECK \
         FAST_Y PACKED2 FAST_PRF FUSED_CMP FAST_READ PIPE_CHECK PAIR_PORT DEFER_J PIPE_MAC FAST_HASH DEC_STREAM SEG_CHECK \
         BG_PRF STREAM_INV STREAM_FWD PRF_TO_NTT STREAM_DEC_INV PRF_FINE_HOLD POLY_GUARD PMAC_RETIME SO_PIPE; do
  DEFS="$DEFS -DTRUSTEDGE_$d"; done
for d in MAC_DEEP MM_PIPE CRC_SERIAL BARRETT_1C SA_PIPE PMAC_RAW CODEC_RETIME MSG_PIPE PP_EARLY LOAD_PIPE MARGIN MUL_SEL \
         SEL_REP EK_PREF; do
  DEFS="$DEFS -DTRUSTEDGE_T3_$d"; done
DEFS="$DEFS -DTRUSTEDGE_REVC"
F=$(sed -n '/^F=(/,/)$/p' "$ROOT/scripts/run_system_sim.sh" | tr -d '()"' | sed 's/^F=//; s#\${CAC_TB:-sim/tb/tb_trustedge_spi.sv}#sim/tb/tb_trustedge_spi.sv#')
F="$F rtl/kyber/barrett_reduce_1c.v rtl/kyber/kyber_ntt_engine_packed.sv rtl/kyber/kyber_ntt_engine_packed2.sv"
( cd "$SRC" && iverilog -g2012 -I rtl/kyber $DEFS -DCAC_ACVP_ENCDEC -s tb_trustedge_spi -o "$W/tb.vvp" $F ) > "$W/compile.log" 2>&1 \
  || { grep -m5 -i error "$W/compile.log"; exit 3; }
( cd "$W/run" && vvp -n "$W/tb.vvp" > "$W/sim.log" 2>&1 ) || true
mkdir -p "$ROOT/results/acvp_rtl"
python3 "$ROOT/scripts/acvp_rtl_encdec.py" check "$W/run" "$W/sim.log" "$ROOT/results/acvp_rtl/encdec_rev_c.json" "$N"
