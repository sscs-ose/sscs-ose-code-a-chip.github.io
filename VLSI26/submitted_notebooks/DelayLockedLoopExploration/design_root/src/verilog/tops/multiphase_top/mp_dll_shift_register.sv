`timescale 1ps/1ps

// Scalable now

module dll_shift_register #(
    parameter integer WIDTH = 8
)(
    input  logic clk,
    input  logic rst_n,
    input  logic shift_left,
    input  logic shift_right,
    output logic [WIDTH-1:0] Q
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            Q <= {{(WIDTH-1){1'b0}}, 1'b1};  // one-hot init
        else begin
            if (shift_left)
                Q <= {Q[WIDTH-2:0], Q[WIDTH-1]};
            else if (shift_right)
                Q <= {Q[0], Q[WIDTH-1:1]};
        end
    end

endmodule