`timescale 1ps/1ps

// NEED TO CHANGE AFTER FUNCTIONALITY CHECK (MYTHRI)

module dcdl_behavioral #(
    parameter integer CTRL_BITS   = 6,
    parameter integer DELAY_STEP  = 20,   // ps per step
    parameter integer MIN_DELAY   = 0
)(
    input  wire clk_in,
    input  wire [CTRL_BITS-1:0] ctrl,
    output wire clk_out
);

    localparam integer MAX_CTRL = (1 << CTRL_BITS) - 1;

    integer total_delay_ps;

    always @(*) begin
        total_delay_ps = MIN_DELAY + (ctrl * DELAY_STEP);

        if (total_delay_ps < MIN_DELAY)
            total_delay_ps = MIN_DELAY;
        else if (total_delay_ps > (MIN_DELAY + MAX_CTRL * DELAY_STEP))
            total_delay_ps = MIN_DELAY + MAX_CTRL * DELAY_STEP;
    end

    // Behavioral transport-style delay. NOT SYNTHESIZABLE BE CAREFUL. 

    assign #(total_delay_ps) clk_out = clk_in;

endmodule
