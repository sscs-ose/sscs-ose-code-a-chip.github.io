//**************************************************************************
// Author: Alfi Misha Antony Selvin Raj
// Description: Shift register for one hot encoding
//**************************************************************************
module dll_shift_register(
    input  logic clk,
    input  logic rst_n,
    input  logic shift_left,
    input  logic shift_right,
    output logic [3:0] Q
);
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        Q <= 4'b0001; //start value
    end
    else if (shift_left) begin
        Q <= {Q[2:0], Q[3]};
    end
    else if (shift_right) begin
        Q <= {Q[0], Q[3:1]};
    end
end
endmodule