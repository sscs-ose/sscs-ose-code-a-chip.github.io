`default_nettype none
module nebula_cpu_npu_top (
    input logic clk,
    input logic rst_n,
    output logic imem_valid,
    output logic [31:0] imem_addr,
    input logic [31:0] imem_rdata,
    output logic dmem_req_valid,
    input logic dmem_req_ready,
    output logic dmem_req_write,
    output logic [31:0] dmem_req_addr,
    output logic [31:0] dmem_req_wdata,
    output logic [3:0] dmem_req_wstrb,
    input logic dmem_rsp_valid,
    output logic dmem_rsp_ready,
    input logic [31:0] dmem_rsp_rdata,
    input logic dmem_rsp_err,
    output logic commit_valid,
    output logic [31:0] commit_pc,
    output logic [31:0] commit_insn,
    output logic [4:0] commit_rd,
    output logic [31:0] commit_wdata,
    output logic [31:0] commit_mem_addr,
    output logic [3:0] commit_mem_wstrb,
    output logic [31:0] commit_mem_wdata,
    output logic trap_valid,
    output logic [31:0] trap_pc,
    output logic [31:0] trap_cause,
    output logic [31:0] trap_tval
);
    rv32i_five_stage_cpu #(.ENABLE_XNEBULA(1)) core (.*);
endmodule
`default_nettype wire
