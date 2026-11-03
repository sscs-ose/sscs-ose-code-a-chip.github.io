
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.05.2026 16:09:53
// Design Name: 
// Module Name: core
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module core(
    input logic clk,
    input logic rst,
    input logic [31:0] instr,
    input logic [31:0] read_data,
    input logic stall,
    output logic [31:0] pc,
    output logic [31:0] alu_result,
    output logic [31:0] write_data,
    output logic mem_write
    );
    
    logic alu_src,reg_write,zero;
    logic [1:0] result_src,pc_src;
    logic [2:0] imm_src;
    logic src_a;
    logic [3:0] alu_con;
    
    controller con1(.opcode(instr[6:0]),.funct3(instr[14:12]),.funct7(instr[30]),
                    .zero(zero),.result_src(result_src),.mem_write(mem_write),
                    .alu_src(alu_src),.pc_src(pc_src),.reg_write(reg_write),
                    .imm_src(imm_src),.alu_con(alu_con),.src_a(src_a));
                    
    datapath data(.clk(clk),.rst(rst),.result_src(result_src),.alu_src(alu_src),.stall(stall),
                  .pc_src(pc_src),.reg_write(reg_write),.imm_src(imm_src),.src_a(src_a),
                  .alu_con(alu_con),.instr(instr),.read_data(read_data),
                  .zero(zero),.pc(pc),.alu_result(alu_result),.write_data(write_data));
endmodule:core
