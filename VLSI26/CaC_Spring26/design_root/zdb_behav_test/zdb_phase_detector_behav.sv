`timescale 1ns/1ps

module pfd #(
    parameter integer RESET_DELAY_PS = 0
)(
    input  wire clk_ref,
    input  wire clk_fb,
    input  wire rst_n,
    output wire up,
    output wire down
);

    reg up_ff, down_ff;

    wire rst_int;
    wire rst_int_d;

    assign rst_int = up_ff & down_ff;

    generate
        if (RESET_DELAY_PS > 0) begin
            assign #(RESET_DELAY_PS * 1ps) rst_int_d = rst_int;
        end else begin
            assign rst_int_d = rst_int;
        end
    endgenerate

    always @(posedge clk_ref or negedge rst_n) begin
        if (!rst_n)
            up_ff <= 1'b0;
        else if (rst_int_d)
            up_ff <= 1'b0;
        else
            up_ff <= 1'b1;
    end

    always @(posedge clk_fb or negedge rst_n) begin
        if (!rst_n)
            down_ff <= 1'b0;
        else if (rst_int_d)
            down_ff <= 1'b0;
        else
            down_ff <= 1'b1;
    end

    assign up   = up_ff;
    assign down = down_ff;

endmodule