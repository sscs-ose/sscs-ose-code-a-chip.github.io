Integrate the supplied unchanged gemm_pe PE using four parallel instances.
Write a new nebula_npu_dot4 adapter; do not replace or bypass the PE.
The PE has active-high synchronous rst/clear and an internal accumulator.
Clear/reset each PE between requests so the external interface has no cross-request accumulation.
a_valid/b_valid gate accumulation; a_last/b_last set sticky result_valid. Read its supplied interface/source.
