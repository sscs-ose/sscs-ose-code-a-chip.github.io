Design fresh original synthesizable SystemVerilog for nebula_npu_dot4.
Ports: input clk,rst_n,req_valid; output req_ready; input [31:0] req_a,req_b;
output rsp_valid; input rsp_ready; output [31:0] rsp_data; input kill.
Compute the signed INT32 sum of four signed INT8 products, lane0 in bits7:0.
Widen products before reducing. Accept at edge n on req_valid&&req_ready,
assert result after edge n+2, hold valid/data until consumed. At most one
operation is outstanding. Reset and kill dominate all acceptance and output,
cancel pending work, and allow correct recovery. No hidden accumulator,
memory, saturation or rounding. Use four parallel multipliers.
