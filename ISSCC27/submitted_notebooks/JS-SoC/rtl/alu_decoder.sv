
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 21.05.2026 10:08:26
// Design Name: 
// Module Name: alu_decoder
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


module alu_decoder(
    input logic [1:0] alu_op,
    input logic [2:0] funct3,
    input logic funct7,
    input logic opcode5,
    output logic [3:0] alu_con
    );
    logic switch1;
    assign switch1=funct7;
    always_comb
    begin
        case(alu_op)
        2'b00:alu_con='0;
        2'b01:alu_con=4'b0001;
        2'b10:
            case(funct3)
                3'b000: if(switch1&opcode5) begin
                            alu_con=4'b0001;//sub
                            end
                        else begin
                            alu_con=4'b0000;//add
                            end
                3'b001:alu_con=4'b0010;//sll
                3'b010:alu_con=4'b0011;//slt
                3'b011:alu_con=4'b0100;//sltu
                3'b100:alu_con=4'b0101;//xor
                3'b101: if(switch1) begin
                            alu_con=4'b0110;//sra
                            end
                        else begin
                            alu_con=4'b0111;//srl
                            end
                3'b110:alu_con=4'b1000;//or
                3'b111:alu_con=4'b1001;//and
                default:alu_con=4'bx;  
            endcase 
        default:alu_con=4'bx;
        endcase
        end     
endmodule:alu_decoder
