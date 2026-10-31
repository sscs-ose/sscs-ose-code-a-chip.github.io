# fifo16x8

Implement benchmark_fifo, 8 entries of 16 bits, one rising-edge clock.
Active-low asynchronous reset makes the FIFO empty. Read data is the current
head combinationally, and zero when empty. full/empty reflect current occupancy.
At an edge, accept push iff wr_en && !full; accept pop iff rd_en && !empty,
using flags BEFORE the edge. Thus simultaneous read/write on full accepts only
the read; on empty accepts only the write. No fall-through, overwrite or underflow.
Preserve exact insertion order. Memory reset is not required; externally visible
outputs after reset must meet the empty/zero contract.

Use the fixed top-level port names and widths in interface.json. Develop with
`python3 tools/check.py`. Deliver synthesizable RTL under rtl/. Independent
final vectors/reference and scoring are outside your workspace. Do not alter
the task/checker, invoke extra models, or read other trials. The task's area
limit is installed after reference physical calibration, before evaluation.
