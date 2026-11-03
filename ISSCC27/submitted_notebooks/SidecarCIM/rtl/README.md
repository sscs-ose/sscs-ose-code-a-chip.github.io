# rtl/

All sources are Verilog-2005. Each file's header comment lists its
parameters, derived widths, ports and a cycle-by-cycle protocol, and the
tests in `tests/` check the RTL against `python/golden.py` bit for bit. Every
design shares one load/start/busy/valid handshake and outputs raw integers;
zero-point correction and scaling happen outside the macro.

Every measured build (synthesis, layout, PPA) uses flip-flop storage with
clock-gated rows, `USE_LATCH=0` and `CLK_GATE=1`. The parameter default is
still `USE_LATCH=1` (latch storage), which we kept as a reference variant, so
every flow configuration and test of the measured builds sets `USE_LATCH=0`
explicitly.

## dcim_core.v

The dense unsigned DCIM array. Weights sit in standard-cell flip-flops, one
clock gate per row. Each cycle one input bit-plane (MSB first) is ANDed with
every stored weight bit, popcounted per column and weight bit, shift-added and
shift-accumulated. A dot product takes ABITS = 4 cycles after `start`, 5 back
to back. The bit-plane in use is exported on `xbit` for the sidecar. The dense
comparison points W6A4, W7A4, W8A4 and W4A8 are plain `dcim_core` with other
`WBITS` and `ABITS` values and no wrapper; the port widths of each are in the
header table.

## sidecar.v

The outlier path: K = 2 slots per column, each a 5-bit row index and a signed
12-bit value, in flip-flops (17-bit slots, 272 bits in all). With
`PARALLEL=0` (the default) it picks each slot row's bit from the shared
bit-plane every cycle, gates the value with it and shift-accumulates into a
17-bit signed result, so it finishes in the same ABITS cycles as the dense
array. `PARALLEL=1` is the comparison build with one 12 x 4-bit multiplier per
slot and the same latency.

## sidecarcim_top.v

Joins `dcim_core` and the sidecar on one bit-plane and merges, per column,
`Y = (dense << S) + sidecar` into a signed output, with S loaded per column.
Two parameters shape the final build:

- `PIPE_MERGE=1` adds one register after the merge (one clock gate on the y
  register plus a valid flop). `y` and `valid` appear one edge later, so start
  to valid is ABITS + 1 = 5 edges, while busy, loads, start and `x_in`
  sampling do not change. The throughput stays one dot product per 5 cycles
  back to back, because the result of one dot product is valid while the next
  is busy. We added it because post-layout STA put the worst path of the
  combinational merge at S register, barrel shifter, merge adder and y port
  (36.4 MHz at the slow corner).
- `SBITS=3` stores S in 3 bits (0..7), with an 8-position barrel shifter and a
  22-bit output per column (176 y bits). `SBITS=4`, the default, is the
  original design bit for bit (S 0..11, 26 bits per column). The encoder never
  picks S > 7 in any column of GPT-2 or Qwen (`python/out/srange.json`), so
  accuracy is bit-identical.

The final build is `USE_LATCH=0, CLK_GATE=1, PARALLEL=0, K=2, PIPE_MERGE=1,
SBITS=3`, laid out as `flow/sidecarcim_top_ff_pipe_s3`. It has a latency of 5
cycles and the same throughput as the dense arrays. The generic output width
is YTW = max(YW + SMAX + 1, SCW) + 1 with SMAX = min(VB - 1, 2^SBITS - 1).

## Other files

- `dcim_8bit.v` is the uniform 8-bit baseline, `dcim_core` with
  WBITS = ABITS = 8 (8 cycles).
- `mac_baseline.v` is the conventional baseline: a flip-flop register file and
  one WBITS x ABITS MAC that walks every (i, j) pair, N_IN x N_OUT = 256 cycles
  (257 back to back).
- `icg.v` is the clock gate: `sky130_fd_sc_hd__dlclkp_1` under `SYNTHESIS`,
  a behavioral latch and AND otherwise. It gives one gated clock per dense
  weight row, per register-file row of `mac_baseline`, per sidecar slot column
  and per S register (enable = load or rst, so the synchronous reset still
  clears S). Every source list that reads these modules must include it.

Loading costs one cycle per dense row (32) and one per sidecar column (8); the
two ports may write in the same cycle.
