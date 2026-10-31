# P0 compute-only split

## Authority and scope

Both complete input records (`fold-design`, `fold-spec`) identify commit
`fb5a23d8d9d60f956cb4599d4e6b84e67cb1077b`. Every declared input file was
byte-compared with that commit. The complete CSIR document equals the specification
artifact payload. Its demand equals both `spec/design_doc.md` and
`spec/contract.md`; their SHA256 is
`c8d6467bebee2297eac8b020472b736dad319a5532878b24205c6311833ea7a3`.
The frozen digest in CSIR, artifact spec_digest and implementation constraints is
`sha256:492e6b0b622e342562231b756bf170ec6b30c47c1a43d550d6dba0eab17c5b9b`.
The initial RTL matches the immutable R hash
`da28b093a22a9fa923c89fa8dd28f00292ceeba8ada8c142192757b140deb5ad`.
No dependencies artifact was supplied.

The approved folding clause explicitly supersedes the historical +2-cycle and
110%-area rules. The old latency wording remains in CSIR acceptance metadata;
the signed demand and LB.PERFORMANCE require all 162 steady supply/completion
intervals not to increase, with latency reported separately. No architectural or
interface disagreement was found. Physical constraints do not change RTL behavior.
This delivery implements P0 only; P1/P2 require subsequent resume and captured
physical feedback. No specification, checker, tool or vendor source was modified.

## Ownership and capacity

`rtl/lb_feedback.sv` contains wire-only `lb_feedback`, with exactly the system
instances `lb_l0 L0` and `lb_l1 L1`. No parameters or package port names,
directions or widths changed. There is no wrapper state or third logic block.
The two additional module definitions are simulation models of library cells,
guarded by `ifndef SYNTHESIS`.

| Payload | Owner | Capacity |
|---|---|---:|
| Input ping-pong banks, `input_bank[0:1]` | L0 | 128 bytes |
| Four aggregate weight rows, `weight_row[0:3]` | L0 | 128 bytes |
| Output ping-pong banks, `output_bank[0:1]` | L0 | 64 bytes |
| Eight signed32 `accumulator[0:7]` registers | L1 | 32 bytes |
| Total | L0 + L1 | 352 bytes |

L0 retains all PHY ports, static repair/map validation and lock state,
per-lane issue/response counters, partial-row validity, job/error/consume control,
output bank occupancy and ordered retirement. Input/output/weight payload storage
has the original reset behavior (valid/control state resets; payload is not
artificially initialized). L1 contains the original 32 varying signed8x8 products,
eight sign-extended four-product reductions and eight signed32 accumulators.
No storage, multiplier, useful lane or queue reservation capacity is removed.

## Host routing and compute cut

All 23 original non-PHY ports (181 bits including clock/reset) enter or leave the
system through L1. Each has a reverse-direction `link_<original_name>` port on
L1 connected to the original host port name on L0. There is no package-to-L0
host bypass. L1 uses package `clk`/`rst_n` for its own synchronous accumulators;
L0 uses the received clock/reset after the actual endpoint cells.

| Compute signal | Direction | Meaning |
|---|---|---|
| `fold_x[31:0]` | L0 -> L1 | Current four input bytes, unchanged little-endian order |
| `fold_w[255:0]` | L0 -> L1 | Current aggregate weight row, four bytes per lane |
| `fold_start` | L0 -> L1 | Original `start_job` |
| `fold_consume` | L0 -> L1 | Original `consume` |
| `fold_next[255:0]` | L1 -> L0 | Eight combinational accumulator + tile_sum results |

At synchronous reset or start, L1 clears the accumulators; on consume it captures
`fold_next`. L0 stores that same combinational value on the last tile, without
waiting for the updated accumulator. No added cycle, pipeline or serialization
exists. L0's original `consume` includes `active`, so start and consume are
mutually exclusive in reachable state. L1's start priority preserves this behavior.

The original four-row reservation window and independent lane request/response
handling are retained verbatim apart from host endpoint signal names. Last-tile
output error still captures `job_error | response_error`, including errors arriving
on that edge. Output stability, bank exclusion, legal K=4/16/64, repair routing,
independent request stalls and delayed responses remain governed by the original
L0 control equations. No new handshake or response backpressure is introduced.

