
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 23:50:52
// Design Name: 
// Module Name: main_decoder
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


module main_decoder(
    input  logic [6:0] opcode,

    output logic reg_write,
    output logic [2:0] imm_src,
    output logic alu_src,
    output logic mem_write,
    output logic [1:0] result_src,
    output logic branch,
    output logic [1:0] alu_op,
    output logic jump,
    output logic src_a
);

logic [12:0] controls;

assign {reg_write,
        imm_src,
        alu_src,
        mem_write,
        result_src,
        branch,
        alu_op,
        jump,
        src_a} = controls;

always_comb begin
    case(opcode)

        // lw
        7'b0000011:
            controls = 13'b1_000_1_0_01_0_00_0_0;

        // sw
        7'b0100011:
            controls = 13'b0_001_1_1_xx_0_00_0_0;

        // R-type
        7'b0110011:
            controls = 13'b1_xxx_0_0_00_0_10_0_0;

        // beq
        7'b1100011:
            controls = 13'b0_010_0_0_xx_1_01_0_0;

        // addi
        7'b0010011:
            controls = 13'b1_000_1_0_00_0_10_0_0;

        // jal
        7'b1101111:
            controls = 13'b1_011_x_0_10_0_xx_1_0;

        // jalr
        7'b1100111:
            controls = 13'b1_000_1_0_10_0_00_1_0;

        // LUI
        7'b0110111:
            controls = 13'b1_100_1_0_00_0_00_0_1;

        default:
            controls = 13'bx;

    endcase
end

endmodule : main_decoder
