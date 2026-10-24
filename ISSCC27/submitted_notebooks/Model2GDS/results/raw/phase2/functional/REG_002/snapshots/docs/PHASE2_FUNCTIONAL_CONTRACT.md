# Phase 2 functional qualification contract

Human authorization extends the audited Phase 1 compute fabric to exactly
S=2,4,8. The arithmetic, output-stationary dataflow, token meaning and counted
edge convention in `PHASE1_MICROARCHITECTURE.md` are unchanged. The old Phase 1
implementation and evidence remain immutable reference material; new generic
modules are the sole implementation used for all Phase 2 configurations.

The generic fabric elaborates S by S real `gemm_pe` instances. Lane i occupies
bits 8*i+:8 of the packed A boundary; lane j similarly addresses B. Output
(i,j) occupies bits 32*(S*i+j)+:32. Mask/result-valid bit S*i+j addresses that
PE. Packed ports support the pinned Yosys frontend without replacing the PE
interconnect with behavioral GEMM. Thin generated wrappers bind S only.

Each tile begins with one counted clear edge, which flushes every accumulator
and pipeline valid/last register and latches the tile mask. At subsequent data
edge t, row i receives reduction token k=t-i and column j receives k=t-j when
in range. Both valid tokens MAC; matching final tokens set sticky result-valid
on the same edge as the final product. Completion is a nonzero-mask AND over
required result-valid bits, observed after the edge. Inactive lanes are invalid
zeros. Reset edges precede workload counting.

Tiles traverse output origins in row-major order in steps of S, with active
rows=min(S,M-row) and columns=min(S,N-col). All K is streamed for every tile.
The next edge after completion is the next tile clear: no extra inter-tile
bubble, overlap, K tiling, buffering or backpressure is introduced. Signed
INT8 multiplication sign-extends to modulo-2^32 INT32 accumulation.

The independent token model advances all S*S old-neighbor register states and
stops on its own masked last-token result flags. The identity
`K + active_rows + active_cols - 1` is only a secondary consistency check.
The C++ harness independently drives skewed boundaries, observes actual RTL
completion and counts actual rising edges. Python expected cycles are never
supplied to the harness.

The fixed qualification plan reuses every one of the 147 preserved Phase 1
input cases, once per authorized S: 13 directed, 128 deterministic random and
six frozen-workload sanity cases. Original seeds, case identities and input
matrices remain unchanged. All numerical outputs and tile/workload cycles must
match the numerical golden and generic token model. S=2 must additionally
match every audited Phase 1 RTL output and per-tile/workload count exactly.
Verification cases do not become research workloads. No ranking, winner,
implementation-aware latency or Phase 3 analysis is computed.

Physical qualification uses the same generic fabric through the observation
boundary in `PHASE2_PHYSICAL_VIEW.md`. Its recipe and timing method are frozen
by a dedicated commit before accelerator synthesis/P&R begins.
