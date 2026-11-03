`default_nettype none
// ALU de 8 Bits
module alu_8bit (
    input  wire [7:0] a,           // Reg A
    input  wire [7:0] b,           // Reg B
    input  wire [2:0] op,          // Operaciones (3 bits = 8 ops)
    output reg  [7:0] result,      // Resultado de 8 bits
    output wire       zero,        // Flag 0
    output wire       carry,       // Flag desbordamiento sin signo
    output wire       negative     // Flag bit 7 del resultado (signed)
);

    // Operaciones de la ALU
    localparam OP_ADD = 3'b000;
    localparam OP_SUB = 3'b001;
    localparam OP_AND = 3'b010;
    localparam OP_OR  = 3'b011;
    localparam OP_XOR = 3'b100;
    localparam OP_SLL = 3'b101;    // Shift left
    localparam OP_SRL = 3'b110;    // Shift right
    localparam OP_SLT = 3'b111;    // Set less than (sin signo)

    // Resultado con carry extendido jsjs
    reg [8:0] result_ext;

    always @(*) begin
        result_ext = 9'b0;
        case (op)
            OP_ADD: result_ext = {1'b0, a} + {1'b0, b};
            OP_SUB: result_ext = {1'b0, a} - {1'b0, b};
            OP_AND: result_ext = {1'b0, a & b};
            OP_OR:  result_ext = {1'b0, a | b};
            OP_XOR: result_ext = {1'b0, a ^ b};
            OP_SLL: result_ext = {1'b0, a << b[2:0]};
            OP_SRL: result_ext = {1'b0, a >> b[2:0]};
            OP_SLT: result_ext = {9'h000} | (a < b ? 9'h001 : 9'h000);
            default: result_ext = 9'b0;
        endcase
        result = result_ext[7:0];
    end

    assign zero     = (result == 8'h00);
    assign carry    = result_ext[8];
    assign negative = result[7];

endmodule

`default_nettype wire
