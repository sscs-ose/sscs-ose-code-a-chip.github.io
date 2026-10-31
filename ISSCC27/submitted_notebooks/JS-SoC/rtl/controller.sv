
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 22.05.2026 12:32:35
// Design Name: 
// Module Name: controller
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


module controller(
    input logic [6:0] opcode,
    input logic [2:0] funct3,
    input logic funct7,
    input logic zero,
    output logic [1:0] result_src,
    output logic mem_write,
    output logic alu_src,
    output logic [1:0] pc_src,
    output logic reg_write,
    //output logic jump,
    output logic [2:0] imm_src,
    output logic [3:0] alu_con,
    output logic src_a
    );
    logic [1:0] alu_op; 
    logic jump;
    logic branch;
    
    main_decoder d1(.opcode(opcode),.result_src(result_src),.mem_write(mem_write),
                    .reg_write(reg_write),.branch(branch),.alu_src(alu_src),
                    .jump(jump),.imm_src(imm_src),.alu_op(alu_op),.src_a(src_a));
    
    alu_decoder a1(.alu_op(alu_op),.funct3(funct3),.funct7(funct7),.opcode5(opcode[5]),
                   .alu_con(alu_con));
    
    always_comb 
    begin
        if(jump&&!opcode[3])
            begin
            pc_src=2'b10;
            end
        else if((jump && opcode[3])|| (branch && zero))
            begin
            pc_src=2'b01;
            end
        else 
            begin
            pc_src=2'b00;
            end
    end   
endmodule:controller
