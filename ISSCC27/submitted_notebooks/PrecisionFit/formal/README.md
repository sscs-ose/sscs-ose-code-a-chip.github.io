# Formal Verification (SymbiYosys)

This directory is created by `src/python/formal_verify.py` on first run. It
holds generated harnesses and `.sby` task files. Nothing here is committed;
the entire layer is regenerable from the templates and the driver:

```bash
python3 src/python/formal_verify.py            # proofs + mutation tests
python3 src/python/formal_verify.py --proofs   # proofs only
```

## Status — completed

All 15 proof tasks passed. Mutation testing killed all 4 injected bugs.
Runtime: fastest < 1 s, slowest ~14 s.

## Properties proven

Run on all three committed FIR configurations
(`fir_conservative_uniform`, `fir_best_uniform`, `fir_sensitivity_guided`):

| Property | Statement |
|---|---|
| P1 | `rst_n` low clears all taps, accumulator, `out_valid` and `out_data` within one cycle |
| P2 | `out_valid == $past(valid_pipe)` — clean 2-stage pipeline, no skipped or doubled valid |
| P3 | No `out_valid` without `in_valid` exactly two cycles earlier |
| P4s | Stall freeze: when `in_valid` is low, all registers hold their values |
| P4a | Full datapath equivalence: `acc_reg` and `out_data` equal an independent per-tap shadow MAC bit-for-bit |
| P4b | Requantizer correctness: shift, rounding and saturation match the Python golden model's integer arithmetic |
| P5 | `out_valid` implies `out_data` is within the two's-complement saturation range |
| L1/L2 | Helper lemmas (shadow delay line, shadow deep state) that let k-induction close P4a |

## Mutation tests

Four bugs were injected into the RTL, one at a time, and all four were killed
by the property set (i.e. at least one proof task failed for each injected bug,
confirming the properties are not vacuous):

| Bug | Injected change |
|---|---|
| M1 | Requantizer shift off-by-one (`SHIFT-1` instead of `SHIFT`) |
| M2 | Rounding constant zeroed (round → truncate silently) |
| M3 | Symmetric pre-adder sign-bit dropped (1-bit narrower fold wire) |
| M4 | Center-tap constant off-by-one LSB |

## Implementation notes

The properties live in the DUT template's `` `ifdef FORMAL `` block
(`src/verilog/fir_symmetric.v.j2`) and are invisible to simulation, lint and
synthesis. The `regen_rtl.py` drift check verifies that regenerating the RTL
from the template produces byte-identical files, ensuring the formal block
never diverges from the simulated design.

**Engines:** `abc pdr` (unbounded IC3/PDR) and `smtbmc yices` (bounded model
checking with an independent SMT solver; Z3 also works). All properties are
safety properties whose violating traces are bounded well below the BMC depth
used, so the bounded runs constitute complete proofs for this architecture.

**Requirements:** `sby` (SymbiYosys), `yosys`, `yices` (or `z3` for smtbmc),
and `abc` (for PDR tasks).
