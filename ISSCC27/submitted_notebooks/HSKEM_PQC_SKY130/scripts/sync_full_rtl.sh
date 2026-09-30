#!/usr/bin/env bash
# Copy the complete HSKEM RTL needed by the full-system testbench into
# hskem_rtl/, so that Section 8 can be reproduced from the submission alone.
#
# One deliberate change is applied to the published copy: the synthesis-time
# provisioning test credential in hsm_shell.sv is replaced by a public
# placeholder (SHA-256 of an explicit label), because the original value is
# still used by the author's demonstration board and firmware. The change is
# recorded in hskem_rtl/PUBLICATION_PATCH.diff; the testbench does not depend
# on the value.
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="${HSKEM_ROOT:-$ROOT/..}"; DST="$ROOT/hskem_rtl"
rm -rf "$DST"; mkdir -p "$DST"
FILES=(rtl/math/barrett_reduce.v rtl/spi/crc16_ccitt.v rtl/spi/trustedge_frame.v rtl/spi/spi_slave.v
  rtl/puf/trng.v rtl/puf/c2_shake_drbg.sv rtl/puf/ropuf_core.v rtl/puf/ro_ring_oscillator.v
  rtl/puf/puf_char_engine.sv rtl/puf/puf_char_service.sv rtl/puf/puf_secded_sketch.sv
  rtl/puf/puf_root_service.sv rtl/puf/puf_vault_service.sv rtl/puf/rep_codec.v
  rtl/puf/fuzzy_extractor.v rtl/puf/puf_top.v rtl/kyber/kyber_pkg.sv rtl/kyber/kyber_montgomery.v
  rtl/kyber/kyber_ntt_engine.sv rtl/kyber/kyber_poly_mul.v rtl/kyber/kyber_ntt_selftest.sv
  rtl/kyber/kyber_params.vh rtl/kyber/kyber_zetas.vh
  rtl/mlkem512/mlkem512_pkg.sv rtl/mlkem512/mlkem512_compress.sv rtl/mlkem512/mlkem512_cbd.sv
  rtl/mlkem512/mlkem512_bytecodec.sv rtl/mlkem512/mlkem512_partial_selftest.sv
  rtl/mlkem512/mlkem512_polyvec_ntt_selftest.sv rtl/mlkem512/mlkem512_runtime_selftest.sv
  rtl/mlkem512/keccak_f1600_iter.sv rtl/mlkem512/keccak_sponge_stream.sv
  rtl/mlkem512/mlkem512_keccak_selftest.sv rtl/mlkem512/mlkem512_matrix_mac_selftest.sv
  rtl/mlkem512/mlkem512_ciphertext_codec.sv rtl/mlkem512/mlkem512_kpke_encrypt_selftest.sv
  rtl/mlkem512/mlkem512_partial_kem_selftests.sv rtl/ota/ota_gate.v rtl/hsm/sha256_compress.sv
  rtl/hsm/hmac_sha256_fixed.sv rtl/hsm/aes256_encrypt_block.sv rtl/hsm/sdm_chipid_client.sv
  rtl/hsm/sdm_crypto_axi_ram.sv rtl/hsm/hsm_shell.sv asic/rtl/sram_models.sv
  rtl/spi/spi_command_bridge.v rtl/trustedge_top.v sim/tb/tb_trustedge_spi.sv)
for f in "${FILES[@]}"; do mkdir -p "$DST/$(dirname "$f")"; cp "$SRC/$f" "$DST/$f"; done
(cd "$SRC" && sha256sum "${FILES[@]}") > "$DST/UPSTREAM_SHA256.txt"

# Replace whatever value PROVISION_AUTH_TEST_KEY has; the original never appears in this script.
KEY_NEW="$(printf 'HSKEM public placeholder provisioning key - not used by any device' | sha256sum | cut -c1-64 | tr a-f A-F)"
python3 - "$DST/rtl/hsm/hsm_shell.sv" "$KEY_NEW" <<'PY'
import re, sys
p, new = sys.argv[1], sys.argv[2]
s = open(p, newline="").read()                  # keep the original line endings
s2, n = re.subn(r"(PROVISION_AUTH_TEST_KEY\s*=\s*256'h)[0-9A-Fa-f_]+", lambda m: m.group(1) + new, s)
assert n == 1, "PROVISION_AUTH_TEST_KEY not found exactly once"
open(p, "w", newline="").write(s2)
PY
# The full-system testbench carries two precomputed provisioning tags,
# HMAC-SHA256(key, "TEP1" || chip_id || counter || request)[0:16]; recompute them
# for the placeholder key so that the published testbench passes unchanged.
python3 - "$DST/sim/tb/tb_trustedge_spi.sv" "$KEY_NEW" <<'PY'
import hashlib, hmac, sys
p, key = sys.argv[1], bytes.fromhex(sys.argv[2])
chip = bytes.fromhex("0123456789ABCDEF")
request = bytes.fromhex("53494731" "00" "05" "21" "01" "0123456789ABCDEF")
def tag(counter):
    msg = b"TEP1" + chip + counter.to_bytes(4, "big") + request
    return hmac.new(key, msg, hashlib.sha256).digest()[:16].hex().upper()
s = open(p, newline="").read()
for counter, old in ((1, "71ACDD99D459A9E4EB103DA487E64EDA"), (2, "4E0F947264A360AB279D188A2146EF7B")):
    assert old in s, f"tag for counter {counter} not found"
    s = s.replace(old, tag(counter))
open(p, "w", newline="").write(s)
PY
{ diff "$SRC/rtl/hsm/hsm_shell.sv" "$DST/rtl/hsm/hsm_shell.sv" \
    | sed -E "/^</ s/256'h[0-9A-Fa-f_]+/256'h<withheld: demo-board test credential>/"
  echo "--- sim/tb/tb_trustedge_spi.sv: provisioning tags recomputed for the placeholder key"
  diff "$SRC/sim/tb/tb_trustedge_spi.sv" "$DST/sim/tb/tb_trustedge_spi.sv"
} > "$DST/PUBLICATION_PATCH.diff" || true
echo "copied ${#FILES[@]} files to $DST"
cat "$DST/PUBLICATION_PATCH.diff"
