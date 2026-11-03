# Vendored reference RTL: nano_hash

This directory is a **read-only, unmodified** copy of the `nano_hash` SHA-256
core and its verification environment.

| Field | Value |
|---|---|
| Source | https://github.com/chijindumu/nano_hash |
| Vendored on | 2026-10-09 |
| License | Apache-2.0 (see repository-root `LICENSE` and `NOTICE`) |
| Contents | `rtl/core` (SHA-256 datapath), `rtl/board` (Basys3 UART demo), `tb` (unit + top testbenches and `memory_files` test vectors), `constraints` (Basys3 XDC), `NANO_HASH_README.md` (upstream README) |

## Why it is here

- **Attribution**: the original design is retained verbatim so its provenance and
  license are unambiguous.
- **Reference / golden model**: Phase 1 refactors this core into a parameterized
  generator and must stay bit-exact against it. The testbenches and
  `tb/memory_files/` vectors are reused as the golden correctness suite.
- **Interface freeze**: `rtl/core/sha_256_top.sv` defines the `sha_top` AXI4-Stream
  interface that every generated variant must preserve.

## Do not edit

Changes for HashPareto live under `rtl/generated/` (Phase 1) and `flow/` (Phase 2).
