`timescale 1ns/1ps

module dcdl #(
    parameter integer CTRL_BITS = 6,
    parameter integer DELAY_PS  = 100
)(
    input  wire                 clk_in,
    input  wire [CTRL_BITS-1:0] ctrl,
    output wire                 clk_out
);

    localparam integer STAGES = (1 << CTRL_BITS);

    wire [STAGES:0] delay_chain;
    assign delay_chain[0] = clk_in;

    genvar i;
    generate
        for (i = 0; i < STAGES; i = i + 1) begin : delay_chain_gen
            if (DELAY_PS > 0) begin
                assign #(DELAY_PS * 1ps) delay_chain[i+1] = delay_chain[i];
            end else begin
                assign delay_chain[i+1] = delay_chain[i];
            end
        end
    endgenerate

    reg [CTRL_BITS-1:0] ctrl_r = 0;

    always @(posedge clk_in)
        ctrl_r <= ctrl;

    assign clk_out = delay_chain[ctrl_r];

endmodule