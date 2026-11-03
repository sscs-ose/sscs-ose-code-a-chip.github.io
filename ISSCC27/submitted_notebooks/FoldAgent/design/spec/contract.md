# Frozen LB-Feedback single-LB contract v1

Purpose: a reduced logic block with eight geographically fixed normal MC data
channels, two static repair channels, two banks per normal MC, a four-row
concentrated weight queue and a 4x8 signed INT8 MAC array. The normal resources
represent sixteen DRAM banks. Spare capacity is separate and hypothetical.
DRAM contents and delays belong to the external environment, not synthesized
logic. No external IP, generated reference RTL or checker changes are permitted.

## Interface: module `lb_feedback`, no parameters

All signals use one rising-edge `clk`; synchronous active-low `rst_n`. A
valid/ready transfer occurs at a rising edge. Source payloads must stay stable
while valid and not ready. Reset cancels all work, unlocks configuration, clears
errors and output validity; a new task requires input refill and configuration.

| Port | Direction | Bits | Meaning |
|---|---|---:|---|
| clk, rst_n | input | 1 each | Clock and synchronous reset |
| cfg_commit | input | 1 | Try to freeze static configuration |
| cfg_map | input | 16 | Two bits per logical lane |
| cfg_bad | input | 10 | Bad physical targets |
| cfg_locked, cfg_error | output | 1 each | Configuration status |
| in_valid | input | 1 | Input-vector write |
| in_ready | output | 1 | Selected input bank available for writing |
| in_bank | input | 1 | Input ping-pong bank |
| in_word | input | 3 | Eight INT8 values at offsets 8*in_word..+7 |
| in_data | input | 64 | Little-endian packed signed INT8 values |
| cmd_valid | input | 1 | Start one GEMV |
| cmd_ready | output | 1 | Can accept command |
| cmd_k | input | 7 | Exactly 4, 16 or 64 |
| cmd_in_bank, cmd_out_bank | input | 1 each | Selected ping-pong banks |
| out_valid | output | 1 | Next output word available |
| out_ready | input | 1 | Consume output word |
| out_data | output | 64 | Two packed signed INT32 results, low lane first |
| out_last, out_bank, out_error | output | 1 each | Last of four words, bank, accumulated PHY error |
| phy_req_valid | output | 10 | Read request per physical MC |
| phy_req_ready | input | 10 | MC independently accepts request |
| phy_req_addr | output | 160 | Sixteen-bit address per physical MC |
| phy_req_bank | output | 10 | Bank selection per physical MC |
| phy_rsp_valid | input | 10 | One-cycle ordered read response, no response backpressure |
| phy_rsp_rdata | input | 320 | Thirty-two-bit data per physical MC |
| phy_rsp_error | input | 10 | Per-response error flag |

## Static repair

For logical lane j=0..7, cfg_map[2*j+:2] selects 0:physical j,
1:physical 8, 2:physical 9, 3:illegal. Targets must be unique and not bad.
On cfg_commit while unlocked, a legal mapping locks until reset and clears
cfg_error. Illegal mapping leaves cfg_locked low and sets cfg_error; a later
legal commit is allowed. cfg_commit after lock is ignored. A bad unselected
physical lane does not invalidate a mapping. Map=0 is the normal eight lanes.
Repair redirects the same bank pair and addresses; it does not add bandwidth.

## Input, commands and output

Each input bank stores 64 INT8 values. A bank used by an active command cannot
be overwritten (`in_ready=0` for that bank); the other bank remains writable.
The caller fills all used input values before cmd acceptance and may prepare the
next input bank concurrently. There is one active MAC job at a time; both output
banks can retain completed jobs while the output consumer stalls. Do not accept
a command targeting a busy output bank or illegal K. Valid commands produce
exactly four output words, in command order, with out_last on word 3 only.
out_bank and out_error remain stable across each result. Output words never
interleave jobs. Output can overlap computation of the next job.

For each output j: Y[j] = sum(i=0..K-1, signed(X[i])*signed(W[i,j])).
Accumulate exactly in signed INT32; no saturation, quantization or rounding.
K<=64 avoids signed INT32 overflow. Do not use signless multiplication.

## Weight delivery

