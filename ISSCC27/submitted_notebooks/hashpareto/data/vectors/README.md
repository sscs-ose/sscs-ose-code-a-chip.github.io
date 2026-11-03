# SHA-256 test vectors

Canonical correctness vectors for HashPareto, used by the Phase 1 verification
harness and the Phase 4 notebook.

| File | Contents |
|---|---|
| `nist_sha256.json` | FIPS 180-4 example messages and their expected 256-bit digests |

## Provenance

The vectors are the published examples from **FIPS PUB 180-4, Secure Hash
Standard (SHS)** (Appendix A/B), plus the 26-byte alphabet message already used
by the vendored `nano_hash` top-level testbench. They are not derived from this
project's RTL, so they serve as an independent golden reference.

## Format

Each entry provides the message as ASCII and/or hex and the expected digest as
32 big-endian bytes (`digest_hex`), matching the SHA-256 word ordering used by
the RTL (`digest[255:224]` is emitted first). The `nist-million-a` vector is
described with `message_repeat` rather than a multi-megabyte string.

These vectors are intended for bit-exact comparison against generated variants;
the existing SystemVerilog golden suite under `rtl/original/tb/` remains the
cycle/interface-level check.
