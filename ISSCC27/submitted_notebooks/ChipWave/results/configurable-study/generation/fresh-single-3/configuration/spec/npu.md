Implement synthesizable SystemVerilog module nebula_npu_dot4.
Ports: input clk,rst_n,req_valid; output req_ready; input [31:0] req_a,req_b;
output rsp_valid; input rsp_ready; output [31:0] rsp_data; input kill.
Each request computes the signed INT32 sum of four parallel signed INT8
products. Lane 0 is bits 7:0. Widen products before reduction. At most one
operation is outstanding. An idle module is ready. If accepted on edge n,
rsp_valid is low after n and n+1 and high after n+2. Hold valid/data under
backpressure, and do not accept another request before consuming the result.
Active-low reset and active-high kill dominate acceptance and output,
including combinational req_ready/rsp_valid while either is asserted.
Cancel pending work; no stale response may emerge after recovery.
No persistent accumulation across requests, memory, saturation or rounding.
Use four parallel multipliers. All inputs are sampled on rising edges.
