# Formal proofs

Formal verification proves a property holds for every possible input sequence, not just the ones a
test happens to try. Each proof here wraps one RTL module, unchanged, in a harness that adds a
small reference model and assertions, then runs [SymbiYosys](https://github.com/YosysHQ/sby) (SBY).

| Module | What is proved | Engine |
| --- | --- | --- |
| `host_fifo` | Occupancy never exceeds the depth; `full` and `empty` are exact; flush empties it; any value written comes out unchanged and in order | `abc pdr` (unbounded) |
| `frame_buffer` | Same as above, plus commit and rollback: rollback discards exactly the uncommitted entries, committed entries survive, and reads only ever see committed entries | `abc pdr` (unbounded) |
| `uart_tx` | Every frame is a start bit, 8 data bits LSB first, and a stop bit, each held for exactly `clk_ratio` clocks, for every ratio from 1 to 15; the line idles high and `tx_ready` is exact | `abc pdr` (unbounded) |
| `branch_unit` | The two BRANCH rules behave as the ISA describes: compare with mask and value, hit and miss actions, read-back mismatch and CRC-result sources, rule 0 before rule 1, each rule acts at most once per frame, `stall`, `hit`, `branch_abort` and `line_watch` timing | `abc pdr` (unbounded) |
| `crc_unit` | The 8-bit-per-clock update equals a bit-by-bit CRC of the configured width (1 to 16, any polynomial, any chunk of 1 to 8 bits), kept right aligned; `good` is exactly "register equals residue"; `crc_out` is the register top aligned, inverted when asked; feeding the register its own value top bit first always leaves zero (so an appended CRC checks with residue 0); the configuration outputs match the last write | `abc pdr` (unbounded) |
| `line_codec` | Entry accounting against a reference count: `tx_done` is never pulsed without an outstanding entry, at most four entries are ever outstanding, and whenever the codec has been idle (select output inactive) for three clocks every accepted entry has been answered with exactly one `tx_done`, including entries dropped by `tx_cancel` and cancels that arrive while earlier drops are still being answered; with DRIVE 00 no output enable is ever set; with open drain the data and clock outputs only ever pull low; the clock output is only enabled when the codec generates the clock. Every line, clock and output configuration is left free and may change at any time | `abc pdr` (unbounded) |

Every job also has a `cover` task that shows the interesting cases are reachable (the FIFO fills,
a tracked value is read back, both rules fire together), so a proof cannot pass by accident.
Planting a bug (for example, rollback keeping one entry too many, or swapping the rule priority)
makes the matching proof fail with a counterexample trace.

The proofs use small parameters (4-entry buffers, 4-bit data, a 4-bit ratio). The logic does not
depend on the size, so this covers the same behaviour as the chip's 16-entry buffers.

## Running

Install the [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) (it includes Yosys,
SBY, yices and ABC), then:

```sh
bash scripts/formal.sh          # every proof
cd formal && sby -f uart_tx.sby # one proof; results in formal/uart_tx_prove/ and uart_tx_cover/
```

A failing proof writes a counterexample waveform, `formal/<name>_prove/engine_0/trace.vcd`, which
opens in GTKWave or Surfer. The `formal` GitHub workflow runs every proof on each push and keeps the
results as an artifact.

## Not yet covered

`uart_rx` (the auto-baud measurement makes the state space large), the counters in the frame chain,
the bit-level timing of the line codec and the control unit. These are checked by the simulation suites instead.
