
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.05.2026 15:31:01
// Design Name: 
// Module Name: datapath
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


module datapath(
    input logic clk,
    input logic rst,
    input logic stall,
    input logic [1:0] result_src,
    input logic alu_src,
    input logic [1:0] pc_src,
    input logic reg_write,
    input logic [2:0] imm_src,
    input logic src_a,
    input logic [3:0] alu_con,
    input logic [31:0] instr,
    input logic [31:0] read_data,
    output logic zero,
    output logic [31:0] pc,
    output logic [31:0] alu_result,
    output logic [31:0] write_data 
    );
    
    logic [31:0] pcplus4,pcjump,pcjalr,pcnext;
    logic [31:0] immext;
    logic [31:0] sra,srb;
    logic [31:0] srca;
    logic [31:0] result;
    logic [31:0] rd2_wire;
    //program counter logic 
    d_ff d_ff1(.clk(clk),.rst(rst),.stall(stall),.d(pcnext),.out(pc));//d flip flop for PC
    adder a1(.a(pc),.b(32'd4),.c(pcplus4));//pc+4
    adder a2(.a(pc),.b(immext),.c(pcjump));//branch and jal
    mux_3 m1(.a(pcplus4),.b(pcjump),.c(pcjalr),.sel(pc_src),.y(pcnext));
    
    //register_file
    register_file r1(.a1(instr[19:15]),.a2(instr[24:20]),.a3(instr[11:7]),.data(result),.reg_write(reg_write),
                     .clk(clk),.rd1(sra),.rd2(rd2_wire));
                     
    extender e1(.instr(instr[31:0]),.imm_src(imm_src),.out(immext));
    assign write_data=rd2_wire;
    //alu 
    mux_2 m2(.a(rd2_wire),.b(immext),.sel(alu_src),.y(srb));// selection of B
    mux_2 mm2(.a(sra),.b(32'b0),.sel(src_a),.y(srca));
    alu alu1(.alu_con(alu_con),.a(srca),.b(srb),.zero(zero),.result(alu_result));//ALU 
    assign pcjalr={alu_result[31:1],1'b0};//alu_result directly for jalr
    mux_3 m3(.a(alu_result),.b(read_data),.c(pcplus4),.sel(result_src),.y(result));//selection for register
    
endmodule:datapath