## Actual endpoint cells

Each cross-die output is driven directly by `sky130_fd_sc_hd__buf_4.X` (TX),
and each input directly drives `sky130_fd_sc_hd__buf_2.A` (RX). Every instance
has `(* keep = 1, dont_touch = 1 *)`; endpoints are cells, not aliases or comments.
All core-side values use separate `core_*` nets/registers.

For vector port `p`, actual instance names are `L0.endpoint_p[b].tx/rx` or
`L1.endpoint_p[b].tx/rx`. Scalar names are `L0.tx_p/rx_p` or `L1.tx_p/rx_p`.
Host ports on L1 use `p=link_<original_name>`; compute ports use their fold names.
For example, `L0.endpoint_fold_x[0].tx` drives `L0.fold_x[0]`, and
`L1.endpoint_fold_x[0].rx` receives `L1.fold_x[0]`.

The clock path is package `clk` -> `L1.tx_link_clk` (buf_4) -> `link_clk`
-> `L0.rx_clk` (buf_2) -> `L0.core_clk`, the actual clock of L0's sequential
process. Reset similarly traverses `L1.tx_link_rst_n` and `L0.rx_rst_n` to
`core_rst_n`. Reset remains synchronous; no generated clock, gating or reset state
was added. These paths must retain cell timing during downstream CTS/joint STA.

The frozen link-map counts **725 functional links** (179 host + 546 compute)
plus **2 utility links** (clock/reset), hence **727 connected link pairs**:

| Module | TX buf_4 | RX buf_2 | Total |
|---|---:|---:|---:|
| L0 | 362 | 365 | 727 |
| L1 | 365 | 362 | 727 |
| System | 727 | 727 | 1454 |

Behavioral cell definitions exist only outside SYNTHESIS. Production synthesis
must read actual Liberty blackboxes before the RTL; the simulation definitions
are not a substitute for library timing or a synthesized wire implementation.
No technology files were copied or changed.

## Quick checks and limits

The first Icarus elaboration found forward references to unpacked arrays in the
new cut assignments. Moving those assignments below the existing declarations
resolved it; there were two RTL source revisions, within the three-attempt limit.
Final checks:

- `iverilog -g2012 -s lb_feedback -o build/rtl/p0.elab rtl/lb_feedback.sv`: passed.
- `verilator --lint-only --top-module lb_feedback -Wall -Wno-DECLFILENAME rtl/lb_feedback.sv`: passed with an empty log. Only the filename warning is disabled because the frozen delivery requires several modules in one file.
- Yosys `read_verilog -sv -nosynthesis rtl/lb_feedback.sv; hierarchy -check -top lb_feedback; stat -width; write_rtlil build/rtl/p0.il`: passed. This is frontend elaboration using simulation cell models, not technology synthesis or physical qualification.
- `python3 build/rtl/check_structure.py`: assert-based structural audit of elaborated RTLIL passed: all 727 frozen map entries have exactly one direct TX and RX with both retention attributes; expected per-die counts match; wrapper has exactly two cells and no process; 32 L1 multipliers consume signed bytes (frontend sign-extended to the 16-bit product context) and produce 16-bit outputs; original package ports and 352-byte storage declarations match.
- Frozen file gates: `rtl/lb_feedback.sv` and `docs/implementation/physical-change.md` are present and nonempty.

Text evidence is under `build/rtl/`. Generated elaboration binaries and RTLIL are
scratch files, not production RTL. Review of acceptance stimulability/observability:
all original package and PHY signals remain exposed, allowing downstream tests to
exercise signed edge cases and K values, all repair maps, partial rows and four-row
bursts, independent delays, overlapping jobs, output stalls, last-tile errors and
reset with outstanding work. Output words/status and PHY requests remain externally
observable; the split does not require checker changes or internal force hooks.

Engineering verdict: P0 structural implementation and available quick lint/
elaboration pass. Independent numerical/configuration/protocol regressions,
162-case performance comparison, actual Liberty synthesis retention, routed timing,
power, DRC/antenna/LVS and physical endpoint placement were not executed here.
Combinational L0 -> L1 -> L0 paths and the clock feedthrough require downstream
joint timing analysis; no physical or performance qualification is claimed.
