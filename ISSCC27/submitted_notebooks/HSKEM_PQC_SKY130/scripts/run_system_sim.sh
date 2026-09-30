#!/usr/bin/env bash
# Full-system HSKEM simulation (tb_trustedge_spi) with Icarus Verilog, in the
# FPGA configuration or the ASIC configuration (single-port SRAM contract +
# row-serialized Keccak). The testbench measures the internal Decaps busy
# interval, which the 16-bit hardware counter cannot report.
# usage: run_system_sim.sh fpga|asic|sram_only|keccak_only   (needs the HSKEM source tree: HSKEM_ROOT)
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
CFG=${1:?fpga|asic}
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# the published copy (hskem_rtl/, see sync_full_rtl.sh) unless HSKEM_ROOT points elsewhere
if [ -n "${HSKEM_ROOT:-}" ]; then SRC="$HSKEM_ROOT"; elif [ -d "$ROOT/hskem_rtl" ]; then SRC="$ROOT/hskem_rtl"; else SRC="$ROOT/.."; fi
OUTTAG="${CAC_SIM_TAG:-}"
OUT="$ROOT/results/system_sim"; mkdir -p "$OUT"
# fpga: dual-port NTT store + one-round Keccak; asic: both ASIC choices;
# sram_only / keccak_only isolate the two decisions.
case $CFG in
  fpga)        DEFS=();;
  asic)        DEFS=(-DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_KECCAK_SERIAL_ROUND
                     -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS);;
  sram_only)   DEFS=(-DTRUSTEDGE_ASIC_SRAM -DTRUSTEDGE_ASIC_RESET_BRANCHES -DTRUSTEDGE_ASIC_SKY130_RESET_CELLS);;
  keccak_only) DEFS=(-DTRUSTEDGE_ASIC_KECCAK_SERIAL_ROUND);;
  *) echo "unknown config $CFG"; exit 2;;
esac
F=(rtl/math/barrett_reduce.v rtl/spi/crc16_ccitt.v rtl/spi/trustedge_frame.v rtl/spi/spi_slave.v
   rtl/puf/trng.v rtl/puf/c2_shake_drbg.sv rtl/puf/ropuf_core.v rtl/puf/ro_ring_oscillator.v
   rtl/puf/puf_char_engine.sv rtl/puf/puf_char_service.sv rtl/puf/puf_secded_sketch.sv
   rtl/puf/puf_root_service.sv rtl/puf/puf_vault_service.sv rtl/puf/rep_codec.v
   rtl/puf/fuzzy_extractor.v rtl/puf/puf_top.v rtl/kyber/kyber_pkg.sv rtl/kyber/kyber_montgomery.v
   rtl/kyber/kyber_ntt_engine.sv rtl/kyber/kyber_poly_mul.v rtl/kyber/kyber_ntt_selftest.sv
   rtl/mlkem512/mlkem512_pkg.sv rtl/mlkem512/mlkem512_compress.sv rtl/mlkem512/mlkem512_cbd.sv
   rtl/mlkem512/mlkem512_bytecodec.sv rtl/mlkem512/mlkem512_partial_selftest.sv
   rtl/mlkem512/mlkem512_polyvec_ntt_selftest.sv rtl/mlkem512/mlkem512_runtime_selftest.sv
   rtl/mlkem512/keccak_f1600_iter.sv rtl/mlkem512/keccak_sponge_stream.sv
   rtl/mlkem512/mlkem512_keccak_selftest.sv rtl/mlkem512/mlkem512_matrix_mac_selftest.sv
   rtl/mlkem512/mlkem512_ciphertext_codec.sv rtl/mlkem512/mlkem512_kpke_encrypt_selftest.sv
   rtl/mlkem512/mlkem512_partial_kem_selftests.sv rtl/ota/ota_gate.v rtl/hsm/sha256_compress.sv
   rtl/hsm/hmac_sha256_fixed.sv rtl/hsm/aes256_encrypt_block.sv rtl/hsm/sdm_chipid_client.sv
   rtl/hsm/sdm_crypto_axi_ram.sv rtl/hsm/hsm_shell.sv asic/rtl/sram_models.sv
   rtl/spi/spi_command_bridge.v rtl/trustedge_top.v "${CAC_TB:-sim/tb/tb_trustedge_spi.sv}")
# CAC_PROFILE=1 adds tb/decaps_profiler.sv as a second top level (read-only hierarchical probes)
PROF=(); [ "${CAC_PROFILE:-0}" = 1 ] && PROF=(-s decaps_profiler "$ROOT/tb/decaps_profiler.sv")
cd "$SRC"
V="tb_${CFG}${OUTTAG}.vvp"; L="tb_trustedge_spi_${CFG}${OUTTAG}.log"
# CAC_TB / CAC_EXTRA_DEFS / CAC_RUN_DIR: a derived testbench, e.g. scripts/acvp_rtl_keygen.py
[ -n "${CAC_EXTRA_DEFS:-}" ] && DEFS+=(${CAC_EXTRA_DEFS})
iverilog -g2012 -I rtl/kyber "${DEFS[@]}" -s tb_trustedge_spi -o "$OUT/$V" "${F[@]}" "${PROF[@]}" 2>&1 | tail -20
[ "${COMPILE_ONLY:-0}" = 1 ] && exit 0
( cd "${CAC_RUN_DIR:-$OUT}" && time vvp -n "$OUT/$V" > "$OUT/$L" 2>&1 ) || true
rm -f "$OUT/$V"
grep -E "U1 Decaps|FAIL|errors|PASS runtime_mlkem|TB_TRUSTEDGE_SPI_RESULT|PROFILE|ACVP_KEYGEN_RESULT" "$OUT/$L" | head -20
