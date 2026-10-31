
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 09:49:49
// Design Name: 
// Module Name: extender
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


module extender(
    input  logic [31:0] instr,
    input  logic [2:0]  imm_src,
    output logic [31:0] out
);

always_comb begin
    case (imm_src)

        3'b000: out = {{20{instr[31]}}, instr[31:20]};                               // I-type

        3'b001: out = {{20{instr[31]}}, instr[31:25], instr[11:7]};                  // S-type

        3'b010: out = {{20{instr[31]}}, instr[7], instr[30:25],
                        instr[11:8], 1'b0};                                           // B-type

        3'b011: out = {{12{instr[31]}}, instr[19:12], instr[20],
                        instr[30:21], 1'b0};                                          // J-type

        3'b100: out = {instr[31:12], 12'b0};                                          // U-type (LUI)

        default: out = 32'bx;

    endcase
end
always_comb begin
    if(|instr[6:0]) begin
    end
end
endmodule : extender
