# Phase 1 — Parameterized RTL and Verification

## Goal
Turn the hard-coded (UNROLL=1) `nano_hash` SHA-256 core into a single
parameterized implementation `#(parameter int UNROLL)` and prove it bit-exact
against a golden model across all planned Pareto variants.

## Deliverables
- `rtl/generated/sha256_core.sv` — parameterized compression core.
  `UNROLL` rounds are computed per cycle (`NCHUNK = 64/UNROLL` cycles per
  block); message schedule is extended in-cycle through an `ext[]` chain; the
  64 round constants are returned by a `kconst()` function (Icarus cannot
  elaborate unpacked `localparam` arrays).
- `rtl/generated/sha_top.sv` — parameterized top with the *same* port list as
  the original `sha_256_top.sv`, reusing the untouched vendored
  `message_padder` and `digest_buffer`.
- `verif/cocotb/` — cocotb 2.1.0 harness.
  - `test_sha256.py` — 5 suites, golden model = Python `hashlib.sha256`.
  - `run.py` — cocotb runner (Verilator/Icarus), per-UNROLL build dir under
    `flow/runs/cocotb_u<UNROLL>/`.
- `tools/run_cocotb_matrix.sh` — one-shot runner for UNROLL ∈ {1,2,4,8,16}.
- `tools/phase1_env.sh` — environment probe.

## Method
Each variant is elaborated with `-PUNROLL=N`, driven through the full
AXI-stream `sha_top`, and the 8×32-bit output digest is compared to
`hashlib.sha256(bytes(msg)).digest()`.

Test suites:
1. `test_known_vectors` — empty, "abc", 56-byte NIST vector, 112-byte
   (2-block) vector, `bytes(range(256))` (4 blocks), and 10^6 `'a'` bytes
   (~15 625 blocks) to stress multi-block chaining.
2. `test_boundary_lengths` — 28 lengths straddling the 55/56 and 63/64 packing
   boundaries.
3. `test_random` — 40 randomized messages, 0–300 bytes.
4. `test_ingress_bubbles` — 15 randomized messages with `s_axis_tvalid`
   deassertions.
5. `test_egress_backpressure` — 15 randomized messages with `m_axis_tready`
   stalls at beat 2 and 5.

Simulator: Verilator 5.032 (`--timing -Wno-fatal`), cocotb 2.1.0, Python
3.14 hashlib.

## Results (2026-10-11)
All 5 × 5 = 25 test/suite combinations **PASS** (0 failures):

| UNROLL | NCHUNK/block | rounds/cycle | suites | result |
|-------:|:-----------:|:-------------|:------:|--------|
| 1 | 64 | 1 | 5 | PASS |
| 2 | 32 | 2 | 5 | PASS |
| 4 | 16 | 4 | 5 | PASS |
| 8 | 8 | 8 | 5 | PASS |
| 16 | 4 | 16 | 5 | PASS |

## Notes
- Output `digest_valid` is qualified with the padder `done` signal in
  `sha_top` so only the hash of the final block is emitted (intermediate
  per-block digests for multi-block messages are suppressed). Behavioral
  model verified against the 1 000 000-byte vector.
- Icarus (12.0) cannot elaborate the vendored `sha_256_top_tb.sv` (named task
  arguments with default values + `return` in tasks), so verification runs on
  cocotb + Verilator; the original RTL/TB and 5 NIST vector sequences remain
  vendored for reference.

## Reproduce
```bash
# one variant
python verif/cocotb/run.py --sim verilator --unroll 8
# all variants
bash tools/run_cocotb_matrix.sh
```
Results XML per variant: `flow/runs/cocotb_u<UNROLL>/sim_build_verilator/`.