Tile t=0..K/4-1 comprises four K positions and eight output positions. Logical
lane j carries W[4*t+0..3,j] in a 32-bit little-endian word. Request address is
floor(t/2); bank=t mod 2. Each lane issues every tile once in increasing t, only
to its selected physical target. Unselected targets remain invalid. Address and
bank must stay stable under independent request backpressure. Responses on a
physical lane are ordered as its accepted requests, but different lanes have
independent delays. A response is no earlier than the cycle after request.
The caller returns exactly one response for each accepted request.

Reserve four aggregate row slots (8*32*4=1024 payload bits); incomplete rows
must retain independently returned lane data. Issue ahead independently up to
four pending rows; never exceed four outstanding requests on a physical lane.
Do not serialize all MC reads through a single physical channel. The initial
implementation uses a central four-row queue and central validity/control;
future candidates may regroup the same capacity. MAC arithmetic is 4x8 per
consumed tile. OR all phy_rsp_error flags into out_error without changing the
numeric result. Retire every response before releasing the active job.

## Frozen implementation/performance boundaries

Use standard cells for small queues, local input/output ping-pong storage and
MACs. Synthesize all 32 MAC operations, no serial multiplier replacement.
All physical requests and responses remain connected and meaningful. Unloaded
throughput/latency will be measured on the accepted initial RTL; optimization
must not lower sustained jobs/cycle and may add at most two cycles per job.
Storage capacities, eight useful lanes and normal aggregate width cannot shrink.

Independent verification owns the testbench and reference arithmetic. It checks
all 65,536 configuration encodings; all 73 legal mappings; five random seeds
with 1,000 tasks each; signed edge cases, bank selection, backpressure, response
delay, reset during work, ping-pong and error propagation. Checker mutation is
an engineering failure, not a repair. Physical obligations are separate: fixed
Sky130HD TT25C/1.8V, 100ns, I/O delay20ns, transition2ns, output load5fF;
detail route, extracted setup/hold, installed DRC/antenna/LVS, readable GDS.


# Approved folding pilot
Create P0, the frozen compute-only coarse split of the provided R RTL.
Deliver one rtl/lb_feedback.sv containing lb_feedback (wire-only system), lb_l0 and lb_l1.
System instances MUST be named L0 and L1. Preserve every original external port and
cycle-level behavior. Place all phy_* ports on lb_l0, all original non-phy ports on
lb_l1. L1 forwards each host signal across a link_<original_name> port to L0;
directions reverse relative to its package port, including link_clk and link_rst_n.
L0 keeps its original host port names. No host bypass outside L1 is allowed.
L0 keeps mapping/configuration, request/response state, four weight rows, input/output
banks and all job/consume control. L1 keeps all 32 varying signed8x8 products,
eight tile reductions and eight signed32 accumulators. Preserve 352 payload bytes.
Exactly these compute ports cross: L0 outputs fold_x[31:0], fold_w[255:0],
fold_start,fold_consume; L0 inputs fold_next[255:0]; L1 directions reverse.
fold_start=start_job, fold_consume=consume. fold_x is the current 4-input slice;
fold_w is the current weight row. fold_next returns accumulator+tile_sum combinationally,
including the last tile result. No additional pipeline, serialization or reduced MACs.
Keep reset synchronous. Preserve last-tile errors, independent response delays and
all backpressure/repair semantics. No third block or extra wrapper state.
Every one of the 725 functional links uses real TX sky130_fd_sc_hd__buf_4 and RX
sky130_fd_sc_hd__buf_2 at the physical port, with keep/dont_touch cell attributes.
Clock/reset must also have real connected cells and remain valid clock/reset paths.
Use behavioral definitions of these library cells only under `ifndef SYNTHESIS for
standalone Icarus simulation; synthesis reads the actual Liberty blackboxes first.
Read spec/folding-spec.json and spec/contract.md, then make the minimum structural
split of the current RTL. Do not alter any checker, spec or tool. Run quick lint/
elaboration only; independent numerical/performance/physical Tasks are downstream.
Document storage ownership, the cut and actual endpoint cells in
docs/implementation/physical-change.md. Finish with the exact native output protocol.
This Task owns P0/P1/P2 over its life; CURRENT authorization is P0 only, at most
3 RTL Attempts. P1/P2 need subsequent user resume and captured physical feedback.

The provided R RTL is explicitly permitted as the starting implementation.
Steady supply and completion intervals must not increase in any of the 162 frozen cases. A constant added latency is reported separately. The old +2-cycle and110%-area optimization rules are superseded only for this folding experiment.
