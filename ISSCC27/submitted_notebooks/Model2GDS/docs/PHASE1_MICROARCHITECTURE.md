# Phase 1 microarchitecture and cycle contract

This contract is fixed before final regression collection. Phase 1 is authorized
by the human instruction following independent audit of Phase 0 commit
`fa59e0f7378b40b5d2598daeb25750c86d7f2d4e`. Only the 2×2 functional compute
core is implemented and evaluated. No physical accelerator work is authorized.

## Arithmetic and reset

Operands are signed INT8 in [-128,127]. Each multiplication produces a signed
16-bit product, sign-extended to 32 bits before addition. Accumulators are signed
INT32 with modulo-2^32 two's-complement wrap, never saturation. The numerical
reference explicitly wraps results. No unbounded host integer is a final C.

Reset is synchronous, active high. On a rising edge, reset takes priority over
clear, and clear takes priority over normal operation. Reset or clear sets every
PE accumulator, forwarded data, forwarded valid/last flags, and sticky result
valid to zero. Reset also clears the array's active-output mask. Reset edges are
outside workload counting. Clear latches the next tile's active mask.

## PE registers and token movement

Each of four PEs holds C locally. On each normal rising edge it registers its A
input for its right neighbor and its B input for its lower neighbor, including
separate valid and last bits. All PEs sample pre-edge inputs; a token therefore
traverses one PE per edge. Invalid tokens are bubbles, their payload is ignored,
and their forwarded last flag is zero. There is no ready/backpressure interface.

The PE updates C exactly when both input valid bits are high. On a valid pair
with both last bits high it incorporates that product and sets sticky
`result_valid` on the same edge. Result valid remains high until reset/clear.
Producers must align A/B tokens and their last bits for a required output; a
single valid token does not accumulate and does not finish a result. Directed
verification exercises bubbles and one-sided valid/last inputs. After a final
pair the producer supplies no further pair to that PE until clear.

## Streaming boundary and output mask

The idealized boundary has two A lanes on the left and two B lanes on the top,
with one valid/last pair per lane. It supplies the wavefront; it is not an SRAM,
DMA, processor, cache, or external-memory interface. The array contains four
actual registered PE instances and neighbor wires, not behavioral GEMM loops.

For tile origin (row0,col0), active rows r=min(2,M-row0), active columns
c=min(2,N-col0). Active mask bit (2*i+j) is set iff i<r and j<c. Inactive
boundary lanes carry invalid zero tokens. PE output values are read only for
active mask bits. Unused physical PEs never delay completion. A nonzero active
mask is required for a tile. `tile_done` is the combinational AND of sticky
result-valid flags of masked PEs, gated by a nonzero mask. It becomes visible
after the final MAC edge settles; there is no extra completion register edge.

## Counted edges and schedule

For every tile, one rising clear/setup edge counts as cycle 1. Data begins on
the immediately following rising edge. Number data edges by t=0,1,... . At
edge t, boundary A lane i supplies A[row0+i,k] for k=t-i, and B lane j supplies
B[k,col0+j] for k=t-j, when that lane is active and 0<=k<K. Last accompanies
k=K-1. Otherwise that lane is invalid. Inside PE(i,j), pair k is consumed at
data edge t=k+i+j. Operands are sampled before the edge; C and result-valid are
sampled after evaluation of the edge. M,N,K must all be positive integers.

Tile completion is observed from RTL `tile_done`, not predicted by the model
or a fixed wait. It is the edge on which the last required output incorporates
its final K product. A sequential Python token model independently advances all
PE states using the old neighbor state and stops on its own masked completion.
As a secondary check only, a bubble-free tile takes K+r+c-1 counted edges,
including clear (1×1,K=1 takes two edges; 2×2,K=1 takes four edges).

GEMMs tile M and N in row-major order, stepping by two, streaming all K for
each tile. There is no K tiling. A tile is read after its completion edge; the
next rising edge is the next tile's clear. No uncounted inter-tile edge or extra
bubble is inserted. Workload cycles equal the sum of observed tile cycles.
No inter-tile overlap or double buffering is implemented. Ragged edges use the
active mask above; clearing all PEs prevents stale pipeline state between tiles.

## Verification and separation from research workloads

The numerical golden reference, Python token/cycle model, and Verilator harness
implement this contract separately. The cycle model never reads RTL, simulator
output, timing, frequency, or physical metrics. Optional per-edge traces retain
token/accumulator/result-valid state for diagnosis; a closed form never controls
model completion. The harness schedules the boundary independently and counts
actual rising edges until RTL completion, with only a generous failure timeout.

Verification-only directed inputs cover signs, extrema, zeros, K=1, underfilled
and ragged dimensions. PE tests cover overflow, reset, clear, propagation,
bubbles and final tokens. The randomized suite uses master seed 20260927 and
128 reproducible cases, M,N in 1..6 and K in 1..16, with signed INT8 data. These
are verification cases, not additions to the research workload set.

The six existing workloads W1..W6 are taken unchanged from PROJECT_FREEZE.json
and checked against the frozen experiment protocol. They run with deterministic
inputs on the 2×2 functional path only, in a separate `frozen_workload_sanity`
category. No ranking or research conclusion is derived.

Any disagreement is a model/RTL/harness/convention bug until resolved. Recorded
attempts are immutable; retries use new run IDs. A convention change requires
an explicit documented bug explanation and new evidence, never an adjustment
merely to force numerical or cycle agreement.
